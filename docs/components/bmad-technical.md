# BMAD - Technical Implementation Guide

## Overview

BMAD (Business, Management, Architecture, Development) is the systematic methodology framework for the 33GOD ecosystem. It provides structured templates, workflow automation, and devlog tracking to ensure consistent, high-quality development across all components.

## Implementation Details

**Language**: Markdown templates + Shell scripts
**Methodology**: BMAD (4-phase development cycle)
**Tooling**: Git hooks, CI/CD templates, documentation generators
**Storage**: File-based devlogs with Git integration

### Key Concepts

- **Business**: Product requirements, user stories, success metrics
- **Management**: Sprint planning, resource allocation, risk assessment
- **Architecture**: System design, technical specifications, C4 diagrams
- **Development**: Implementation, testing, deployment, maintenance

## Architecture & Design Patterns

### Devlog Structure

```
bmad/
├── devlog/
│   ├── tasks/
│   │   ├── 202601290904-task.md
│   │   └── 202601282205-task.md
│   ├── decisions/
│   │   └── 20260128-architecture-decision.md
│   └── retrospectives/
│       └── sprint-01-retro.md
├── templates/
│   ├── product-brief.md
│   ├── tech-spec.md
│   ├── sprint-plan.md
│   └── architecture-decision-record.md
└── scripts/
    ├── new-task.sh
    ├── generate-docs.sh
    └── validate-bmad-compliance.sh
```

### Product Brief Template

```markdown
# Product Brief: [Component Name]

**Date**: 2026-01-29
**Author**: [Name]
**Status**: Draft | Review | Approved
**Version**: 1.0

## Problem Statement

[3-5 sentences describing the problem being solved]

## Goals & Non-Goals

### Goals
- [Primary objective 1]
- [Primary objective 2]

### Non-Goals
- [Explicitly out of scope]

## Success Metrics

- **User Adoption**: [Metric]
- **Performance**: [Metric]
- **Quality**: [Metric]

## User Stories

### Primary Use Case
**As a** [user type]
**I want** [action]
**So that** [benefit]

**Acceptance Criteria**:
- [ ] [Criterion 1]
- [ ] [Criterion 2]

## Technical Constraints

- [Constraint 1]
- [Constraint 2]

## Timeline

- **Phase 1** (Week 1-2): [Milestone]
- **Phase 2** (Week 3-4): [Milestone]

## Dependencies

- [External dependency 1]
- [Internal dependency 2]

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk] | High/Medium/Low | [Strategy] |
```

### Technical Specification Template

```markdown
# Technical Specification: [Component Name]

## Architecture Overview

### System Context (C4 Level 1)

\`\`\`
┌─────────────────┐
│     System      │◄────── External System
│   (Component)   │
└─────────────────┘
\`\`\`

### Container Diagram (C4 Level 2)

\`\`\`
┌──────────┐     ┌──────────┐
│   Web    │────►│   API    │
│  Client  │     │  Server  │
└──────────┘     └──────────┘
                      │
                      ▼
                 ┌──────────┐
                 │ Database │
                 └──────────┘
\`\`\`

## Data Models

### Entity: User

\`\`\`typescript
interface User {
    id: UUID;
    email: string;
    created_at: DateTime;
}
\`\`\`

## API Specification

### Endpoint: GET /api/users

**Request**:
\`\`\`http
GET /api/users?limit=10
Authorization: Bearer <token>
\`\`\`

**Response**:
\`\`\`json
{
    "users": [...],
    "total": 42
}
\`\`\`

## Security Considerations

- [Authentication method]
- [Authorization strategy]
- [Data encryption]

## Performance Requirements

- **Latency**: <100ms p99
- **Throughput**: 1000 req/sec
- **Availability**: 99.9%

## Testing Strategy

- **Unit Tests**: 80% coverage
- **Integration Tests**: Critical paths
- **E2E Tests**: User flows

## Deployment

- **Infrastructure**: Docker + Kubernetes
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana
```

### Sprint Plan Template

