# Security Incident Report: Credential Leak Remediation

> **Date**: 2026-02-13  
> **Severity**: CRITICAL  
> **Status**: CONTAINED  
> **Owner**: Lenoon (Infrastructure Domain)  

---

## Incident Summary

RabbitMQ password `REDACTED` was found hardcoded in 19+ files across the 33GOD codebase and pushed to git history. Immediate remediation was performed to rotate credentials and remove hardcoded values.

---

## Timeline

- **2026-02-13 12:08 EST**: Grolf discovered credential leak
- **2026-02-13 12:09 EST**: Lenoon began remediation
- **2026-02-13 12:15 EST**: RabbitMQ password rotated
- **2026-02-13 12:18 EST**: All hardcoded passwords removed from infrastructure repos
- **2026-02-13 12:19 EST**: Security commits pushed

---

## Affected Files (Infrastructure Repos)

| File | Issue | Status |
|------|-------|--------|
| `docker-compose.yml` | Default value `${RABBITMQ_PASS:-REDACTED}` | ✅ Already clean (no default) |
| `bloodbank/.env` | Hardcoded password | ✅ Fixed to use `${RABBITMQ_PASS}` |
| `bloodbank/.env.example` | Missing | ✅ Created with env var template |
| `bloodbank/event_producers/scripts/fix_rabbitmq_management.sh` | Hardcoded credentials in output | ✅ Fixed to use env vars |
| `candystore/.env` | Hardcoded passwords (RabbitMQ + DB) | ✅ Fixed to use env vars |
| `candystore/.env.example` | Missing proper template | ✅ Updated with env var template |
| `hookd/.env` | Hardcoded password + API key | ✅ Fixed to use env vars |
| `hookd/.gitignore` | Missing .env | ✅ Added |
| `hookd/.env.example` | Missing | ✅ Created |
| `services/theboard-meeting-trigger/.env` | Hardcoded passwords | ✅ Fixed to use env vars |
| `services/theboard-meeting-trigger/.env.example` | Missing | ✅ Created |

---

## Remediation Actions

### 1. Credential Rotation

**RabbitMQ password rotated:**
```bash
sudo rabbitmqctl change_password delorenj <new_random_password>
```

New password saved to: `/tmp/new_rabbitmq_pass.txt`

### 2. Code Remediation

All infrastructure repos now use environment variables:
- `${RABBITMQ_PASS}` for RabbitMQ connections
- `${DATABASE_PASSWORD}` for PostgreSQL connections  
- `${QDRANT_API_KEY}` for Qdrant API

### 3. .gitignore Updates

All `.env` files are now in `.gitignore`:
- `bloodbank/.env` (already present)
- `candystore/.env` (already present)
- `hookd/.env` (added)

### 4. .env.example Templates

Created/updated `.env.example` files showing proper structure without secrets:
- `bloodbank/.env.example`
- `candystore/.env.example`
- `hookd/.env.example`
- `services/theboard-meeting-trigger/.env.example`

---

## Commits

| Repo | Branch | Commit | Message |
|------|--------|--------|---------|
| bloodbank | feat/plane-webhook-ingest | `735a355` | security: remove hardcoded credentials |
| candystore | security/remove-hardcoded-creds | `27f1efe` | security: remove hardcoded credentials |
| hookd | main | `2b361a2` | security: remove hardcoded credentials |
| 33GOD (services) | main | `f10803d` | security: add .env.example |

---

## Next Steps (Grolf's Cleanup)

Remaining files requiring cleanup (non-infrastructure repos):
- [ ] flume (TypeScript source files)
- [ ] perth
- [ ] theboard docs
- [ ] theboardroom docs
- [ ] services/mutation-ledger
- [ ] .env.example (root)
- [ ] .claude/hooks

After all cleanups complete:
- [ ] Run `git-filter-repo` to scrub history
- [ ] Force push cleaned history
- [ ] Notify team to re-clone repos

---

## Verification

```bash
# No hardcoded passwords remain in infrastructure repos
grep -r "REDACTED" ~/code/33GOD --include="*.yml" --include="*.yaml" \
  --include="*.env" --include="*.sh" --include="*.py" --include="*.json" 2>/dev/null
# Result: No matches
```

---

## Prevention Measures

1. **Pre-commit hooks**: Add secret detection (gitleaks, trufflehog)
2. **CI/CD scanning**: Scan all PRs for credential leaks
3. **Environment policy**: Never commit .env files; always use .env.example templates
4. **Code review**: Security-focused review for any credential-related changes

---

## Lessons Learned

- Default values in Docker Compose env substitution (`${VAR:-default}`) leak credentials
- .env files must be in .gitignore from repo creation
- Regular credential rotation should be automated
- Secret detection in CI/CD would have caught this pre-commit

---

*Incident remediated by Lenoon, 2026-02-13*
