"""Exercise actual CLI configuration across CWD and malformed ownership boundaries."""
import json
import os
from pathlib import Path
import subprocess


def resolve(tmp_path, manifest, *, outside=False, registry=None):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".project.json").write_text(manifest if isinstance(manifest, str) else json.dumps(manifest))
    config = tmp_path / "config"
    config.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    paths = tmp_path / "manifests.json"
    paths.write_text(json.dumps([str(project / ".project.json")]))
    (config / "config.json").write_text(json.dumps({"manifestRegistry": str(registry or paths)}))
    pilot = Path(os.environ.get("KREBS_TEST_PILOT", str(Path(__file__).resolve().parents[3] / "pilot")))
    script = f"""
import {{loadConfig}} from {json.dumps((pilot / 'src/config.js').as_uri())};
try {{
 const cfg=loadConfig(JSON.parse(process.argv[1]));
 console.log(JSON.stringify({{ok:true,mode:cfg.execution?.mode,project:cfg.projectId,board:cfg.board}}));
}} catch(error) {{console.log(JSON.stringify({{ok:false,error:error.message}}));}}
"""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PLANE_", "PILOT_", "KREBS_"))}
    env["PILOT_CONFIG_DIR"] = str(config)
    proc = subprocess.run(["node", "--input-type=module", "-e", script,
                           json.dumps({"board": "fixture-board", "workspace": "fixture", "actor": "fixture-pm"})],
                          cwd=outside_dir if outside else project, env=env,
                          capture_output=True, text=True, check=True, timeout=10)
    return json.loads(proc.stdout)


def manifest():
    return {"project_id": "fixture-project", "ticket_provider": {"type": "plane", "workspace": "fixture", "board_id": "fixture-board"},
            "execution": {"mode": "managed", "actors": {"fixture-pm": {"key_ref": "op://DeLoSecrets/fixture/key"}}}}


def test_explicit_board_outside_project_preserves_managed_authority(tmp_path):
    result = resolve(tmp_path, manifest(), outside=True)
    assert result == {"ok": True, "mode": "managed", "project": "fixture-project", "board": "fixture-board"}


def test_malformed_manifest_never_resolves_as_legacy(tmp_path):
    result = resolve(tmp_path, "{broken-json")
    assert result["ok"] is False
    assert "json" in result["error"].lower() or "manifest" in result["error"].lower()


def test_missing_configured_ownership_registry_fails_closed(tmp_path):
    result = resolve(tmp_path, manifest(), registry=tmp_path / "missing.json")
    assert result["ok"] is False and "registry unavailable" in result["error"]
