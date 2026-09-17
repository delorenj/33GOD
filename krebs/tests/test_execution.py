import copy
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from krebs.contract import Rejected, LANES
from krebs.controller import Controller
from krebs.store import Store

class Registry:
    def __init__(self):
        self.binding = {'project_id':str(uuid.uuid4()),'board':str(uuid.uuid4()),'mode':'managed','pm_actor':'pm','controller_actor':'repair','legacy_writers_fenced':True,'skill_version':'test','policy_version':2,'actors': {name:{'native_user_id':name,'role':'operator' if name=='repair' else 'pm','runtime':{'adapter':'systemd'}} for name in ['pm','reviewer','repair']}}
    def project(self, _): return self.binding
    def authenticate(self, command, auth):
        if auth != command['actor_id']: raise Rejected('bad identity')
        return self.binding, self.binding['actors'][command['actor_id']]
class Provider:
    def __init__(self): self.comments=set(); self.lane='Todo'; self.revision='revision-1'; self.writes=0; self.lose=False; self.outage=False
    def verify(self, *_):
        if self.outage: raise Rejected('provider unavailable')
    def ticket(self,*_): return {'lane':self.lane,'revision':self.revision}
    def reconcile(self,p,a,t,action,marker): return {'matched': self.lane == action['lane'] if 'lane' in action else marker in self.comments, 'revision':self.revision}
    def apply(self,p,a,t,action,marker):
        self.writes += 1; self.lane=action.get('lane',self.lane); self.comments.add(marker); self.projection_revision=f'projection-{self.writes+1}'
        if self.lose: self.lose=False; raise OSError('response lost')
class Runtime:
    def __init__(self): self.live=False; self.stops=0
    def stop(self,*_):
        self.stops+=1
        if self.live: raise Rejected('old worker alive')
        return {'stopped':True}
    def start(self,*_): return {'started':True}
    def running(self,*_): return self.live
    def present(self,*_): return True
@pytest.fixture
def world():
    dsn=os.environ.get('KREBS_TEST_DSN')
    if not dsn: pytest.fail('KREBS_TEST_DSN required: run mise run test with disposable services')
    store=Store(dsn); store.migrate()
    registry,provider,runtime=Registry(),Provider(),Runtime()
    clock=[1000]
    ctl=Controller(store,registry,provider,runtime,clock=lambda:clock[0])
    return ctl,registry,provider,runtime,clock

def command(world, operation='claim', actor='pm', **overrides):
    c,r,p,_,_=world
    with c.store.board_lock(r.binding['project_id']) as conn:
        board=c.store.board(conn,r.binding)
    ident=str(uuid.uuid4())
    result={'version':2,'operation':operation,'command_id':ident,'idempotency_key':ident,'project_id':r.binding['project_id'],'ticket_id':'ticket','actor_id':actor,'runtime_id':'host','run_id':'run','generation':board['generation'],'expected_revision':board['revision'],'correlation_id':ident,'causation_id':ident,'payload':{'acceptance':{'profile':'default'},'artifact':'sha1','ticket_revision':p.revision}}
    result.update(overrides); return result

def execute(world, **kw):
    cmd=command(world,**kw); return world[0].execute(cmd,cmd['actor_id'])

def test_concurrent_claim_exactly_one(world):
    a,b=command(world),command(world,run_id='other')
    barrier=threading.Barrier(2)
    def claim(c):
        barrier.wait()
        try: return world[0].execute(c,'pm')['ok']
        except Rejected: return False
    with ThreadPoolExecutor(2) as pool: assert sum(pool.map(claim,[a,b]))==1
    assert world[2].writes==1

def test_duplicate_conflict_identity_and_late_callback(world):
    c=command(world)
    with pytest.raises(Rejected): world[0].execute(c,'wrong')
    assert world[2].writes==0
    receipt=world[0].execute(c,'pm')
    assert world[0].execute(c,'pm')==receipt
    c['payload']['artifact']='different'
    with pytest.raises(Rejected): world[0].execute(c,'pm')
    execute(world,operation='start',payload={'argv':['true']})
    assert execute(world,operation='finish',generation=0)['status']=='audit_only'
    assert world[2].writes==1

