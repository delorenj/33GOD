#!/usr/bin/env python3
"""
Rererere Heartbeat Worker — 10-minute Intelliforia team crank

Polls for heartbeat dispatches from the router and executes checks.
Designed to run in background via systemd timer or cron.

Usage:
    python3 rererere_heartbeat_worker.py

Expected heartbeat dispatch payload:
    {
        "check_id": "intelliforia_team_crank",
        "agent": "rererere",
        "session_key": "agent:work:main",
        "timestamp": "2026-03-05T13:00:00Z"
    }
"""
import asyncio
import json
import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Paths
WORKSPACE = Path.home() / ".openclaw" / "workspace-rererere"
HEARTBEAT_LOG = WORKSPACE / "heartbeat_execution.log"
STATUS_FILE = WORKSPACE / "team_status.json"
TRINOTE_REPO = Path.home() / "code" / "trinote2.0"
INTELLIFORIA_REPO = Path.home() / "code" / "intelliforia"


def log_msg(msg: str):
    """Append timestamped message to heartbeat log."""
    timestamp = datetime.now(timezone.utc).isoformat()
    line = f"[{timestamp}] {msg}\n"
    HEARTBEAT_LOG.write_text(
        HEARTBEAT_LOG.read_text() + line if HEARTBEAT_LOG.exists() else line
    )
    print(line.strip())


def run_cmd(cmd: str, cwd: Path = TRINOTE_REPO) -> tuple[str, int]:
    """Run shell command, return (output, exit_code)."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 124
    except Exception as e:
        return f"ERROR: {e}", 1


async def check_open_prs() -> dict:
    """Check open PRs on intelliforia."""
    output, code = run_cmd("gh pr list --state open --json number,title,author,reviewDecision --limit 10", cwd=INTELLIFORIA_REPO)
    if code != 0:
        return {"status": "error", "message": output}
    
    try:
        prs = json.loads(output)
        review_needed = [pr for pr in prs if pr.get("reviewDecision") in [None, "REVIEW_REQUIRED", "CHANGES_REQUESTED"]]
        return {
            "status": "ok",
            "total_open": len(prs),
            "review_needed": len(review_needed),
            "prs": review_needed[:3],  # Top 3
        }
    except json.JSONDecodeError:
        return {"status": "error", "message": "Failed to parse PR list"}


async def check_ci_status() -> dict:
    """Check latest CI runs on main."""
    output, code = run_cmd("gh run list --branch main --limit 3 --json status,conclusion,name", cwd=INTELLIFORIA_REPO)
    if code != 0:
        return {"status": "error", "message": output}
    
    try:
        runs = json.loads(output)
        failing = [r for r in runs if r.get("conclusion") == "failure"]
        return {
            "status": "ok",
            "latest_runs": len(runs),
            "failing": len(failing),
            "names": [r.get("name") for r in failing],
        }
    except json.JSONDecodeError:
        return {"status": "error", "message": "Failed to parse CI runs"}


async def check_plane_tickets() -> dict:
    """Check assigned Plane tickets (via mise task or API)."""
    # TODO: Integrate with Plane API once credentials are available
    return {"status": "pending", "message": "Plane integration not yet configured"}


async def execute_team_crank() -> dict:
    """Execute full team crank check."""
    log_msg("=== Starting Intelliforia Team Crank ===")
    
    prs = await check_open_prs()
    ci = await check_ci_status()
    tickets = await check_plane_tickets()
    
    # Determine active agents (for now, just rererere)
    active_agents = ["rererere"]
    
    # Determine next actions
    next_actions = []
    if prs.get("review_needed", 0) > 0:
        next_actions.append(f"Review {prs['review_needed']} PR(s)")
    if ci.get("failing", 0) > 0:
        next_actions.append(f"Fix {ci['failing']} failing CI run(s)")
    if not next_actions:
        next_actions.append("No urgent work — monitoring")
    
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "check": "intelliforia_team_crank",
        "status": "complete",
        "prs": prs,
        "ci": ci,
        "tickets": tickets,
        "active_agents": active_agents,
        "next_actions": next_actions,
    }
    
    # Write status file
    STATUS_FILE.write_text(json.dumps(result, indent=2))
    
    # Log summary
    summary = f"PRs:{prs.get('review_needed',0)} CI_fails:{ci.get('failing',0)} Next:{','.join(next_actions)}"
    log_msg(f"Team crank complete — {summary}")
    
    return result


async def main():
    """Main execution loop."""
    try:
        result = await execute_team_crank()
        
        # Print 1-line status for main session
        summary = (
            f"[CRANK] {result['timestamp']} | "
            f"Active: {','.join(result['active_agents'])} | "
            f"{', '.join(result['next_actions'])}"
        )
        print(summary)
        
        sys.exit(0)
    except Exception as e:
        log_msg(f"ERROR: {e}")
        print(f"[CRANK ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
