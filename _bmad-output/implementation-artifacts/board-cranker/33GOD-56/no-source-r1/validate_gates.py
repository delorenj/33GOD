from evidence import *
import re

assert json.loads((E/'gates-pass.json').read_text())['status']=='PASS'
rows = []
for path in sorted(E.glob('*.reports.json')):
    name = path.name.removesuffix('.reports.json')
    raw = json.loads(path.read_text())
    parsed = json.loads((E/(name+'.parsed.json')).read_text())
    rec = json.loads((E/(name+'.exit.json')).read_text())
    text = Path(rec['log']).read_text()
    terminal_failures = set(re.findall(r'^FAILED (\S+)',text,re.M))
    terminal_errors = set(re.findall(r'^ERROR (\S+)',text,re.M))
    plugin_failed = set(parsed['failed_nodes'])
    assert terminal_failures | terminal_errors == plugin_failed, name
    summaries = [line for line in text.splitlines() if re.search(r'\b\d+ passed\b.*\bin \d',line)]
    assert summaries,name
    summary = summaries[-1]
    counts = {word:int(num) for num,word in re.findall(r'(\d+) (failed|passed|skipped|xfailed|xpassed|warnings?)\b',summary)}
    assert counts['passed']==parsed['passed'],(name,counts,parsed['passed'])
    assert raw['exit_status']==rec['exit_code'] and sha(rec['log'])==rec['sha256']
    assert not raw['collection_errors']
    assert rec['process']['all_descendants_gone'] and not rec['process']['before_gateway_processes']
    rows.append({'name':name,'summary':summary,'terminal_counts':counts,
                 'terminal_failed_nodes_match_instrumentation':True,
                 'exception_records':str(path),'exception_records_sha256':sha(path),
                 'log':rec['log'],'log_sha256':rec['sha256']})
records = sorted([json.loads(p.read_text()) for p in E.glob('*.exit.json') if json.loads(p.read_text()).get('sequence_index',0)>0],key=lambda r:r['sequence_index'])
for left,right in zip(records,records[1:]):
    assert left['finished_at'] < right['started_at']
    assert left['finished_monotonic_ns'] < right['started_monotonic_ns']
    assert left['process']['all_descendants_gone']
save('gates-receipt-validation.json',{'status':'PASS','at':utc(),'checks':rows,
     'all_test_and_static_commands_nonoverlapping':True,'sequence':[r['name'] for r in records],
     'scope':'Evidence consistency validation only; not specification or quality/security review.',
     'skip_count_note':'Raw plugin skipped totals are pre-final-wrapper report counts. Terminal summaries above are authoritative for skipped/xfail presentation; failure nodes and passed counts are cross-checked exactly.'})
print('GATE_RECEIPT_VALIDATION_PASS',flush=True)