def test_lost_provider_response_restart_reconciles_without_duplicate(world):
    c=command(world); world[2].lose=True
    with pytest.raises(OSError): world[0].execute(c,'pm')
    old=world[0]; restarted=Controller(old.store,old.registry,old.provider,old.runtime,old.clock)
    assert restarted.execute(c,'pm')['ok']
    assert world[2].writes==1

def test_attention_holds_capacity_until_stopped_resume_once(world):
    execute(world); world[3].live=True
    c=command(world,operation='attention',payload={'question_id':'q','question':'Which revision?','context':'Cannot proceed'})
    with pytest.raises(Rejected): world[0].execute(c,'pm')
    with pytest.raises(Rejected): execute(world,run_id='replacement')
    world[3].live=False; assert world[0].execute(c,'pm')['ok']
    assert world[2].lane=='Needs Attention'
    payload={'question_id':'q','answer':'A','acceptance':{'profile':'default'},'artifact':'sha2','ticket_revision':world[2].revision}
    assert execute(world,operation='resume',run_id='new',payload=payload)['generation']==2
    with pytest.raises(Rejected): execute(world,operation='resume',run_id='new',payload=payload)

def test_expiry_does_not_free_live_worker_then_repairs_provider(world):
    execute(world); world[4][0]+=301; world[3].live=True
    assert world[0].sweep()
    with pytest.raises(Rejected): execute(world,run_id='new')
    world[3].live=False; assert not world[0].sweep()
    assert world[2].lane=='Needs Attention'
    stops=world[3].stops; assert not world[0].sweep(); assert world[3].stops==stops

def test_success_requires_reviews_and_exact_progression(world):
    execute(world)
    with pytest.raises(Rejected): execute(world,operation='complete',payload={})
    execute(world,operation='start',payload={'argv':['true']})
    assert execute(world,operation='finish',payload={'outcome':'success','artifact':'sha2'})['lane']=='In Progress'
    for kind in ['spec','quality']:
        execute(world,operation='review',actor='reviewer',run_id=kind,payload={'artifact':'sha2','acceptance':{'profile':'default'},'kind':kind,'passed':True,'receipt':'review:'+kind})
    evidence={'artifact':'sha2','acceptance':{'profile':'default'}}
    for gate in ['tests','docs','notebook','skill','main','push','deployment']: evidence[gate]={'passed':True,'receipt':gate+':verified'}
    for lane in ['E2E Testing & QA','Ready for Documentation','Done']:
        result=execute(world,operation='handoff' if lane!='Done' else 'complete',payload={'lane':lane,'evidence':evidence})
        assert result['lane']==lane
    assert world[3].stops==1

def test_takeover_revision_checked_before_stop(world):
    execute(world)
    with pytest.raises(Rejected): execute(world,operation='takeover',actor='repair',expected_revision=0,payload={'reason':'repair','acceptance':{'profile':'default'},'artifact':'y','ticket_revision':world[2].revision})
    assert world[3].stops==0

def test_outage_no_mutations_and_shadow_no_mutations(world):
    world[2].outage=True
    with pytest.raises(Rejected): execute(world)
    world[2].outage=False; world[1].binding['mode']='shadow'
    with pytest.raises(Rejected): execute(world)
    assert world[2].writes==0

def test_supervised_resume_resets_dispatch_and_question_cannot_be_skipped(world):
    execute(world)
    execute(world,operation='start',payload={'argv':['true']})
    execute(world,operation='attention',payload={'question_id':'q','question':'Which?','context':'Blocked'})
    with pytest.raises(Rejected,match='open question'):
        execute(world,run_id='new')
    payload={'question_id':'q','answer':'yes','acceptance':{'profile':'default'},'artifact':'sha2','ticket_revision':world[2].revision}
    execute(world,operation='resume',run_id='new',payload=payload)
    assert execute(world,operation='start',run_id='new',payload={'argv':['true']})['ok']

