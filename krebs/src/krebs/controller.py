"""Serialized board authority with durable launch and independently fenced provider steps."""
from copy import deepcopy
import time
import uuid
from psycopg.types.json import Jsonb
from .contract import decide, digest, require, validate, content_revision

class Controller:
    def __init__(self, store, registry, provider, runtime, clock=time.time):
        self.store,self.registry,self.provider,self.runtime,self.clock=store,registry,provider,runtime,clock
        # Only the controller injects its database into the internal subprocess.
        if hasattr(provider,'attach_store'): provider.attach_store(store)

    def _pm(self, project, actor, command):
        require(actor.get('role')=='operator' or (actor.get('role')=='pm' and command['actor_id']==project.get('pm_actor')) or actor.get('role')=='interactive', 'delegate to the owning PM')

    def execute(self, command, auth):
        validate(command)
        project,actor=self.registry.authenticate(command,auth)
        op=command['operation']
        require(project.get('mode')=='managed' or op in {'status','get'}, 'shadow mode forbids mutations')
        with self.store.board_lock(command['project_id']) as conn:
            prior=conn.execute('SELECT * FROM krebs.commands WHERE command_id=%s OR idempotency_key=%s',(command['command_id'],command['idempotency_key'])).fetchone()
            if prior:
                require(prior['digest']==digest(command),'idempotency key or command id body conflict')
                if prior['receipt']['status']=='accepted': self._recover(conn,project,prior['command_id'])
                return self._receipt(conn,prior['command_id'])
            board=self.store.board(conn,project)
            if op=='status':
                operation=None
                if command.get('payload',{}).get('operation_id'):
                    found=conn.execute('SELECT receipt FROM krebs.commands WHERE command_id=%s AND project_id=%s',(command['payload']['operation_id'],command['project_id'])).fetchone()
                    require(found is not None,'operation not found for this project'); operation=found['receipt']
                return {'version':2,'command_id':command['command_id'],'status':'result','ok':True,'board':board,'operation':operation}
            if op=='reconcile':
                require(actor.get('role')=='operator','operator reconciliation required')
                return self._operator_reconcile(conn,project,board,command)
            require(not board['pending'],'board has an unresolved provider intent')
            self.provider.verify(project,actor)
            require(project.get('legacy_writers_fenced') is True,'legacy writer inventory is not fenced')
            require(project.get('skill_version') and project.get('policy_version')==2,'runtime skill/policy binding missing')
            require(actor.get('runtime',{}).get('adapter')=='systemd','runtime stop-proof adapter not enrolled')
            target=bool(board['active'] and board['active']['ticket_id']==command['ticket_id'])
            if op in {'claim','takeover','resume','create','plan','reevaluate','override','planner'} or (op in {'comment','update','cancel'} and not target): self._pm(project,actor,command)
            if op in {'takeover','reevaluate','override'}:
                require(actor.get('role')=='operator' and command.get('payload',{}).get('reason'),'reasoned operator authority required')
            if op in {'claim','resume','takeover'}:
                used=conn.execute("SELECT 1 FROM krebs.commands WHERE project_id=%s AND body->>'run_id'=%s AND body->>'operation' IN ('claim','resume','takeover') LIMIT 1",(command['project_id'],command['run_id'])).fetchone()
                require(not used,'run ID already used; create a new run')
            if op=='planner': return self._planner(conn,project,actor,board,command)
            ticket={'lane':'Backlog','revision':None,'content_revision':None} if op=='create' else self.provider.ticket(project,actor,command['ticket_id'])
            if op=='get': return {'version':2,'command_id':command['command_id'],'status':'result','ok':True,'ticket':ticket}
            reviews=conn.execute('SELECT * FROM krebs.reviews WHERE project_id=%s AND ticket_id=%s AND generation=%s',(command['project_id'],command['ticket_id'],command['generation'])).fetchall()
            children=conn.execute("SELECT command_id,project_id,body->>'ticket_id' AS ticket_id FROM krebs.commands WHERE receipt->>'lane'='Done' AND receipt->>'operation' IN ('handoff','complete') AND receipt->>'ok'='true' AND COALESCE(receipt->>'completion_kind','reviewed')='reviewed'").fetchall()
            next_state,action=decide(board,command,self.clock(),ticket,reviews,children)
            if action and action.get('audit_only'): return self._audit(conn,command,action)
            if op in {'claim','resume','takeover'}:
                next_state['active']['supervisor']=self.runtime.freeze(actor['runtime']) if hasattr(self.runtime,'freeze') else deepcopy(actor['runtime'])
                next_state['active']['project_root']=str(__import__('pathlib').Path(project.get('manifest','.project.json')).parent)
                next_state['tickets'][command['ticket_id']]['attempt']=deepcopy(next_state['active'])
            if action and action.get('update'):
                desired={'description_html':ticket.get('description_html',''),'name':ticket.get('name','')}
                desired.update(action['update'])
                action['_desired_content_revision']=digest(desired)
            plan={'next':next_state,'action':action,'attempt':deepcopy(board['active']),'actor':command['actor_id'],
                  'content_revision':content_revision(ticket)}
            self._enqueue(conn,project,actor,board,command,plan)
            self._recover(conn,project,command['command_id'])
            return self._receipt(conn,command['command_id'])

    def _receipt(self, conn, ident):
        return conn.execute('SELECT receipt FROM krebs.commands WHERE command_id=%s',(ident,)).fetchone()['receipt']

    def _base_receipt(self,command,**fields):
        return {'version':2,**{k:command[k] for k in ('command_id','project_id','ticket_id','run_id','runtime_id','generation')},**fields}

    def _steps(self, action, expected):
        if not action or 'runtime_start' in action: return []
        steps=[]
        if 'create' in action: steps.append(('create',{'create':action['create'],'lane':'Backlog'}))
        else:
            projection={k:action[k] for k in ('lane','working','assign','update','_desired_content_revision') if k in action}
            if projection: steps.append(('projection',projection))
        if action.get('comment') or action.get('question'):
            steps.append(('comment',{k:action[k] for k in ('comment','question') if action.get(k)}))
        for _,step in steps: step['_expected_content_revision']=expected
        return steps

    def _enqueue(self,conn,project,actor,board,command,plan):
        ident=command['command_id']
        binding=self.provider.binding(project,actor) if hasattr(self.provider,'binding') else {}
        with conn.transaction():
            conn.execute('INSERT INTO krebs.commands(command_id,idempotency_key,project_id,body,digest,receipt) VALUES(%s,%s,%s,%s,%s,%s)',(ident,command['idempotency_key'],command['project_id'],Jsonb(command),digest(command),Jsonb(self._base_receipt(command,status='accepted',ok=True))))
            conn.execute('INSERT INTO krebs.intents(command_id,project_id,plan) VALUES(%s,%s,%s)',(ident,command['project_id'],Jsonb(plan)))
            for step_id,action in self._steps(plan['action'],plan.get('content_revision')):
                conn.execute('INSERT INTO krebs.provider_steps(command_id,step_id,action,binding) VALUES(%s,%s,%s,%s)',(ident,step_id,Jsonb(action),Jsonb(binding)))
            board['pending']=ident
            if plan['action'] and plan['action'].get('stop') and board['active']: board['active']['revoked']=True
            self.store.save(conn,board)

    def _recover(self,conn,project,ident):
        intent=conn.execute('SELECT * FROM krebs.intents WHERE command_id=%s',(ident,)).fetchone()
        if not intent or intent['verified']: return
        command=conn.execute('SELECT body FROM krebs.commands WHERE command_id=%s',(ident,)).fetchone()['body']
        plan,actor=intent['plan'],project['actors'][command['actor_id']]
        try:
            action=plan['action'] or {}
            # Safety never depends on provider availability. Stop first and persist proof.
            if action.get('stop') and plan.get('attempt') and not intent['stopped']:
                proof=self.runtime.stop(project,plan['attempt'])
                conn.execute('UPDATE krebs.intents SET stopped=true WHERE command_id=%s',(ident,))
            if 'runtime_start' in action:
                attempt=plan['attempt']
                if self.clock() >= attempt['lease_until']:
                    if command['operation']=='planner':
                        self.runtime.stop(project,attempt)
                        board=self.store.board(conn,project)
                        self._supersede(conn,board,'planner launch lease expired; stopped without dispatch')
                        board['pending']=None; board['revision']+=1; self.store.save(conn,board)
                    else: self._expire(conn,project,self.store.board(conn,project),'launch lease expired')
                    return
                if intent['launch_attempted']:
                    require(self.runtime.present(project,attempt),'launch outcome uncertain; transient unit disappeared; operator reconciliation required')
                else:
                    conn.execute('UPDATE krebs.intents SET launch_attempted=true WHERE command_id=%s',(ident,))
                    self.runtime.start(project,attempt,action['runtime_start'])
                conn.execute('UPDATE krebs.intents SET launch_confirmed=true WHERE command_id=%s',(ident,))
            self.provider.verify(project,actor)
            observed=None
            # Each HTTP mutation has its own durable sent bit and readback. A PATCH
            # committed before a comment can be recovered without replaying either POST.
            steps=conn.execute("SELECT * FROM krebs.provider_steps WHERE command_id=%s ORDER BY CASE step_id WHEN 'create' THEN 0 WHEN 'projection' THEN 1 ELSE 2 END",(ident,)).fetchall()
            for step in steps:
                if step['verified']:
                    observed=step['observed']; continue
                marker=ident+':'+step['step_id']
                observed=self.provider.reconcile(project,actor,command['ticket_id'],step['action'],marker)
                require(not observed.get('content_conflict'),'provider content changed; readiness invalidated')
                if not observed.get('matched'):
                    require(not step['sent'],'uncertain provider write; operator reconciliation required')
                    conn.execute('UPDATE krebs.provider_steps SET sent=true WHERE command_id=%s AND step_id=%s',(ident,step['step_id']))
                    capability={'command_id':ident,'step_id':step['step_id'],'ticket_id':command['ticket_id']}
                    if hasattr(self.provider,'apply_step'): self.provider.apply_step(project,actor,command['ticket_id'],step['action'],marker,capability)
                    else: self.provider.apply(project,actor,command['ticket_id'],step['action'],marker)
                    observed=self.provider.reconcile(project,actor,command['ticket_id'],step['action'],marker)
                    require(not observed.get('content_conflict'),'provider content changed; readiness invalidated')
                    require(observed.get('matched'),'provider readback mismatch')
                conn.execute('UPDATE krebs.provider_steps SET verified=true,observed=%s WHERE command_id=%s AND step_id=%s',(Jsonb(observed),ident,step['step_id']))
            next_state=plan['next']; next_state['pending']=None
            record=next_state['tickets'].get(command['ticket_id'],{})
            if observed:
                record['provider_revision']=observed.get('projection_revision',observed.get('revision'))
                # Comments never change accepted content authority. An explicit update
                # invalidates acceptance; a later claim freezes new content separately.
            receipt=self._base_receipt(command,status='result',ok=True,operation=command['operation'],evidence=command.get('payload',{}),
                intent_id=ident,question=record.get('question'),requested_actor=command['actor_id'],applied_native_user=actor['native_user_id'],
                revision=next_state['revision'],generation=next_state['generation'],lane=record.get('lane'),provider=observed,
                completion_kind=record.get('completion_kind','reviewed'))
            with conn.transaction():
                self.store.save(conn,next_state)
                if command['operation']=='review':
                    conn.execute('INSERT INTO krebs.reviews(id,project_id,ticket_id,generation,actor_id,run_id,evidence) VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',(ident,command['project_id'],command['ticket_id'],command['generation'],command['actor_id'],command['run_id'],Jsonb(command['payload'])))
                conn.execute('UPDATE krebs.intents SET verified=true,error=NULL,updated_at=now() WHERE command_id=%s',(ident,))
                conn.execute('UPDATE krebs.commands SET receipt=%s WHERE command_id=%s',(Jsonb(receipt),ident))
                self._record(conn,command,receipt)
        except Exception as exc:
            if 'content changed' in str(exc):
                board=self.store.board(conn,project)
                if board['active']:
                    board['active']['acceptance']=None; board['active']['revoked']=True
                    self.store.save(conn,board)
                    self.runtime.stop(project,board['active'])
            conn.execute('UPDATE krebs.intents SET error=%s,updated_at=now() WHERE command_id=%s',(type(exc).__name__+': '+str(exc),ident))
            raise

    def _audit(self,conn,command,action):
        receipt=self._base_receipt(command,ok=False,status='audit_only',**action)
        with conn.transaction():
            conn.execute('INSERT INTO krebs.commands(command_id,idempotency_key,project_id,body,digest,receipt) VALUES(%s,%s,%s,%s,%s,%s)',(command['command_id'],command['idempotency_key'],command['project_id'],Jsonb(command),digest(command),Jsonb(receipt)))
            self._record(conn,command,receipt)
        return receipt

    def _record(self,conn,command,receipt):
        conn.execute('INSERT INTO krebs.history(project_id,command_id,receipt) VALUES(%s,%s,%s)',(command['project_id'],command['command_id'],Jsonb(receipt)))
        from .service import envelope
        eid=str(uuid.uuid4()); event=envelope('event','receipt','recorded',receipt,command['correlation_id'],command['command_id'],eid)
        event['ordering_key']=command['project_id']
        conn.execute('INSERT INTO krebs.outbox(id,subject,envelope) VALUES(%s,%s,%s)',(eid,'bloodbank.evt.lifecycle.receipt.recorded',Jsonb(event)))

    def _supersede(self,conn,board,reason):
        if board['pending']:
            old=conn.execute('SELECT body FROM krebs.commands WHERE command_id=%s',(board['pending'],)).fetchone()['body']
            receipt=self._base_receipt(old,ok=False,status='cancelled',reason=reason)
            conn.execute('UPDATE krebs.commands SET receipt=%s WHERE command_id=%s',(Jsonb(receipt),old['command_id']))
            conn.execute('UPDATE krebs.intents SET verified=true,error=%s WHERE command_id=%s',(reason,old['command_id']))
            self._record(conn,old,receipt)
            board['pending']=None

    def _expire(self,conn,project,board,reason='lease expired'):
        old=deepcopy(board['active'])
        require(old is not None,'no attempt to expire')
        actor_id=project.get('controller_actor')
        require(actor_id in project['actors'],'controller repair actor not enrolled; capacity held')
        ident=str(uuid.uuid4())
        command={'version':2,'operation':'attention','command_id':ident,'idempotency_key':ident,
            'project_id':project['project_id'],'ticket_id':old['ticket_id'],'actor_id':actor_id,'runtime_id':old['runtime_id'],
            'run_id':old['run_id'],'generation':old['generation'],'expected_revision':board['revision'],
            'correlation_id':old['correlation_id'],'causation_id':ident,'payload':{'reason':reason}}
        next_state=deepcopy(board);next_state['active']=None;next_state['revision']+=1
        next_state['tickets'][old['ticket_id']]['lane']='Needs Attention'
        plan={'next':next_state,'action':{'lane':'Needs Attention','working':False,'stop':True},'attempt':old,'actor':actor_id,'content_revision':None}
        with conn.transaction():
            self._supersede(conn,board,reason)
            self._enqueue(conn,project,project['actors'][actor_id],board,command,plan)
        self._recover(conn,project,ident)

    def _operator_reconcile(self,conn,project,board,command):
        payload=command.get('payload',{})
        require(board['pending'] and payload.get('operation_id')==board['pending'],'select the pending operation')
        require(command['expected_revision']==board['revision'],'revision conflict')
        require(payload.get('reason') and payload.get('receipt'),'operator reconciliation reason and evidence receipt required')
        require(payload.get('resolution') in {'cancel','abandon'},'resolution must be cancel or abandon')
        pending=conn.execute('SELECT body FROM krebs.commands WHERE command_id=%s',(board['pending'],)).fetchone()['body']
        pending_plan=conn.execute('SELECT plan FROM krebs.intents WHERE command_id=%s',(board['pending'],)).fetchone()['plan']
        planner=pending['operation']=='planner'
        require(command['ticket_id']==pending['ticket_id'],'reconciliation ticket mismatch')
        next_state=deepcopy(board);next_state['revision']+=1;next_state['pending']=None
        attempt=deepcopy(pending_plan.get('attempt') if planner else board['active'])
        action={'stop':bool(attempt)}
        if planner:
            next_state['tickets'].pop(command['ticket_id'],None)
        elif payload['resolution']=='cancel':
            action.update(lane='Cancelled',working=False)
            next_state['tickets'].setdefault(command['ticket_id'],{})['lane']='Cancelled'
        else:
            next_state['tickets'].setdefault(command['ticket_id'],{}).update(lane='Needs Re-evaluation',unverified_provider=True)
        if not planner and board['active'] and board['active']['ticket_id']==command['ticket_id']: next_state['active']=None
        plan={'next':next_state,'action':action,'attempt':attempt,'actor':command['actor_id'],'content_revision':None}
        with conn.transaction():
            self._supersede(conn,board,'operator '+payload['resolution']+': '+payload['reason'])
            self._enqueue(conn,project,project['actors'][command['actor_id']],board,command,plan)
        self._recover(conn,project,command['command_id'])
        return self._receipt(conn,command['command_id'])

    def _planner(self,conn,project,actor,board,command):
        active=board['active']
        successful=bool(active and (board['tickets'][active['ticket_id']].get('outcome') or {}).get('outcome')=='success')
        require(not active or successful,'worker capacity occupied')
        require(command['expected_revision']==board['revision'],'revision conflict')
        argv=actor.get('runtime',{}).get('planner_argv')
        from .contract import argv_valid
        require(argv_valid(argv),'enrolled planner argv required')
        planner={**command,'lease_until':self.clock()+300,'supervisor':self.runtime.freeze(actor['runtime']) if hasattr(self.runtime,'freeze') else deepcopy(actor['runtime']),'project_root':str(__import__('pathlib').Path(project['manifest']).parent)}
        # One fixed planner unit per board; runtime refuses a second active instance.
        planner['run_id']='planner-'+digest(project['project_id'])[:16]
        planner['planning']=True
        plan={'next':deepcopy(board),'action':{'runtime_start':argv},'attempt':planner,'actor':command['actor_id'],'content_revision':None}
        plan['next']['revision']+=1
        self._enqueue(conn,project,actor,board,command,plan)
        self._recover(conn,project,command['command_id'])
        return self._receipt(conn,command['command_id'])

    def sweep(self):
        with self.store.connect() as conn: ids=[r['project_id'] for r in conn.execute('SELECT project_id FROM krebs.boards')]
        errors=[]
        for pid in ids:
            try:
                project=self.registry.project(pid)
                with self.store.board_lock(pid) as conn:
                    board=self.store.board(conn,project)
                    # Revoke/stop before *any* Plane read, even during outage or paused rollout.
                    pending_stop=False
                    if board['pending']:
                        pending=conn.execute('SELECT plan FROM krebs.intents WHERE command_id=%s',(board['pending'],)).fetchone()
                        pending_stop=bool(pending and (pending['plan'].get('action') or {}).get('stop'))
                    if board['active'] and not pending_stop and (self.clock()>=board['active']['lease_until'] or project['mode']!='managed'):
                        self._expire(conn,project,board,'lease expired or authority paused'); continue
                    if board['pending']:
                        self._recover(conn,project,board['pending']); board=self.store.board(conn,project)
                    if project['mode']!='managed': continue
                    if board['active']:
                        attempt=board['active'];record=board['tickets'][attempt['ticket_id']]
                        successful=(record.get('outcome') or {}).get('outcome')=='success'
                        if record.get('dispatched') and not successful and not self.runtime.running(project,attempt):
                            self._expire(conn,project,board,'worker exited without delivered outcome');continue
                        observed=self.provider.ticket(project,project['actors'][attempt['actor_id']],attempt['ticket_id'])
                        if observed['lane']!=record['lane'] or content_revision(observed)!=attempt.get('content_revision',attempt.get('ticket_revision')):
                            self._expire(conn,project,board,'external provider content or lane changed')
                    else:
                        for tid,record in board['tickets'].items():
                            if record.get('attempt') and record.get('lane')!='Done':
                                old=record['attempt']; observed=self.provider.ticket(project,project['actors'][old['actor_id']],tid)
                                if observed['lane']=='Done':
                                    board['active']=old;self._expire(conn,project,board,'manual Done lacks evidence');break
            except Exception as exc: errors.append({'project_id':pid,'error':type(exc).__name__})
        return errors
