# Hermes Per-Repo Template

Reusable scaffold for provisioning a repo-local Hermes runtime in any repository.

## Quick use

```bash
/home/delorenj/code/33GOD/templates/hermes-agent-repo/install.sh /absolute/path/to/repo
```

Optional flags:
- `--agent-name <name>` (default: `hermes`)
- `--provision` (run provision script immediately after install)

Example:

```bash
/home/delorenj/code/33GOD/templates/hermes-agent-repo/install.sh /home/delorenj/code/33GOD/holyfields --provision
```

## What it creates
- `agents/README.md`
- `agents/<agent>/README.md`
- `agents/<agent>/bin/<agent>-<repo-slug>` launcher
- `agents/<agent>/provision.sh`
- `agents/<agent>/runtime/.gitignore`
- Adds runtime ignore block to `<repo>/.gitignore`

## Notes
- Runtime state remains repo-local but git-ignored.
- Secrets/auth/session data are not copied.
