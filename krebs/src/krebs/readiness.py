from .contract import LANES, require, argv_valid
import re

def validate_binding(project):
    require(project.get('policy_version')==2 and project.get('skill_version'),'policy/skill version missing')
    for pin in ('pilot_bundle_sha256','momo_bundle_sha256'):
        require(bool(re.fullmatch('[a-f0-9]{64}',project.get(pin,''))),pin+' missing')
    actors=project.get('actors',{})
    require(isinstance(actors,dict) and actors,'actor enrollment empty')
    require(project.get('pm_actor') in actors and actors[project['pm_actor']].get('role')=='pm','owning PM role missing')
    require(project.get('controller_actor') in actors and actors[project['controller_actor']].get('role')=='operator','controller operator role missing')
    native=set()
    for name,actor in actors.items():
        require(actor.get('role') in {'pm','operator','reviewer','interactive'},'invalid actor role: '+name)
        require(actor.get('native_user_id') and actor['native_user_id'] not in native,'native identity missing or duplicate')
        native.add(actor['native_user_id'])
        require(actor.get('key_ref','').startswith('op://') and actor.get('runtime_id'),'actor credential/runtime missing')
        runtime=actor.get('runtime',{})
        require(runtime.get('adapter')=='systemd' and bool(re.fullmatch('[a-zA-Z0-9_-]+',runtime.get('unit_prefix',''))),'supervisor adapter/prefix missing')
        if name==project['pm_actor']: require(argv_valid(runtime.get('planner_argv')),'PM planner argv missing')
    require(set(LANES)<=set(project.get('states',{})) and all(project['states'][lane] for lane in LANES),'exact lane binding missing')
    require(project.get('working_label') and project.get('legacy_writers_fenced') is True,'writer fences or label binding missing')