def test_operator_takeover_stops_old_before_new_generation(world):
    execute(world)
    payload={'reason':'repair','acceptance':{'profile':'default'},'artifact':'sha2','ticket_revision':world[2].revision}
    result=execute(world,operation='takeover',actor='repair',run_id='replacement',payload=payload)
    assert result['generation']==2
    assert world[3].stops==1

def test_ephemeral_independent_reviewer_shares_accountable_actor(world):
    execute(world)
    assert execute(world,operation='review',run_id='independent-review',payload={'artifact':'sha1','acceptance':{'profile':'default'},'kind':'spec','passed':True,'receipt':'reviewed'})['ok']

def test_manual_done_is_repaired_to_attention(world):
    execute(world); world[2].lane='Done'
    assert not world[0].sweep()
    assert world[2].lane=='Needs Attention'

def test_operation_status_finds_receipt_without_original_body(world):
    c=command(world); receipt=world[0].execute(c,'pm')
    result=execute(world,operation='status',payload={'operation_id':c['command_id']})
    assert result['operation']==receipt

def test_worker_exit_is_attention_not_done(world):
    execute(world); execute(world,operation='start',payload={'argv':['true']})
    assert not world[0].sweep()
    assert world[2].lane=='Needs Attention'

def test_current_artifact_invalidates_prior_reviews(world):
    execute(world)
    for kind in ['spec','quality']:
        execute(world,operation='review',run_id=kind,payload={'artifact':'sha1','acceptance':{'profile':'default'},'kind':kind,'passed':True,'receipt':kind})
    execute(world,operation='start',payload={'argv':['true']})
    execute(world,operation='finish',payload={'outcome':'success','artifact':'sha2'})
    with pytest.raises(Rejected,match='reviews required'):
        execute(world,operation='handoff',payload={'evidence':{'artifact':'sha2','acceptance':{'profile':'default'}}})

def test_uuid_validation_precedes_provider_mutation(world):
    with pytest.raises(Rejected,match='UUID'):
        execute(world,correlation_id='not-a-uuid')
    assert world[2].writes==0

def test_child_receipts_gate_parent_completion(world):
    c=command(world,payload={'acceptance':{'profile':'default','children':[{'command_id':'missing-child-command','project_id':'child','ticket_id':'child-ticket'}]},'artifact':'sha1','ticket_revision':world[2].revision})
    world[0].execute(c,'pm')
    for kind in ['spec','quality']:
        execute(world,operation='review',run_id=kind,payload={'artifact':'sha1','acceptance':{'profile':'default','children':[{'command_id':'missing-child-command','project_id':'child','ticket_id':'child-ticket'}]},'kind':kind,'passed':True,'receipt':kind})
    execute(world,operation='start',payload={'argv':['true']})
    execute(world,operation='finish',payload={'outcome':'success','artifact':'sha1'})
    evidence={'artifact':'sha1','acceptance':{'profile':'default','children':[{'command_id':'missing-child-command','project_id':'child','ticket_id':'child-ticket'}]},'tests':{'passed':True,'receipt':'test'}}
    with pytest.raises(Rejected,match='child completion'):
        execute(world,operation='handoff',payload={'evidence':evidence})

def test_indeterminate_provider_write_never_retries_blindly(world):
    c=command(world)
    def failed_apply(*args):
        world[2].writes+=1
        raise OSError('unknown transport result')
    world[2].apply=failed_apply
    with pytest.raises(OSError): world[0].execute(c,'pm')
    with pytest.raises(Rejected,match='uncertain provider write'): world[0].execute(c,'pm')
    assert world[2].writes==1

def test_expired_outage_stops_before_provider_and_reuses_repair_intent(world):
    execute(world);world[2].outage=True;world[4][0]+=301
    assert world[0].sweep(); assert world[3].stops==1
    with world[0].store.connect() as conn:
        before=conn.execute('SELECT pending FROM krebs.boards WHERE project_id=%s',(world[1].binding['project_id'],)).fetchone()['pending']
    assert world[0].sweep(); assert world[3].stops==1
    with world[0].store.connect() as conn:
        assert conn.execute('SELECT pending FROM krebs.boards WHERE project_id=%s',(world[1].binding['project_id'],)).fetchone()['pending']==before
    world[2].outage=False;assert not world[0].sweep()

