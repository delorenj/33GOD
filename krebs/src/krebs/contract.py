"""Pure, deterministic execution decisions; adapters supply verified external facts."""
from copy import deepcopy
import hashlib
import json
import uuid

LANES = ('Backlog', 'Needs Re-evaluation', 'Todo', 'In Progress', 'E2E Testing & QA',
         'Ready for Documentation', 'Done', 'Needs Attention', 'Cancelled')
OPERATIONS = {'claim','handoff','complete','attention','resume','release','cancel','takeover',
              'status','heartbeat','finish','review','get','comment','update','create','start',
              'plan','reevaluate','override','reconcile','planner'}
PM_OPERATIONS = {'plan','reevaluate','override','reconcile','create','planner'}

class Rejected(ValueError):
    pass

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def require(condition, message):
    if not condition: raise Rejected(message)

def acceptance_valid(value):
    return (isinstance(value, dict) and isinstance(value.get('profile'), str) and bool(value['profile'].strip())
            and isinstance(value.get('children', []), list)
            and all(isinstance(x,dict) and all(isinstance(x.get(k),str) and x[k] for k in ('command_id','project_id','ticket_id')) for x in value.get('children', [])))

def argv_valid(argv):
    return isinstance(argv, list) and bool(argv) and all(isinstance(x, str) and x and '\0' not in x for x in argv)

def content_revision(ticket):
    return ticket.get('content_revision', ticket.get('revision'))

def validate(command):
    require(isinstance(command, dict), 'command must be an object')
    for key in ('command_id','idempotency_key','project_id','ticket_id','actor_id','runtime_id','run_id','correlation_id','causation_id'):
        require(isinstance(command.get(key), str) and command[key].strip(), f'missing {key}')
    for key in ('command_id','correlation_id','causation_id'):
        try: uuid.UUID(command[key])
        except (ValueError, TypeError, AttributeError): raise Rejected(f'{key} must be UUID')
    require(command.get('version') == 2, 'unsupported command version')
    require(isinstance(command.get('operation'), str) and command['operation'] in OPERATIONS, 'unsupported operation')
    require(type(command.get('expected_revision')) is int and command['expected_revision'] >= 0, 'expected_revision required')
    require(type(command.get('generation')) is int and command['generation'] >= 0, 'generation required')
    require(isinstance(command.get('payload', {}), dict), 'payload must be object')
    try: canonical(command)
    except (ValueError, TypeError): raise Rejected('invalid JSON payload')
    if command['operation'] == 'start': require(argv_valid(command.get('payload', {}).get('argv')), 'worker argv required')

