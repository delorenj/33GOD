"""CandyStore's HTTP client. Context commands need only the Python stdlib."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from candystore.handoff import render_context

DEFAULT_URL = "http://127.0.0.1:8683"
MAX_RESPONSE_BYTES = 256 * 1024
SESSION_ENV = (
    "CODEX_THREAD_ID",
    "CODEX_SESSION_ID",
    "CLAUDE_SESSION_ID",
    "KIMI_SESSION_ID",
    "GEMINI_SESSION_ID",
    "HERMES_SESSION_ID",
)


class ClientError(RuntimeError):
    pass


def project_directory(cwd: str) -> str:
    """Use a worktree's main checkout, retaining submodule repository identity."""
    path = str(Path(cwd).expanduser().resolve())
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                path,
                "rev-parse",
                "--path-format=absolute",
                "--show-toplevel",
                "--git-common-dir",
            ],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return path
    parts = result.stdout.splitlines()
    if result.returncode or len(parts) != 2:
        return path
    root, common = parts
    # A submodule has .git/modules/<name>, not <main-checkout>/.git. Returning
    # its parent here would misattribute CandyStore to the 33GOD parent.
    return str(Path(common).parent) if Path(common).name == ".git" else root


def fetch_context(
    base_url: str,
    *,
    project: str | None,
    cwd: str,
    since: str | None,
    sessions: int,
    exclude_session: str | None,
    timeout: float,
) -> dict:
    url = urlsplit(base_url)
    if url.scheme not in {"http", "https"} or not url.netloc or url.username or url.password:
        raise ClientError("base URL must be an HTTP(S) URL without embedded credentials")
    params = {"sessions": str(sessions)}
    if project:
        params["project"] = project
    else:
        params["cwd"] = project_directory(cwd)
    if since:
        params["since"] = since
    if exclude_session:
        params["exclude_session"] = exclude_session
    request = Request(
        base_url.rstrip("/") + "/context/latest?" + urlencode(params),
        headers={"Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        if exc.code == 400:
            try:
                error = json.loads(exc.read(4096)).get("error", "invalid context request")
            except (ValueError, AttributeError):
                error = "invalid context request"
            raise ClientError(str(error)) from exc
        raise ClientError(f"CandyStore returned HTTP {exc.code}") from exc
    except (URLError, OSError, TimeoutError) as exc:
        raise ClientError("CandyStore is unavailable or timed out") from exc
    if len(body) > MAX_RESPONSE_BYTES:
        raise ClientError("CandyStore context response exceeded the size limit")
    try:
        result = json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ClientError("CandyStore returned invalid JSON") from exc
    if not isinstance(result, dict) or result.get("schema_version") != 1:
        raise ClientError("CandyStore returned an unsupported context response")
    return result


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="candystore", description="CandyStore event history and session handoffs"
    )
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("serve", help="start the ingest/query HTTP server")
    context = commands.add_parser("context", help="recover work across agent CLIs")
    subcommands = context.add_subparsers(dest="context_command", required=True)
    latest = subcommands.add_parser("latest", help="recent sessions in the current project")
    latest.add_argument(
        "--project", help="registry slug or project alias; otherwise detect from cwd"
    )
    latest.add_argument("--cwd", default=os.getcwd(), help="directory for project detection")
    latest.add_argument("--since", help="ISO date/time or duration (24h, 7d); defaults to 30d")
    latest.add_argument("--sessions", type=int, default=3, help="number of sessions (1–10)")
    latest.add_argument(
        "--exclude-session",
        default=next((os.environ[name] for name in SESSION_ENV if os.environ.get(name)), None),
        help="omit this native/correlation ID; defaults to the current agent session",
    )
    latest.add_argument(
        "--json", action="store_true", help="structured evidence instead of Markdown"
    )
    latest.add_argument("--base-url", default=os.environ.get("CANDYSTORE_URL", DEFAULT_URL))
    latest.add_argument("--timeout", type=float, default=5, help="HTTP deadline in seconds")
    return root


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Preserve the original console script's bare invocation. Container startup
    # still uses python -m candystore.main and never enters the CLI parser.
    if not argv or argv == ["serve"]:
        from candystore.main import main as serve

        return serve()
    command_parser = parser()
    args = command_parser.parse_args(argv)
    if not 1 <= args.sessions <= 10:
        command_parser.error("--sessions must be between 1 and 10")
    if not 0 < args.timeout <= 30:
        command_parser.error("--timeout must be greater than 0 and at most 30")
    try:
        response = fetch_context(
            args.base_url,
            project=args.project,
            cwd=args.cwd,
            since=args.since,
            sessions=args.sessions,
            exclude_session=args.exclude_session,
            timeout=args.timeout,
        )
    except ClientError as exc:
        print(f"candystore: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(response, ensure_ascii=False) if args.json else render_context(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
