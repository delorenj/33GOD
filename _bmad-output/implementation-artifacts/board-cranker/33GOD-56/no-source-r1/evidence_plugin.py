"""External pytest instrumentation: record actual exception types without changing tests."""
import json
import os
from pathlib import Path
import pytest

REPORT = Path(os.environ['EVIDENCE_REPORT'])
RECORDS = []
COLLECTION = []

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    cls = call.excinfo.type if call.excinfo else None
    RECORDS.append({'nodeid':report.nodeid, 'phase':report.when, 'outcome':report.outcome,
                    'error_class':cls.__module__+'.'+cls.__qualname__ if cls else None,
                    'error_message':str(call.excinfo.value) if call.excinfo else None})

def pytest_collectreport(report):
    if report.failed:
        COLLECTION.append({'nodeid':report.nodeid,'longrepr':str(report.longrepr)})

def pytest_sessionfinish(session, exitstatus):
    with REPORT.open('x') as f:
        json.dump({'exit_status':int(exitstatus),'tests_collected':session.testscollected,
                   'reports':RECORDS,'collection_errors':COLLECTION}, f, indent=2, sort_keys=True)
        f.write('\n')