def decide(board, command, now, ticket, reviews=(), children=()):
    state = deepcopy(board)
    op, payload = command['operation'], command.get('payload', {})
    active = state.get('active')
    record = state['tickets'].get(command['ticket_id'], {})
    target_active = bool(active and active['ticket_id'] == command['ticket_id'])
    inactive_pm = op in {'comment','update','cancel'} and not target_active
    operator_op = op in {'override','reevaluate','plan','reconcile','planner'}
    if op in {'status','get'}: return state, None
    if op not in {'claim','resume','takeover','create'} and not inactive_pm and not operator_op:
        if not active or command['generation'] != active['generation'] or (op != 'review' and command['run_id'] != active['run_id']):
            return state, {'audit_only':True, 'reason':'obsolete attempt'}
        require(target_active, 'ticket does not own capacity')
        if op != 'review': require(command['actor_id'] == active['actor_id'], 'attempt belongs to another actor')
        require(now < active['lease_until'], 'lease expired; stop proof required')
        require(not active.get('revoked'), 'attempt authority revoked')
    require(command['expected_revision'] == state['revision'], 'revision conflict')
    action = None
    current_content = content_revision(ticket)
    if inactive_pm or op in {'plan','reevaluate','override'}:
        require(payload.get('ticket_revision') and payload['ticket_revision'] == current_content, 'explicit current ticket revision required')
    if op in {'claim','resume','takeover'}:
        require(not active or op == 'takeover', 'board capacity occupied; stopped proof required')
        if op == 'takeover' and active:
            require(target_active and command['generation'] == active['generation'], 'takeover must target current active ticket/generation')
        require(command['run_id'] not in state.get('used_runs', []), 'run ID already used; create a new run')
        if op == 'resume':
            question = record.get('question', {})
            require(question and question.get('id') == payload.get('question_id') and not question.get('answered'), 'unknown or answered question')
            require(payload.get('answer'), 'answer required')
            question['answered'] = payload['answer']
        else:
            require(not record.get('question') or record['question'].get('answered'), 'open question requires resume with its answer')
            require(op == 'takeover' or ticket['lane'] in {'Todo','Needs Attention'}, 'ticket is not ready')
        require(not record.get('retry_exhausted'), 'retry budget exhausted; operator re-evaluation required')
        require(acceptance_valid(payload.get('acceptance')) and isinstance(payload.get('artifact'), str) and payload['artifact'], 'freeze valid acceptance and artifact before dispatch')
        require(payload.get('ticket_revision') == current_content, 'ticket changed; revalidate readiness')
        state['generation'] += 1
        state.setdefault('used_runs', []).append(command['run_id'])
        active = {'actor_id':command['actor_id'], 'run_id':command['run_id'], 'runtime_id':command['runtime_id'],
                  'ticket_id':command['ticket_id'], 'generation':state['generation'], 'lease_until':now+300,
                  'artifact':payload['artifact'], 'acceptance':payload['acceptance'], 'content_revision':current_content,
                  'ticket_revision':current_content, 'correlation_id':command['correlation_id'], 'revoked':False}
        state['active'] = active
        record.update(lane='In Progress', attempt=active, dispatched=False, outcome=None, retries=record.get('retries',0))
        action = {'lane':'In Progress','working':True,'assign':True,'stop':op=='takeover' and bool(board.get('active'))}
    elif op == 'start':
        require(argv_valid(payload.get('argv')), 'worker argv required')
        require(not record.get('dispatched') and not record.get('outcome'), 'run already dispatched or finished')
        action = {'runtime_start':payload['argv']}
        record['dispatched'] = True
    elif op == 'heartbeat':
        require(record.get('dispatched') or (record.get('outcome') or {}).get('outcome') == 'success', 'undispatched claim cannot renew lease')
        limit = active.get('review_until', now+300)
        require(now < limit, 'PM review lease exhausted')
        active['lease_until'] = min(now+300, limit)
    elif op == 'review':
        require(command['run_id'] != active['run_id'], 'independent reviewer run required')
        require(acceptance_valid(active.get('acceptance')), 'acceptance invalidated; re-evaluate')
        require(payload.get('artifact') == active['artifact'] and payload.get('acceptance') == active['acceptance'], 'review evidence is stale')
        require(payload.get('kind') in {'spec','quality'} and payload.get('passed') is True and payload.get('receipt'), 'review failed or lacks receipt')
    elif op in {'handoff','complete'}:
        require(acceptance_valid(active.get('acceptance')), 'acceptance invalidated; re-evaluate')
        require((record.get('outcome') or {}).get('outcome') == 'success' and record['outcome'].get('artifact') == active['artifact'], 'successful delivered outcome required')
        evidence = payload.get('evidence', {})
        require(isinstance(evidence,dict) and evidence.get('artifact') == active['artifact'] and evidence.get('acceptance') == active['acceptance'], 'evidence is not frozen to current artifact')
        require(current_content == active.get('content_revision', active['ticket_revision']), 'provider content changed; readiness invalidated')
        valid = [r for r in reviews if r['evidence'].get('artifact') == active['artifact'] and r['evidence'].get('acceptance') == active['acceptance'] and r['run_id'] != active['run_id']]
        require({'spec','quality'} <= {r['evidence']['kind'] for r in valid}, 'independent spec and quality reviews required')
        lane = payload.get('lane', 'Done' if op=='complete' else 'E2E Testing & QA')
        require({'In Progress':'E2E Testing & QA','E2E Testing & QA':'Ready for Documentation','Ready for Documentation':'Done'}.get(record.get('lane')) == lane, 'invalid lane progression')
        for name in (['tests'] if lane=='E2E Testing & QA' else ['tests','docs','notebook','skill','main','push','deployment']):
            gate = evidence.get(name, {})
            require(isinstance(gate,dict) and ((gate.get('passed') is True and bool(gate.get('receipt'))) or (gate.get('applicable') is False and bool(gate.get('reason')))), f'missing {name} evidence')
        needed = active['acceptance'].get('children', [])
        require(all(any(all(actual.get(k)==child[k] for k in ('command_id','project_id','ticket_id')) for actual in children) for child in needed), 'child completion receipts not verified')
        if needed: require(evidence.get('integration',{}).get('passed') is True and evidence['integration'].get('receipt'), 'parent integration evidence required')
        record['lane'] = lane
        action = {'lane':lane,'working':lane!='Done','stop':lane=='Done'}
        if lane=='Done': state['active']=None
    elif op in {'attention','release','cancel','finish'}:
        if op=='finish' and payload.get('outcome')=='success':
            require(record.get('dispatched') or active['acceptance'].get('profile')=='non-code', 'successful delivery requires dispatched worker or explicit non-code profile')
            require(isinstance(payload.get('artifact'),str) and payload['artifact'], 'delivered artifact required')
            require(current_content == active['content_revision'], 'provider content changed; readiness invalidated')
            if payload['artifact'] != active['artifact']:
                active['artifact']=payload['artifact']; record['lane']='In Progress'
                action={'lane':'In Progress','working':True}
            record['outcome']=payload
            active['review_until']=now+1800
            active['lease_until']=now+300
        else:
            if op=='finish':
                require(payload.get('classification') in {'recoverable','dependency','terminal'}, 'classify failure')
                if payload['classification']=='recoverable':
                    record['retries']=record.get('retries',0)+1; record['retry_exhausted']=record['retries']>=3
            lane='Cancelled' if op=='cancel' else 'Todo' if op=='release' else 'Needs Attention'
            if op=='attention':
                require(payload.get('question_id') and payload.get('question') and payload.get('context'), 'question id, question and context required')
                require(not record.get('question') or record['question'].get('answered'), 'question already open')
                record['question']={'id':payload['question_id'],'text':payload['question'],'context':payload['context'],'resume_state':record.get('lane')}
            record['lane']=lane
            action={'lane':lane,'working':False,'stop':target_active,'question':record.get('question') if op=='attention' else None}
            if target_active: state['active']=None
    elif op=='comment':
        require(payload.get('text'), 'comment text required')
        action={'comment':payload['text']}
    elif op=='update':
        fields={k:v for k,v in payload.items() if k!='ticket_revision'}
        require(set(fields) <= {'name','description_html'} and bool(fields), 'managed updates cannot bypass lifecycle state')
        action={'update':fields}
        if target_active: active['acceptance']=None
    elif op=='create':
        require(payload.get('name'), 'name required')
        action={'create':{'name':payload['name'],'description_html':payload.get('description_html','')},'lane':'Backlog'}
        record['lane']='Backlog'
    elif op in {'plan','reevaluate','override'}:
        require(not target_active or op=='override', 'active ticket must be stopped before re-planning')
        if op=='plan':
            require(ticket['lane'] in {'Backlog','Needs Re-evaluation','Todo','Needs Attention'}, 'ticket not in planning lanes')
            require(payload.get('lane') in {'Backlog','Needs Re-evaluation','Todo'}, 'invalid planning lane')
            require(not record.get('question') or record['question'].get('answered'), 'open question requires an answer')
            lane=payload['lane']
        elif op=='reevaluate':
            require(payload.get('reason'), 'operator re-evaluation reason required')
            record.update(retries=0,retry_exhausted=False,outcome=None,question=None)
            lane='Needs Re-evaluation'
        else:
            require(payload.get('reason') and payload.get('receipt'), 'operator override requires reason and receipt')
            if target_active: require(command['generation']==active['generation'], 'override generation conflict')
            lane='Done'; record['completion_kind']='operator_override'; record['override']=payload
            if target_active: state['active']=None
        record['lane']=lane
        action={'lane':lane,'working':False,'stop':target_active}
    else:
        raise Rejected('operation requires controller handler')
    state['tickets'][command['ticket_id']]=record
    state['revision']+=1
    return state, action
