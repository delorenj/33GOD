from receipt_runner import *

def parse(log):
    text=pathlib.Path(log).read_text()
    summaries=re.findall(r'^((?:\d+ (?:failed|passed|skipped|xfailed|xpassed|deselected|warnings?|errors?),? ?)+ in [^\n]+)$',text,re.M)
    assert summaries, f'No complete pytest terminal summary in {log}'
    summary=summaries[-1].split('/home/delorenj/.hermes/hermes-agent/.venv/',1)[0]
    failures=[]
    headers=list(re.finditer(r'^_+ (.+?) _+$',text,re.M))
    blocks=[(m[1],text[m.end():headers[i+1].start() if i+1<len(headers) else text.find('short test summary info',m.end())]) for i,m in enumerate(headers)]
    lines=re.findall(r'^(FAILED|ERROR) (tests/[^\n]+)$',text,re.M)
    for outcome,line in lines:
        line=re.sub(r'/home/delorenj/\.hermes/hermes-agent/\.venv/[^\n]*\.py:\d+: \w+Warning:.*$', '', line)
        node,_,message=line.partition(' - ')
        label='.'.join(node.split('::')[1:])
        candidates=[b for title,b in blocks if title==label]
        if len(candidates)>1:
            candidates=[b for b in candidates if re.search(r'^'+re.escape(node.split('::')[0])+r':\d+:',b,re.M)]
        classes=[]
        if len(candidates)==1:
            b=candidates[0]
            classes=re.findall(r'^\S+\.py:\d+: ([\w.]+)\s*$',b,re.M)
            if not classes:
                classes=re.findall(r'^E\s+([\w.]+):',b,re.M)
        if classes:
            error=classes[-1].rsplit('.',1)[-1]
        else:
            m=re.match(r'([\w.]+(?:Error|Exception)|Failed|Timeout|SystemExit)\b',message)
            assert m, f'Unresolved error class: {node} in {log}'
            error=m[1].rsplit('.',1)[-1]
        failures.append({'node_id':node,'error_class':error,'outcome':outcome})
    count=sum(int(m[1]) for m in re.finditer(r'(\d+) (failed|errors?)\b',summary))
    assert count==len(failures),(summary,len(failures),log)
    assert len(set(f['node_id'] for f in failures))==len(failures)
    failures.sort(key=lambda f:f['node_id'])
    canonical=json.dumps([{'node_id':f['node_id'],'error_class':f['error_class']} for f in failures],sort_keys=True,separators=(',',':'))
    return {'summary':summary,'failures':failures,'failure_count':len(failures),'canonical_node_error_json':canonical,'canonical_node_error_sha256':hashlib.sha256(canonical.encode()).hexdigest()}

def differential(attempt):
    pairs={}
    for role in ['head','base']:
        receipt=json.loads((E/('gateway-'+role+'-'+str(attempt)+'.json')).read_text())
        pairs[role]={**receipt,**parse(receipt['log']),'sha':C if role=='head' else BASE}
    h={f['node_id']:f['error_class'] for f in pairs['head']['failures']}
    b={f['node_id']:f['error_class'] for f in pairs['base']['failures']}
    branch=sorted(h.keys()-b.keys()); base=sorted(b.keys()-h.keys())
    changes=[{'node_id':n,'head_error_class':h[n],'base_error_class':b[n]} for n in sorted(h.keys()&b.keys()) if h[n]!=b[n]]
    envh=pairs['head']['environment']; envb=pairs['base']['environment']
    normalized=lambda env:{k:v for k,v in env.items() if k not in ['HERMES_HOME','TMPDIR']}
    assert normalized(envh)==normalized(envb),'Environments differ beyond isolated state roots'
    assert pairs['head']['argv']==pairs['base']['argv']==[PY,'-m','pytest','-q','-o','addopts=','tests/gateway']
    equivalent=not branch and not base and not changes
    complete=all(pairs[r]['exit_code'] in [0,1] for r in pairs)
    report={'attempt':attempt,**pairs,'branch_only_failures':branch,'base_only_failures':base,'error_class_changes':changes,'byte_equal_node_error_signatures':pairs['head']['canonical_node_error_json']==pairs['base']['canonical_node_error_json'],'status':'PASS' if equivalent and complete else 'FAIL','environment_equivalent_except_isolation_roots':True}
    save('gateway-differential-'+str(attempt)+'.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['head','base']},indent=2))
    return report

if __name__=='__main__':
    if sys.argv[1]=='prior-parser-validation':
        for name in ['gateway-head.log','gateway-baseline.log']:
            log=E.parent.parent/'33GOD-53'/'integration-conflict-r3'/name
            result=parse(log)
            print(name,result['summary'],result['failure_count'])
        save('parser-prior-validation.json',{'status':'PASS','inputs':['33GOD-53/integration-conflict-r3/gateway-head.log','33GOD-53/integration-conflict-r3/gateway-baseline.log'],'purpose':'Validate complete node/error extraction only; no reuse as current classification'})
    else: differential(int(sys.argv[1]))
