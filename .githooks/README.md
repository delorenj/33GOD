# 33GOD Git Hooks

This directory contains git hooks for maintaining GOD documents and other repository automation.

## Setup

Enable git hooks for this repository:

```bash
git config core.hooksPath .githooks
```

## Hooks

### pre-commit

**Purpose**: Detect component changes and prompt for GOD document updates.

**Behavior**:
1. Detects changed files in component directories
2. Lists components requiring GOD doc updates
3. Prompts user to:
   - Update GOD docs now (recommended)
   - Skip for now (manual update required)
   - Abort commit

**Enable**:
```bash
git config core.hooksPath .githooks
```

**Disable temporarily**:
```bash
git commit --no-verify
```

---

## Testing Hooks

```bash
# Test pre-commit hook
.githooks/pre-commit

# Simulate component change
touch bloodbank/src/publisher.py
git add bloodbank/src/publisher.py
git commit -m "Test commit"
# Hook should prompt for GOD doc update
```

---

## Hook Development

Hooks are bash scripts. Make executable:

```bash
chmod +x .githooks/<hook-name>
```

Test hooks before committing:

```bash
# Lint hook script
shellcheck .githooks/pre-commit

# Test hook
.githooks/pre-commit
```
