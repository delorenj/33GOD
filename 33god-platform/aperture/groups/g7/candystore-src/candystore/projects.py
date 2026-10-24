"""Resolve event working directories to PJangler registry projects.

The trail records where an agent was working, not which project it was working
on. `data.project` is set on 0.17% of rows, so for everything else the project
has to be derived -- and the obvious derivation, the directory basename, is
wrong in ways that are easy to miss. Measured over 7 days it reports git
worktrees (`feat-cartesia-agents`), subdirectories (`.agents`, `dist`, `web`,
`mirror`) and bare-repo suffixes (`james-brennan.git`) as top-level projects.

The registry is the authority: `pjangler list --json` knows each
project's slug, absolute repo path and board prefix. This module matches
directories against it, writes the answers to `project_dir_map`, and leaves
what it cannot resolve visibly unresolved.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

from candystore.db import cursor

logger = logging.getLogger("candystore.projects")

PJANGLER_BIN = "pjangler"
PJANGLER_TIMEOUT_SECONDS = 60

# Separators a sibling worktree directory uses between the project directory
# name and its branch/ticket token: `james-brennan-jimb169`.
_SIBLING_SEPARATORS = ("-", "_")

# Where an event says it was working. `payload.cwd` is the fallback because the
# codex harness nests its hook payload one level deeper than every other
# producer. Shared with query.py so the map's keys and the filter's lookups can
# never be derived two different ways.
WORK_DIR_EXPR = (
    "COALESCE(NULLIF(data->>'working_directory', ''), NULLIF(data->'payload'->>'cwd', ''))"
)


class RegistryError(RuntimeError):
    """The registry could not be read. Distinct from "the registry is empty":
    syncing against an empty registry would mark every directory unresolved and
    silently erase a working map."""


@dataclass(frozen=True)
class Project:
    slug: str
    name: str
    repo_path: str
    ticket_prefix: str

    @property
    def dir_name(self) -> str:
        return self.repo_path.rstrip("/").rsplit("/", 1)[-1]


def load_registry() -> list[Project]:
    """Read the PJangler project registry.

    Shells the CLI rather than reading its state file: the file's location and
    schema are PJangler's business, and `--json` is the contract it publishes.
    """
    if shutil.which(PJANGLER_BIN) is None:
        raise RegistryError(f"{PJANGLER_BIN} is not on PATH")
    try:
        completed = subprocess.run(  # noqa: S603 - fixed binary, no shell, no user input
            [PJANGLER_BIN, "list", "--json"],
            capture_output=True,
            text=True,
            timeout=PJANGLER_TIMEOUT_SECONDS,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RegistryError(
            f"{PJANGLER_BIN} list --json failed: {exc.stderr.strip()}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RegistryError(f"{PJANGLER_BIN} list --json timed out") from exc

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RegistryError(f"{PJANGLER_BIN} returned invalid JSON: {exc}") from exc

    return parse_registry(payload)


def parse_registry(payload: dict) -> list[Project]:
    """Turn the registry payload into Projects. Pure, so the matching rules are
    testable without pjangler installed."""
    raw = payload.get("projects")
    if not isinstance(raw, dict):
        raise RegistryError("registry payload has no 'projects' object")

    projects: list[Project] = []
    for slug, record in raw.items():
        if not isinstance(record, dict):
            continue
        repo_path = (record.get("repo_path") or "").rstrip("/")
        if not repo_path:
            # A project with no path cannot match a directory. Skipping it is
            # right; doing so silently is not.
            logger.warning("registry project %s has no repo_path; skipped", slug)
            continue
        provider = record.get("ticket_provider") or {}
        projects.append(
            Project(
                slug=slug,
                name=_label(record.get("name"), slug),
                repo_path=repo_path,
                ticket_prefix=(provider.get("identifier") or "").strip(),
            )
        )
    if not projects:
        raise RegistryError("registry contains no projects with a repo_path")
    return projects


def _label(name: Any, slug: str) -> str:
    """A name a picker can render, falling back to the slug.

    `or slug` is not enough: the 33GOD project's registry name is literally
    ".", which is truthy and renders as a bullet in a dropdown. Anything with
    no alphanumeric character in it is not a label.
    """
    text = (name or "").strip()
    return text if any(char.isalnum() for char in text) else slug


def resolve(work_dir: str, projects: list[Project]) -> tuple[str | None, str]:
    """Resolve one working directory to (slug, rule).

    Returns (None, "unresolved") rather than guessing. On an audit trail a
    wrong attribution is worse than a visible gap: it silently files one
    project's history under another, and nothing downstream can tell.
    """
    path = (work_dir or "").rstrip("/")
    if not path:
        return None, "unresolved"

    # R1 -- the directory is the repo or lives inside it. Longest match wins,
    # because /home/delorenj/code/33GOD is a prefix of four other registry
    # paths and the innermost project is the right answer.
    #
    # The `/` boundary is the whole trick. A bare `startswith` makes
    # /home/delorenj/code/intelliforia a prefix of
    # /home/delorenj/code/intelliforia-mobile, which quietly files every mobile
    # event under the web project -- and both are real, separately registered
    # projects, so nothing would look wrong.
    best: Project | None = None
    for project in projects:
        if path == project.repo_path or path.startswith(project.repo_path + "/"):
            if best is None or len(project.repo_path) > len(best.repo_path):
                best = project
    if best is not None:
        return best.slug, "repo-path" if path == best.repo_path else "repo-subpath"

    # R2 -- a sibling worktree: `<repo-dir>-<token>` next to the repo rather
    # than inside it, e.g. /home/delorenj/code/james-brennan-jimb169.
    #
    # R1 has already failed, so this cannot steal a directory that is itself a
    # registered project. The token must still start with the project's board
    # prefix (`jimb169` against JIMB) -- that is what makes this a confirmation
    # rather than a guess, and it is why a future real project named `foo-bar`
    # beside a registered `foo` is left unresolved instead of absorbed.
    for project in sorted(projects, key=lambda p: -len(p.repo_path)):
        if not project.ticket_prefix:
            continue
        for separator in _SIBLING_SEPARATORS:
            stem = project.repo_path + separator
            if not path.startswith(stem):
                continue
            token = path[len(stem) :]
            if token and token.lower().startswith(project.ticket_prefix.lower()):
                return project.slug, "sibling-worktree"

    return None, "unresolved"


def aliases_for(project: Project) -> dict[str, str]:
    """Every name that unambiguously means this project, lowercased.

    Three sources, because the trail refers to a project by whichever one the
    producer happened to have: the registry slug, the repo directory name (the
    Plane webhook's `data.repo` uses this -- `bloodbank`, not `bb`), and the
    display name. Collisions between projects are dropped by the caller rather
    than resolved arbitrarily; guessing which project someone meant is exactly
    the failure this whole subsystem exists to avoid.
    """
    candidates = {
        project.slug.lower(): "slug",
        project.dir_name.lower(): "dir_name",
        project.name.lower(): "name",
    }
    return {alias: source for alias, source in candidates.items() if alias}


def build_alias_map(projects: list[Project]) -> dict[str, tuple[str, str]]:
    """alias -> (slug, source), with ambiguous aliases removed."""
    owners: dict[str, set[str]] = {}
    sources: dict[str, str] = {}
    for project in projects:
        for alias, source in aliases_for(project).items():
            owners.setdefault(alias, set()).add(project.slug)
            # A slug is the most authoritative source for an alias, so it wins
            # the attribution when several projects offer the same string.
            if alias not in sources or source == "slug":
                sources[alias] = source

    resolved: dict[str, tuple[str, str]] = {}
    for alias, slugs in owners.items():
        if len(slugs) > 1:
            logger.warning(
                "alias %r claimed by %s; dropped rather than guessed",
                alias,
                ", ".join(sorted(slugs)),
            )
            continue
        resolved[alias] = (next(iter(slugs)), sources[alias])
    return resolved


def observed_work_dirs() -> dict[str, int]:
    """Every distinct working directory in the trail, with its event count."""
    sql = f"""
    SELECT {WORK_DIR_EXPR} AS work_dir, COUNT(*) AS seen
    FROM events
    WHERE {WORK_DIR_EXPR} IS NOT NULL
    GROUP BY 1
    """
    with cursor() as cur:
        cur.execute(sql)
        return {row[0]: row[1] for row in cur.fetchall()}


def sync(projects: list[Project] | None = None) -> dict[str, int]:
    """Bring `project_dir_map` up to date with the registry and the trail.

    Idempotent, and re-resolves every directory rather than only new ones: a
    project registered today has to be able to claim directories that were
    marked unresolved yesterday, which is the whole point of the map being data
    instead of a migration.
    """
    projects = projects if projects is not None else load_registry()
    observed = observed_work_dirs()

    rows = []
    for work_dir, seen in observed.items():
        slug, rule = resolve(work_dir, projects)
        rows.append((work_dir, slug, rule, seen))

    with cursor() as cur:
        # Both tables in one transaction, so a reader never sees a registry
        # that disagrees with the map built from it.
        cur.executemany(
            """
            INSERT INTO projects (slug, name, repo_path, ticket_prefix, synced_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (slug) DO UPDATE
               SET name = EXCLUDED.name,
                   repo_path = EXCLUDED.repo_path,
                   ticket_prefix = EXCLUDED.ticket_prefix,
                   synced_at = NOW()
            """,
            [(p.slug, p.name, p.repo_path, p.ticket_prefix) for p in projects],
        )
        # A project removed from the registry has to leave the projection too,
        # or the picker keeps offering something that no longer exists.
        cur.execute(
            "DELETE FROM projects WHERE slug <> ALL(%s)",
            ([p.slug for p in projects],),
        )
        alias_map = build_alias_map(projects)
        cur.executemany(
            "INSERT INTO project_alias (alias, slug, source) VALUES (%s, %s, %s) "
            "ON CONFLICT (alias) DO UPDATE SET slug = EXCLUDED.slug, source = EXCLUDED.source",
            [(alias, slug, source) for alias, (slug, source) in alias_map.items()],
        )
        cur.execute(
            "DELETE FROM project_alias WHERE alias <> ALL(%s)",
            (list(alias_map),),
        )
        cur.executemany(
            """
            INSERT INTO project_dir_map (work_dir, slug, rule, seen, resolved_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (work_dir) DO UPDATE
               SET slug = EXCLUDED.slug,
                   rule = EXCLUDED.rule,
                   seen = EXCLUDED.seen,
                   resolved_at = NOW()
            """,
            rows,
        )
        cur.execute("SELECT COUNT(*), COUNT(slug) FROM project_dir_map")
        total, resolved = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM project_alias")
        alias_rows = cur.fetchone()[0]

    counts = {
        "directories": len(rows),
        "resolved": sum(1 for row in rows if row[1]),
        "unresolved": sum(1 for row in rows if not row[1]),
        "events_resolved": sum(row[3] for row in rows if row[1]),
        "events_unresolved": sum(row[3] for row in rows if not row[1]),
        "map_rows": total,
        "map_resolved": resolved,
        "aliases": alias_rows,
    }
    logger.info("project:sync %s", counts)
    return counts


def main() -> int:
    logging.basicConfig(level="INFO", format="%(message)s")
    try:
        counts = sync()
    except RegistryError as exc:
        logger.error("project:sync failed: %s", exc)
        return 1

    total_events = counts["events_resolved"] + counts["events_unresolved"]
    share = 100.0 * counts["events_resolved"] / total_events if total_events else 0.0
    print(
        f"{counts['directories']} directories: "
        f"{counts['resolved']} resolved, {counts['unresolved']} unresolved"
    )
    print(f"{share:.2f}% of {total_events:,} placed events resolve to a registry project")

    if counts["unresolved"]:
        with cursor() as cur:
            cur.execute(
                "SELECT work_dir, seen FROM project_dir_map "
                "WHERE slug IS NULL ORDER BY seen DESC LIMIT 10"
            )
            worst = cur.fetchall()
        print("\nworst unresolved (register the repo in pjangler, then re-run):")
        for work_dir, seen in worst:
            print(f"  {seen:>8,}  {work_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
