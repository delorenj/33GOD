from differential_parser import *
while not (E/'gateway-base-1.json').exists():
    time.sleep(5)
r1=differential(1)
reports=[r1]
if r1['branch_only_failures']:
    pytest=[PY,'-m','pytest','-q','-o','addopts=','tests/gateway']
    run('gateway-head-2',pytest,H,controlled=True,attempt=2)
    run('gateway-base-2',pytest,B,controlled=True,attempt=2)
    reports.append(differential(2))
last=reports[-1]
result={'full_pairs_run':len(reports),'pair_receipts':[str(E/('gateway-differential-'+str(i+1)+'.json')) for i in range(len(reports))],
        'status':last['status'],'branch_only_failures':last['branch_only_failures'],'base_only_failures':last['base_only_failures'],
        'error_class_changes':last['error_class_changes'],'persistent_candidate_only_failures':sorted(set(reports[0]['branch_only_failures'])&set(last['branch_only_failures'])),
        'head_failures':last['head']['failures'],'base_failures':last['base']['failures'],'head_summary':last['head']['summary'],'base_summary':last['base']['summary'],
        'target_node':NODE,'target_head_isolated':[],'target_base_isolated':[]}
for role in ['head','base']:
    for attempt in range(1,4):
        receipt=json.loads((E/('target-'+role+'-'+str(attempt)+'.json')).read_text())
        p=parse(receipt['log'])
        result['target_'+role+'_isolated'].append({**receipt,'error_class':p['failures'][0]['error_class'] if p['failures'] else 'NONE','summary':p['summary']})
result['rationale']='Exact full-suite failed node/error-class signatures match with no remaining differential; focused/static gates must independently pass before publication.' if result['status']=='PASS' else 'Full-suite differential remains nonempty; publication forbidden. Isolated-node passes do not waive candidate-only full-suite failures.'
save('full-comparison.json',result)
print(json.dumps(result,indent=2),flush=True)
