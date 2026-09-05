from receipt_runner import *
from differential_parser import parse
if __name__=='__main__':
    node='tests/gateway/test_systemd_notify.py::test_notify_supports_systemd_abstract_socket'
    d=json.loads((E/'gateway-differential-1.json').read_text())
    assert d['base_only_failures']==[node] and not d['branch_only_failures']
    results={}
    for role,tree in [('head',H),('base',B)]:
        r=run('systemd-isolated-'+role,[PY,'-m','pytest','-q','-o','addopts=',node],tree,controlled=True)
        results[role]={**r,**parse(r['log'])}
    report={'status':'BLOCKED','full_pairs_run':1,'branch_only_failures':[],
      'base_only_failures':d['base_only_failures'],'error_class_changes':[],
      'base_only_error_class':'OSError','base_only_error':'[Errno 98] Address already in use',
      'shared_abstract_socket':'hermes-test-notify','diagnostic_isolated_results':results,
      'cause':'The worker scheduled the complete candidate/base pair concurrently. The baseline test failed binding a fixed Linux abstract socket shared across both processes; separate HERMES_HOME/TMPDIR roots do not isolate that socket namespace.',
      'classification':'All 48 common node/error records match, but the one base-only failure makes exact broad equivalence FAIL. Isolated diagnostic passes cannot replace or normalize the complete pair.',
      'retry_decision':'No second complete pair: user permits it only if candidate-only failures remain, and none do.',
      'publication':'NOT_RUN: differential gate failed; remote and PR title/body unchanged.',
      'next_prerequisite':'A new authorized attempt should execute the complete candidate and baseline suites sequentially to avoid shared abstract socket contention; no product source fix is indicated by this failure.'}
    save('publication-blocked.json',report)
    with (E/'publication-not-run.log').open('x') as f:
        f.write('Authorized command (NOT EXECUTED): git -c core.hooksPath=/tmp/agents-board-cranker-55-postmerge-verification-r2/git/hooks push delorenj HEAD:refs/heads/'+BR+'\n')
        f.write(json.dumps(report,indent=2)+'\n[exit_code=null; not attempted]\n')
    print(json.dumps(report,indent=2),flush=True)
