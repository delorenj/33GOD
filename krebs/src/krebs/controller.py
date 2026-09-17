"""Durable command -> intent -> verified projection -> receipt/outbox.

Session advisory locks serialize a board across multiple committed transactions.
Crash recovery always reads provider state before retrying an uncertain mutation.
"""
import time
import uuid
from datetime import datetime, timezone
from psycopg.types.json import Jsonb
from .contract import Rejected, decide, digest, require, validate

class Controller:
    def __init__(self, store, registry, provider, runtime, clock=time.time):
        self.store, self.registry, self.provider, self.runtime, self.clock = store, registry, provider, runtime, clock

    def execute(self, command, auth):
        validate(command)
        project, actor = self.registry.authenticate(command, auth)
        require(project.get("mode") == "managed" or command["operation"] in {"status", "get"}, "shadow mode forbids mutations")
        with self.store.board_lock(command["project_id"]) as conn:
            prior = conn.execute("SELECT * FROM krebs.commands WHERE command_id=%s OR idempotency_key=%s", (command["command_id"], command["idempotency_key"])).fetchone()
            if prior:
                require(prior["digest"] == digest(command), "idempotency key or command id body conflict")
                if prior["receipt"]["status"] == "accepted":
                    self._recover(conn, project, prior["command_id"])
                    prior = conn.execute("SELECT * FROM krebs.commands WHERE command_id=%s", (prior["command_id"],)).fetchone()
                return prior["receipt"]
            board = self.store.board(conn, project)
            self.provider.verify(project, actor)  # before any provider mutation
            if command["operation"] == "status":
                operation_id = command.get("payload", {}).get("operation_id")
                operation = None
                if operation_id:
                    found = conn.execute("SELECT receipt FROM krebs.commands WHERE command_id=%s AND project_id=%s", (operation_id, command["project_id"])).fetchone()
                    require(found is not None, "operation not found for this project")
                    operation = found["receipt"]
                return {"version": 2, "command_id": command["command_id"], "status": "result", "ok": True, "board": board, "operation": operation}
            require(not board["pending"], "board has an unresolved provider intent")
            require(project.get("legacy_writers_fenced") is True, "legacy writer inventory is not fenced")
            require(project.get("skill_version") and project.get("policy_version") == 2, "runtime skill/policy binding missing")
            require(actor.get("runtime", {}).get("adapter") == "systemd", "runtime stop-proof adapter not enrolled")
            if command["operation"] in {"claim", "takeover", "resume", "create"}:
                require(actor.get("role") in {"pm", "operator"} and (actor.get("role") == "operator" or command["actor_id"] == project.get("pm_actor")), "delegate this board to its owning PM")
            ticket = {"lane": "Backlog", "revision": None} if command["operation"] == "create" else self.provider.ticket(project, actor, command["ticket_id"])
            if command["operation"] == "get":
                return {"version": 2, "command_id": command["command_id"], "status": "result", "ok": True, "ticket": ticket}
            review_rows = conn.execute("SELECT * FROM krebs.reviews WHERE project_id=%s AND ticket_id=%s AND generation=%s", (command["project_id"], command["ticket_id"], command["generation"])).fetchall()
            child_rows = conn.execute("SELECT command_id FROM krebs.commands WHERE receipt->>'lane'='Done' AND receipt->>'ok'='true'").fetchall()
            if command["operation"] == "takeover":
                require(actor.get("role") == "operator", "takeover requires enrolled operator")
                require(command.get("payload", {}).get("reason"), "takeover reason required")
            next_state, action = decide(board, command, self.clock(), ticket, review_rows, [r["command_id"] for r in child_rows])
            if action and action.get("audit_only"):
                return self._audit(conn, command, action)
            accepted = {"version": 2, "command_id": command["command_id"], "status": "accepted", "ok": True}
            plan = {"next": next_state, "action": action, "attempt": board["active"], "actor": command["actor_id"]}
            with conn.transaction():
                conn.execute("INSERT INTO krebs.commands(command_id,idempotency_key,project_id,body,digest,receipt) VALUES(%s,%s,%s,%s,%s,%s)", (command["command_id"], command["idempotency_key"], command["project_id"], Jsonb(command), digest(command), Jsonb(accepted)))
                conn.execute("INSERT INTO krebs.intents(command_id,project_id,plan) VALUES(%s,%s,%s)", (command["command_id"], command["project_id"], Jsonb(plan)))
                board["pending"] = command["command_id"]
                if action and action.get("stop") and board["active"]:
                    board["active"]["revoked"] = True
                self.store.save(conn, board)
            self._recover(conn, project, command["command_id"])
            return conn.execute("SELECT receipt FROM krebs.commands WHERE command_id=%s", (command["command_id"],)).fetchone()["receipt"]

    def _audit(self, conn, command, action):
        receipt = {"version": 2, "command_id": command["command_id"], "ok": False, "status": "audit_only", "project_id": command["project_id"], "ticket_id": command["ticket_id"], "run_id": command["run_id"], "runtime_id": command["runtime_id"], "generation": command["generation"], **action}
        with conn.transaction():
            conn.execute("INSERT INTO krebs.commands(command_id,idempotency_key,project_id,body,digest,receipt) VALUES(%s,%s,%s,%s,%s,%s)", (command["command_id"], command["idempotency_key"], command["project_id"], Jsonb(command), digest(command), Jsonb(receipt)))
            self._record(conn, command, receipt)
        return receipt

    def _recover(self, conn, project, command_id):
        intent = conn.execute("SELECT * FROM krebs.intents WHERE command_id=%s", (command_id,)).fetchone()
        if not intent or intent["verified"]:
            return
        command = conn.execute("SELECT body FROM krebs.commands WHERE command_id=%s", (command_id,)).fetchone()["body"]
        plan, actor = intent["plan"], project["actors"][command["actor_id"]]
        try:
            self.provider.verify(project, actor)
            action, observed = plan["action"], None
            if action and "runtime_start" in action:
                self.runtime.start(project, plan["attempt"], action["runtime_start"])
                action = None
            if action:
                # Always revoke before stopping. Keep capacity held on every error.
                if action.get("stop"):
                    self.runtime.stop(project, plan["attempt"])
                observed = self.provider.reconcile(project, actor, command["ticket_id"], action, command_id)
                if not observed.get("matched"):
                    require(not intent["sent"], "uncertain provider write; readback not matched, operator reconciliation required")
                    conn.execute("UPDATE krebs.intents SET sent=true WHERE command_id=%s", (command_id,))
                    self.provider.apply(project, actor, command["ticket_id"], action, command_id)
                    observed = self.provider.reconcile(project, actor, command["ticket_id"], action, command_id)
                    require(observed.get("matched"), "provider readback mismatch")
            next_state = plan["next"]
            next_state["pending"] = None
            record = next_state["tickets"].get(command["ticket_id"], {})
            if observed and observed.get("revision"):
                record["provider_revision"] = observed["revision"]
            receipt = {"version": 2, "command_id": command_id, "status": "result", "ok": True,
                       "project_id": command["project_id"], "ticket_id": command["ticket_id"],
                       "run_id": command["run_id"], "runtime_id": command["runtime_id"],
                       "operation": command["operation"], "evidence": command.get("payload", {}),
                       "intent_id": command_id, "question": record.get("question"),
                       "requested_actor": command["actor_id"], "applied_native_user": actor["native_user_id"],
                       "revision": next_state["revision"], "generation": next_state["generation"],
                       "lane": record.get("lane"), "provider": observed}
            with conn.transaction():
                self.store.save(conn, next_state)
                if command["operation"] == "review":
                    conn.execute("INSERT INTO krebs.reviews(id,project_id,ticket_id,generation,actor_id,run_id,evidence) VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", (command_id, command["project_id"], command["ticket_id"], command["generation"], command["actor_id"], command["run_id"], Jsonb(command["payload"])))
                conn.execute("UPDATE krebs.intents SET verified=true,error=NULL,updated_at=now() WHERE command_id=%s", (command_id,))
                conn.execute("UPDATE krebs.commands SET receipt=%s WHERE command_id=%s", (Jsonb(receipt), command_id))
                self._record(conn, command, receipt)
        except Exception as exc:
            conn.execute("UPDATE krebs.intents SET error=%s,updated_at=now() WHERE command_id=%s", (type(exc).__name__ + ': ' + str(exc), command_id))
            raise

    def _record(self, conn, command, receipt):
        conn.execute("INSERT INTO krebs.history(project_id,command_id,receipt) VALUES(%s,%s,%s)", (command["project_id"], command["command_id"], Jsonb(receipt)))
        event_id = str(uuid.uuid4())
        from .service import envelope as build_envelope
        envelope = build_envelope("event", "receipt", "recorded", receipt, command["correlation_id"], command["command_id"], event_id)
        envelope["ordering_key"] = command["project_id"]
        conn.execute("INSERT INTO krebs.outbox(id,subject,envelope) VALUES(%s,%s,%s)", (event_id, "bloodbank.evt.lifecycle.receipt.recorded", Jsonb(envelope)))

    def _expire(self, conn, project, board, reason="lease expired"):
        from copy import deepcopy
        old = board["active"]
        actor_id = project.get("controller_actor")
        require(actor_id in project["actors"], "controller repair actor not enrolled; capacity held")
        command_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{project['project_id']}:{old['generation']}:{board['revision']}:{reason}"))
        command = {"version": 2, "operation": "attention", "command_id": command_id,
                   "idempotency_key": command_id, "project_id": project["project_id"],
                   "ticket_id": old["ticket_id"], "actor_id": actor_id,
                   "runtime_id": old["runtime_id"], "run_id": old["run_id"],
                   "generation": old["generation"], "expected_revision": board["revision"],
                   "correlation_id": old["correlation_id"], "causation_id": command_id,
                   "payload": {"reason": reason}}
        next_state = deepcopy(board)
        next_state["active"] = None
        next_state["revision"] += 1
        next_state["tickets"][old["ticket_id"]]["lane"] = "Needs Attention"
        plan = {"next": next_state, "action": {"lane": "Needs Attention", "working": False, "stop": True}, "attempt": old, "actor": actor_id}
        with conn.transaction():
            conn.execute("INSERT INTO krebs.commands(command_id,idempotency_key,project_id,body,digest,receipt) VALUES(%s,%s,%s,%s,%s,%s)", (command_id, command_id, project["project_id"], Jsonb(command), digest(command), Jsonb({"version":2,"status":"accepted","ok":True,"command_id":command_id})))
            conn.execute("INSERT INTO krebs.intents(command_id,project_id,plan) VALUES(%s,%s,%s)", (command_id, project["project_id"], Jsonb(plan)))
            board["pending"] = command_id
            board["active"]["revoked"] = True
            self.store.save(conn, board)
        self._recover(conn, project, command_id)

    def sweep(self):
        with self.store.connect() as conn:
            ids = [r["project_id"] for r in conn.execute("SELECT project_id FROM krebs.boards")]
        errors = []
        for project_id in ids:
            try:
                project = self.registry.project(project_id)
                require(project["mode"] == "managed", "board paused")
                with self.store.board_lock(project_id) as conn:
                    board = self.store.board(conn, project)
                    if board["pending"]:
                        self._recover(conn, project, board["pending"])
                        board = self.store.board(conn, project)
                    if not board["active"]:
                        for ticket_id, record in board["tickets"].items():
                            if record.get("attempt") and record.get("lane") != "Done":
                                old = record["attempt"]
                                observed = self.provider.ticket(project, project["actors"][old["actor_id"]], ticket_id)
                                if observed["lane"] == "Done":
                                    board["active"] = old
                                    self._expire(conn, project, board, "manual Done lacks evidence")
                                    board = self.store.board(conn, project)
                                    break
                    if board["active"]:
                        attempt = board["active"]
                        actor = project["actors"][attempt["actor_id"]]
                        observed = self.provider.ticket(project, actor, attempt["ticket_id"])
                        recorded = board["tickets"][attempt["ticket_id"]]
                        if observed["lane"] != recorded["lane"]:
                            self._expire(conn, project, board, "external provider lane changed")
                        elif recorded.get("dispatched") and not self.runtime.running(project, attempt):
                            self._expire(conn, project, board, "worker exited without lifecycle closeout")
                        elif self.clock() >= attempt["lease_until"]:
                            self._expire(conn, project, board)
            except Exception as exc:
                errors.append({"project_id": project_id, "error": type(exc).__name__})
        return errors
