"""Consume a controller-created provider step authorization; never grants raw CRUD."""
import json
import os
import sys
from .store import Store
from .contract import require

def authorize(request,store):
    cap=request.get('capability',{})
    with store.connect() as conn,conn.transaction():
        row=conn.execute('SELECT s.*,c.body,b.pending FROM krebs.provider_steps s JOIN krebs.commands c USING(command_id) JOIN krebs.boards b ON b.project_id=c.project_id WHERE s.command_id=%s AND s.step_id=%s FOR UPDATE OF s',(cap.get('command_id'),cap.get('step_id'))).fetchone()
        require(row and row['pending']==cap['command_id'] and row['sent'] and not row['verified'] and not row['authorized'],'no pending unconsumed durable intent')
        require(row['action']==request['action'] and row['binding']==request['binding'] and row['body']['ticket_id']==request['ticket_id'],'intent capability payload mismatch')
        require(request['marker']==cap['command_id']+':'+cap['step_id'],'intent marker mismatch')
        conn.execute('UPDATE krebs.provider_steps SET authorized=true WHERE command_id=%s AND step_id=%s',(cap['command_id'],cap['step_id']))
    return {'authorized':True}

if __name__=='__main__':
    try: print(json.dumps(authorize(json.load(sys.stdin),Store(os.environ['KREBS_DATABASE_URL']))))
    except Exception: print('{"authorized":false}');raise SystemExit(1)
