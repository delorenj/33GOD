# INFRA-PLANE-KEY-PLAYBOOK

**Date:** 2026-03-11  
**Owner:** Infra (Lenoon)  
**Scope:** Rotate invalid Plane API key for `lasertoast` workspace and restore automation.

## Trigger
Current key in `~/DevCloud/plane.lasertoast.env` fails with:
- `{"detail":"Given API token is not valid"}`

## Owners + Actions

### 1) Key Generation (Owner: Jarad)
1. Log into Plane (`https://plane.delo.sh`).
2. Open: **Settings → API Tokens**.
3. Create new token named: `infra-automation-2026-03`.
4. Scope: workspace `lasertoast` with issues/projects read-write.
5. Copy token once (Plane will not show again).

### 2) Secret Update (Owner: Infra)
1. Backup existing env file:
```bash
cp ~/DevCloud/plane.lasertoast.env ~/DevCloud/plane.lasertoast.env.bak.$(date +%Y%m%d-%H%M%S)
```
2. Replace key in env file:
```bash
sed -i 's/^PLANE_API_KEY=.*/PLANE_API_KEY=<NEW_TOKEN>/g' ~/DevCloud/plane.lasertoast.env
```
3. Sync shell secrets mirror (if present):
```bash
sed -i 's/^export PLANE_API_KEY=.*/export PLANE_API_KEY=<NEW_TOKEN>/g' ~/.config/zshyzsh/secrets.zsh
```
4. Reload shell env:
```bash
set -a && source ~/DevCloud/plane.lasertoast.env && set +a
```

### 3) Verification (Owner: Infra)
Run these exact checks:
```bash
source ~/DevCloud/plane.lasertoast.env

curl -s "https://plane.delo.sh/api/v1/users/me/" \
  -H "X-Api-Key: $PLANE_API_KEY" | jq '{id, email}'

curl -s "https://plane.delo.sh/api/v1/workspaces/lasertoast/projects/" \
  -H "X-Api-Key: $PLANE_API_KEY" | jq '.[0] | {id, name, identifier}'
```

**Success criteria:**
- `users/me` returns user object (not `detail: Given API token is not valid`)
- `projects` returns list JSON (HTTP 200)

### 4) Consumer Validation (Owner: Infra)
Confirm ticket automation works again:
```bash
source ~/DevCloud/plane.lasertoast.env
curl -s "https://plane.delo.sh/api/v1/workspaces/lasertoast/projects/god/issues/" \
  -H "X-Api-Key: $PLANE_API_KEY" | jq '.results | length'
```

Expected: numeric count > 0.

## Rollback
If new key fails or wrong scope:
1. Restore backup env:
```bash
cp <backup-file> ~/DevCloud/plane.lasertoast.env
```
2. Re-source env:
```bash
set -a && source ~/DevCloud/plane.lasertoast.env && set +a
```
3. Re-run verification commands.
4. If still failing, generate a new token and repeat with correct scopes.

## Post-Rotation Hardening
- Store token in 1Password vault `DeLoSecrets` under `plane/lasertoast/api-key`.
- Add expiry reminder: 30 days before token expiration.
- Add health check to heartbeat: weekly `users/me` probe.