```markdown
# Sprint Plan: [Component] Sprint [Number]

**Sprint Duration**: [Start Date] - [End Date]
**Sprint Goal**: [One sentence goal]

## Stories

### Story 1: [Title] (8 points)

**Description**:
[As a... I want... So that...]

**Acceptance Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2

**Tasks**:
- [ ] Task 1 (2 hours)
- [ ] Task 2 (4 hours)

**Dependencies**: None

### Story 2: [Title] (5 points)

[...]

## Velocity

- **Planned Points**: 21
- **Team Capacity**: 40 hours
- **Confidence**: High

## Risks

- **Risk**: [Description]
  - **Mitigation**: [Strategy]
```

### Architecture Decision Record (ADR)

```markdown
# ADR-001: Use PostgreSQL for Primary Database

**Date**: 2026-01-29
**Status**: Accepted | Deprecated | Superseded
**Deciders**: [Names]

## Context

We need a database for storing [data type]. Requirements include:
- ACID transactions
- JSON support
- Horizontal scalability

## Decision

Use PostgreSQL 16 with async SQLAlchemy.

## Rationale

- **Pros**:
  - Mature, battle-tested
  - Excellent JSON support
  - Strong ecosystem
  - Team familiarity

- **Cons**:
  - Vertical scaling limits
  - Complex replication setup

## Alternatives Considered

### MongoDB
- **Pros**: Native JSON, easy sharding
- **Cons**: Weaker consistency, learning curve

### SQLite
- **Pros**: Zero-config, embedded
- **Cons**: No concurrency, single-file limit

## Consequences

- **Positive**: Fast development, reliable transactions
- **Negative**: Will need read replicas for scaling
- **Neutral**: Requires PostgreSQL expertise

## Notes

Revisit this decision if read load exceeds 10K req/sec.
```

## Workflow Automation

### Task Creation Script

```bash
#!/bin/bash
# scripts/new-task.sh

TIMESTAMP=$(date +%Y%m%d%H%M)
TASK_FILE="bmad/devlog/tasks/${TIMESTAMP}-task.md"

cat > "$TASK_FILE" << EOF
# Task: [Title]

**Created**: $(date -I)
**Status**: Todo | In Progress | Done | Blocked
**Priority**: High | Medium | Low

## Description

[Task description]

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Notes

[Any relevant notes]

## Time Tracking

- **Estimated**: [X hours]
- **Actual**: [Y hours]
EOF

echo "Created task: $TASK_FILE"
git add "$TASK_FILE"
```

### Documentation Generator

```bash
#!/bin/bash
# scripts/generate-docs.sh

# Generate component documentation from BMAD artifacts

COMPONENT=$1
DOCS_DIR="docs/components/$COMPONENT"

mkdir -p "$DOCS_DIR"

# Combine product brief + tech spec + sprint plans
cat bmad/product-brief-${COMPONENT}.md > "$DOCS_DIR/overview.md"
cat bmad/tech-spec-${COMPONENT}.md > "$DOCS_DIR/architecture.md"
cat bmad/sprint-plan-${COMPONENT}-*.md > "$DOCS_DIR/development-history.md"

echo "Documentation generated in $DOCS_DIR"
```

## Integration Points

### Git Hook Integration

```bash
# .git/hooks/pre-commit
#!/bin/bash

# Validate BMAD compliance
./bmad/scripts/validate-bmad-compliance.sh

# Ensure all tasks have proper status
./bmad/scripts/check-task-status.sh
```

### CI/CD Integration

```yaml
# .github/workflows/bmad-validation.yml
name: BMAD Validation

on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Check documentation completeness
        run: |
          if [ ! -f "bmad/product-brief-$COMPONENT.md" ]; then
            echo "Missing product brief"
            exit 1
          fi

      - name: Validate sprint plan
        run: |
          python bmad/scripts/validate-sprint-plan.py
```

## Code Examples

### Task Management

```bash
# Create new task
./bmad/scripts/new-task.sh

# Update task status
sed -i 's/Status: Todo/Status: In Progress/' bmad/devlog/tasks/202601290904-task.md

# Generate retrospective
./bmad/scripts/generate-retrospective.sh sprint-01
```

## Related Components

All 33GOD components follow BMAD methodology, documented in their respective `docs/` directories.

---

**Quick Reference**:
- Templates: `bmad/templates/`
- Devlog: `bmad/devlog/`
- Scripts: `bmad/scripts/`
