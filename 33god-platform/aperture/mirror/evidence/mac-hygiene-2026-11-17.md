# Mac hygiene: pjangler residue and config backups (2026-11-17)

Host: Damian's Mac Studio (`hellosubconscious@100.117.109.60`), run from big-chungus over ssh, 2026-11-17 19:14 to 19:16 EST. No secret value was printed; every comparison used sha256 prefixes.

## 1. pjangler registry residue (W4-1 follow-up)

`~/infra/pjangler-registry/registry-runtime.json` and `registry-runtime.loopback-backup.json` held the pre-rotation Postgres password.

Readers checked first:

- `grep -rIl registry-runtime` over `~/infra`, `~/code`, `~/Library/LaunchAgents` and `~/.local/bin` (node_modules and .git excluded). Hits were only mirror evidence docs (`W1-4`, `W3-2.verify`, `W4-1`, `W4-1.verify`, `survey-2026-11-10.json`) and team-inbox BMAD docs that name an unrelated test file (`packages/permission-graph/tests/registry-runtime.test.ts`). No code, plist or script reads either file.
- The live registry LaunchAgent `io.33god.pjangler-registry` runs `env-op-resolve exec --env-file ~/infra/pjangler-registry/registry.env.op -- node ~/code/33GOD/pjangler/dist/project-registry-service.js`. It reads `registry.env.op` (an `op://` ref), not the JSON files. `runner.py` takes the config path as an argument and nothing invokes it.
- `lsof` on both files: no holder.
- The password in both files hashes to `fc314b9942f3`; the live resolved `PGPASSWORD` hashes to `0d72b2c4b3d6`. Both files hold the dead credential.

Done: `rm -P registry-runtime.json registry-runtime.loopback-backup.json` (file sha256 prefixes before removal: `0fb7608c2705`, `f21298e449da`). The PG container was not touched.

Proof:

```
health-before: {"ok":true,"service":"pjangler-project-registry","schema_version":1} http=200
rm-exit=0
zsh:1: no matches found: registry-runtime*
health-after:  {"ok":true,"service":"pjangler-project-registry","schema_version":1} http=200
registry pid 2089 unchanged; pjangler-registry-postgres-1 Up 2 days (healthy)
pj list -> "Projects (7)", exit 0
```

## 2. Config backups holding `secrets.env`

Per-key sha256 comparison of each backup against the live `~/.config/33god/secrets.env` (12 keys). Values were never printed.

| Backup | Keys | Identical | Differ | Missing in live | Action |
|---|---|---|---|---|---|
| `20261116T021149Z-zshrc/secrets.env` | 11 | 11 | none | none | `rm -P` done (sha256 prefix was `a5166a1e3b6e`) |
| `20261116T020642Z-resend/secrets.env` | 11 | 10 | none | `OP_DELOSECRETS_WULYIISB24EHT3WKND6YNF2NYY_CREDENTIAL` | **kept** |

The missing key is the old full-access Resend key line that the 2026-11-15 secrets pass replaced with `OP_DELOSECRETS_ARUIPINTQWSZQMJIUW46ATTHOU_CREDENTIAL` (see `secrets-report-2026-11-15.md` section 1). The resend backup is now the only copy of that retired value on the Mac. Deleting it is an owner call.

Permissions: `find config-backups -type d ! -perm 0700 -exec chmod 0700 {} +`. Result: 49 dirs, 34 non-0700 before, 0 after. Files and the rest of `config-backups` were left as they were.

```
dirs total: 49  non-0700 before: 34
chmod-exit=0
dirs total: 49  non-0700 after: 0
secrets.env copies remaining under config-backups:
-rw-------@ 1 hellosubconscious staff 3136 Nov 15 13:30 ./20261116T020642Z-resend/secrets.env
```

## 2b. Resend backup copy (orchestrator, 2026-11-17)
The kept copy `20261116T020642Z-resend/secrets.env` held Jarad's retired full-access Resend key (`OP_DELOSECRETS_WULYIISB24EHT3WKND6YNF2NYY_CREDENTIAL`). Its sha256 prefix (9a85e99edcff) matches `op://DeLoSecrets/wulyiisb24eht3wknd6ynf2nyy/credential`, so the vault holds it. The copy was removed with `rm -P`. No secrets.env copy is left under config-backups (count 0).
