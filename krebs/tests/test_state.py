"""Pure tests never need Postgres, NATS or a native credential."""
from copy import deepcopy
import uuid
import pytest
from krebs.contract import decide,validate,Rejected

def fixture():
    uid=str(uuid.uuid4())
    board={'revision':0,'generation':0,'tickets':{},'active':None,'used_runs':[]}
    command={'version':2,'operation':'claim','command_id':uid,'idempotency_key':uid,'project_id':'p','ticket_id':'t','actor_id':'pm','runtime_id':'host','run_id':'r','expected_revision':0,'generation':0,'correlation_id':uid,'causation_id':uid,'payload':{'acceptance':{'profile':'default'},'artifact':'sha','ticket_revision':'content'}}
    return board,command,{'lane':'Todo','content_revision':'content'}

@pytest.mark.parametrize('bad',[None,[],['x'],'x',42,{}, {'operation':[]}])
def test_poison_shapes_are_rejected(bad):
    with pytest.raises(Rejected):validate(bad)

@pytest.mark.parametrize('argv',[None,[],[''],[1],['bad\0arg']])
def test_bad_argv_rejected_before_intent(argv):
    _,c,_=fixture();c.update(operation='start',payload={'argv':argv})
    with pytest.raises(Rejected):validate(c)

def test_undispatched_heartbeat_cannot_extend_lease():
    b,c,t=fixture();b,_=decide(b,c,1000,t)
    c.update(operation='heartbeat',generation=1,expected_revision=1,payload={})
    with pytest.raises(Rejected,match='undispatched'):decide(b,c,1001,t)

def test_null_acceptance_and_no_delivered_outcome_reject_closeout():
    b,c,t=fixture();b,_=decide(b,c,1000,t)
    c.update(operation='complete',generation=1,expected_revision=1,payload={})
    with pytest.raises(Rejected,match='successful delivered'):decide(b,c,1001,t)
    b['active']['acceptance']=None
    with pytest.raises(Rejected,match='invalidated'):decide(b,c,1001,t)

def test_reused_run_and_takeover_other_ticket_rejected():
    b,c,t=fixture();b,_=decide(b,c,1000,t)
    c.update(operation='takeover',generation=1,expected_revision=1,ticket_id='other',run_id='new')
    with pytest.raises(Rejected,match='target'):decide(b,c,1001,t)
    b['active']=None;c.update(operation='claim',ticket_id='t',run_id='r')
    with pytest.raises(Rejected,match='already used'):decide(b,c,1001,t)
