import os, sys, json, uuid
# Point AGENT_HOOKS_DIR at bloodbank/services/agent-hooks (the envelope builder).
sys.path.insert(0, os.environ.get('AGENT_HOOKS_DIR', '/tmp/w83/bb/services/agent-hooks'))
from core.envelope import build_envelope
from core.validate import validate_envelope
mode, n = sys.argv[1], int(sys.argv[2])
corr = str(uuid.uuid4())
for i in range(1, n+1):
    e = build_envelope(
        ce_type="bloodbank.conversation.turn.completed", kind="event",
        source="urn:33god:agent:w83-probe", producer="w83-probe", service="w83-probe",
        actor={"type":"agent_cli","cli":"w83-probe","agent_id":"w83.probe"},
        data={"hook":"Stop","outcome":"completed","thread_id":f"w83sim-{mode}","turn_id":f"w83sim-{mode}-{i}",
              "reply_text":f"W83-SIM {mode} #{i}. Completed the enricher failure-path probe: verified behavior, committed 6b2a2bf, tests green. Artifacts: services/turn-enricher/main.py, HOLOC-12.",
              "reply_length":160},
        correlation_id=corr, causation_id=str(uuid.uuid4()), ordering_key=f"w83sim-{mode}.turn-{i}")
    validate_envelope(e)
    print(json.dumps(e, separators=(',',':')))
