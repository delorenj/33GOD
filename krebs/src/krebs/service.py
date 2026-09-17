"""One supervised execution controller; no HTTP mutation surface."""
import argparse
import asyncio
import hashlib
import hmac
import json
import os
from pathlib import Path
import uuid
from datetime import datetime, timezone
import nats
from nats.js.api import ConsumerConfig, AckPolicy
from .adapters import Registry, PilotProvider, Runtime, secret
from .contract import canonical, require
from .controller import Controller
from .store import Store

COMMAND_SUBJECT = 'bloodbank.cmd.lifecycle.task.invoke'
REPLY_SUBJECT = 'bloodbank.rpy.lifecycle.task.invoke'

def envelope(kind, entity, action, data, correlation, causation, event_id=None):
    typ = f'bloodbank.lifecycle.{entity}.{action}'
    return {'specversion':'1.0', 'id':event_id or str(uuid.uuid4()), 'source':'urn:33god:krebs',
            'time':datetime.now(timezone.utc).isoformat(), 'type':typ, 'kind':kind, 'domain':'lifecycle',
            'producer':'krebs-controller', 'service':'krebs',
            'subject':f'bloodbank.{dict(event="evt", reply="rpy", command="cmd")[kind]}.lifecycle.{entity}.{action}',
            'actor':{'type':'service', 'agent_id':'krebs-controller', 'cli':'service'}, 'data':data,
            'datacontenttype':'application/json', 'dataschema':f'apicurio://holyfields/{typ}/versions/2',
            'schemaref':f'{typ}.v2', 'correlationid':correlation, 'causationid':causation}

async def publish_outbox(store, js):
    with store.connect() as conn:
        rows = conn.execute('SELECT * FROM krebs.outbox WHERE published_at IS NULL ORDER BY id LIMIT 100').fetchall()
    for row in rows:
        # JetStream acknowledgement, not flush, proves durable bus storage. Same ID on retries.
        await js.publish(row['subject'], canonical(row['envelope']).encode(), headers={'Nats-Msg-Id':row['id']})
        with store.connect() as conn:
            conn.execute('UPDATE krebs.outbox SET published_at=now(),attempts=attempts+1 WHERE id=%s', (row['id'],))

async def serve(controller):
    nc = await nats.connect(os.environ.get('NATS_URL', 'nats://localhost:4222'), token=os.environ.get('NATS_TOKEN'))
    js = nc.jetstream()
    sub = await js.pull_subscribe(COMMAND_SUBJECT, durable='krebs-execution-v2', config=ConsumerConfig(ack_policy=AckPolicy.EXPLICIT, ack_wait=180, max_ack_pending=1))
    async def ingress():
        while True:
            try:
                messages = await sub.fetch(1, timeout=5)
            except TimeoutError:
                continue
            for message in messages:
                auth_project = auth_actor = command = None
                try:
                    raw = json.loads(message.data)
                    require(raw['subject'] == COMMAND_SUBJECT and raw['type'] == 'bloodbank.lifecycle.task.invoke', 'invalid command envelope')
                    command = raw['data']['command']; auth = raw['data']['auth']
                    require(raw['command_id'] == command['command_id'], 'envelope command id mismatch')
                    auth_project, auth_actor = await asyncio.to_thread(controller.registry.authenticate, command, auth)
                    receipt = await asyncio.to_thread(controller.execute, command, auth)
                except Exception as exc:
                    receipt = {'version':2, 'command_id':command.get('command_id') if command else None,
                               'project_id':command.get('project_id') if command else None, 'ticket_id':command.get('ticket_id') if command else None, 'ok':False, 'status':'rejected', 'error':str(exc)}
                if auth_actor:
                    wire = canonical(receipt)
                    key = await asyncio.to_thread(secret, auth_actor['key_ref'])
                    data = {'wire':wire, 'signature':hmac.new(key.encode(), wire.encode(), hashlib.sha256).hexdigest()}
                    reply = envelope('reply', 'task', 'invoke', data, command['correlation_id'], command['command_id'])
                    await nc.publish(REPLY_SUBJECT, canonical(reply).encode())
                    await nc.flush()
                # Failed/uncertain accepted intents remain in Postgres for sweep/retry.
                await message.ack()
    async def recovery():
        while True:
            await asyncio.to_thread(controller.sweep)
            try:
                await publish_outbox(controller.store, js)
            except Exception:
                pass  # no published marker; retry persisted event with original provenance
            await asyncio.sleep(60)
    try:
        await asyncio.gather(ingress(), recovery())
    finally:
        await nc.drain()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['migrate','serve','health','reconcile','readiness'])
    args = parser.parse_args()
    store = Store(os.environ['KREBS_DATABASE_URL'])
    registry = Registry(json.loads(os.environ.get('KREBS_MANIFESTS', '[]')))
    provider = PilotProvider(os.environ.get('KREBS_PILOT_HELPER', '/opt/pilot/src/provider-helper.js'))
    controller = Controller(store, registry, provider, Runtime())
    if args.operation == 'migrate': store.migrate()
    elif args.operation == 'serve': asyncio.run(serve(controller))
    elif args.operation == 'reconcile': print(canonical(controller.sweep()))
    elif args.operation == 'health':
        with store.connect() as conn:
            conn.execute('SELECT 1 FROM krebs.boards LIMIT 1')
        print('{"ok":true}')
    elif args.operation == 'readiness':
        results=[]
        for path in registry.paths:
            doc=json.loads(Path(path).read_text()); pid=doc.get('project_id')
            try:
                project=registry.project(pid)
                require(project.get('legacy_writers_fenced') is True, 'legacy writers not fenced')
                require(project.get('policy_version') == 2 and project.get('skill_version'), 'policy/skill not pinned')
                require(project.get('pm_actor') in project.get('actors',{}), 'PM not enrolled')
                for actor in project['actors'].values():
                    require(actor.get('runtime',{}).get('adapter') == 'systemd', 'stop-proof runtime missing')
                    provider.verify(project, actor)
                results.append({'project_id':pid,'ready':True,'mode':project['mode']})
            except Exception as exc: results.append({'project_id':pid,'ready':False,'error':str(exc)})
        print(canonical(results))
        if not results or any(not r['ready'] for r in results): raise SystemExit(1)