def test_lost_launch_never_restarts_disappeared_unit(world):
    execute(world)
    calls=[]
    def launch(*args):calls.append(1);raise OSError('lost supervisor reply')
    world[3].start=launch;world[3].present=lambda *_:False
    c=command(world,operation='start',payload={'argv':['true']})
    with pytest.raises(OSError):world[0].execute(c,'pm')
    with pytest.raises(Rejected,match='uncertain'):world[0].execute(c,'pm')
    assert len(calls)==1
    fix=command(world,operation='reconcile',actor='repair',payload={'operation_id':c['command_id'],'resolution':'cancel','reason':'unit gone','receipt':'systemd probe'})
    assert world[0].execute(fix,'repair')['lane']=='Cancelled'

def test_finished_worker_can_be_reviewed_after_exit(world):
    execute(world);execute(world,operation='start',payload={'argv':['true']})
    execute(world,operation='finish',payload={'outcome':'success','artifact':'sha1'})
    assert not world[0].sweep();assert world[3].stops==0
    assert execute(world,operation='heartbeat')['ok']
    world[4][0]+=1801
    assert not world[0].sweep();assert world[2].lane=='Needs Attention'

def test_planning_operations_inactive_and_retry_reset(world):
    world[2].lane='Backlog'
    assert execute(world,operation='plan',payload={'lane':'Todo','ticket_revision':world[2].revision})['lane']=='Todo'
    execute(world,operation='comment',payload={'text':'planning note','ticket_revision':world[2].revision})
    assert execute(world,operation='reevaluate',actor='repair',payload={'reason':'new scope','ticket_revision':world[2].revision})['lane']=='Needs Re-evaluation'
    assert execute(world,operation='override',actor='repair',payload={'reason':'operator accepted','receipt':'decision receipt','ticket_revision':world[2].revision})['completion_kind']=='operator_override'

def test_enrolled_interactive_actor_can_claim_but_cannot_override(world):
    world[1].binding['actors']['interactive']={'role':'interactive','native_user_id':'interactive','runtime':{'adapter':'systemd'}}
    assert execute(world,actor='interactive')['ok']
    with pytest.raises(Rejected,match='operator authority'):
        execute(world,actor='interactive',operation='override',payload={'reason':'cannot override','receipt':'fixture'})

def test_outbox_sequence_follows_board_revisions(world):
    first=execute(world);second=execute(world,operation='comment',payload={'text':'after claim'})
    with world[0].store.connect() as conn:
        rows=conn.execute("SELECT envelope->>'causationid' AS command_id FROM krebs.outbox WHERE envelope->>'causationid'=ANY(%s) ORDER BY sequence",([first['command_id'],second['command_id']],)).fetchall()
    assert [r['command_id'] for r in rows]==[first['command_id'],second['command_id']]

def test_pending_planner_cancel_stops_frozen_unit_without_plane_issue_write(world):
    world[1].binding['manifest']='/tmp/fixture/.project.json'
    world[1].binding['actors']['pm']['runtime']['planner_argv']=['true']
    def launch(*args):raise OSError('unknown launch')
    world[3].start=launch
    c=command(world,operation='planner',ticket_id='_board',payload={})
    with pytest.raises(OSError):world[0].execute(c,'pm')
    stopped=[]
    world[3].stop=lambda p,a:stopped.append(a) or {'stopped':True}
    fix=command(world,operation='reconcile',ticket_id='_board',actor='repair',payload={'operation_id':c['command_id'],'resolution':'cancel','reason':'unit outcome uncertain','receipt':'supervisor evidence'})
    assert world[0].execute(fix,'repair')['ok']
    assert stopped[0]['planning'] is True and stopped[0]['run_id'].startswith('planner-')
    assert world[2].writes==0
