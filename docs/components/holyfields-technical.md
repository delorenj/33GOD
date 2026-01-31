# Holyfields - Technical Implementation Guide

## Overview

Holyfields is the event schema registry and contract validation system for 33GOD. It auto-generates language-specific artifacts (Python Pydantic, TypeScript Zod) from JSON Schema definitions, enabling independent component development with guaranteed schema compatibility at build time.

## Implementation Details

**Language**: JSON Schema (definitions), Python & TypeScript (generators)
**Schema Format**: JSON Schema Draft 2020-12
**Package Manager**: uv (Python), bun (TypeScript)
**Task Runner**: mise (unified task execution)
**Generation Tools**: datamodel-code-generator, json-schema-to-zod

### Key Technologies

- **JSON Schema 2020-12**: Universal schema definition format
- **datamodel-code-generator**: Python Pydantic model generation
- **json-schema-to-zod**: TypeScript Zod schema generation
- **jsonschema + pytest**: Python contract validation
- **ajv + vitest**: TypeScript contract validation

## Architecture & Design Patterns

### Schema-First Development

Holyfields enforces a **contract-first** approach:

1. **Define** schemas in JSON Schema format
2. **Validate** schema structure with pre-commit hooks
3. **Generate** language artifacts via CI pipeline
4. **Test** contracts with automated validation
5. **Consume** generated artifacts in dependent services

### Directory Structure

```
holyfields/
├── common/schemas/          # Shared base types
│   ├── base_types.json     # UUID, timestamp, pagination
│   └── enums.json          # Status codes, categories
├── theboard/               # TheBoard component contracts
│   ├── events/            # Event schemas (immutable)
│   │   ├── meeting_created.json
│   │   ├── meeting_started.json
│   │   └── comment_extracted.json
│   └── commands/          # Command schemas (mutable)
│       └── create_meeting.json
├── theboardroom/          # TheBoardroom consumer schemas
│   └── events/
│       └── meeting_state_update.json
├── generated/             # Auto-generated artifacts
│   ├── python/           # Pydantic models
│   │   ├── __init__.py
│   │   ├── theboard/
│   │   │   └── events.py
│   │   └── common/
│   │       └── types.py
│   └── typescript/       # Zod schemas + types
│       ├── theboard/
│       │   └── events.ts
│       └── common/
│           └── types.ts
└── tests/                # Contract tests
    ├── python/
    └── typescript/
```

### Event Schema Example

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://33god.dev/schemas/theboard/events/meeting_created.json",
  "type": "object",
  "title": "Meeting Created Event",
  "description": "Emitted when TheBoard creates a new brainstorming meeting",
  "properties": {
    "event_type": {
      "type": "string",
      "const": "theboard.meeting.created",
      "description": "Event type identifier for routing"
    },
    "meeting_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique meeting identifier"
    },
    "topic": {
      "type": "string",
      "minLength": 10,
      "maxLength": 500,
      "description": "Brainstorming topic or question"
    },
    "participant_count": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10,
      "description": "Number of AI agents in meeting"
    },
    "scheduled_time": {
      "type": "string",
      "format": "date-time",
      "description": "Meeting start time (ISO8601)"
    }
  },
  "required": ["event_type", "meeting_id", "topic", "participant_count", "scheduled_time"],
  "additionalProperties": false
}
```

### Code Generation Workflow

**Python Generation**:
```bash
mise run generate:python
# Executes: scripts/generate_python.sh

# Internal: datamodel-code-generator
datamodel-codegen \
  --input common/schemas/base_types.json \
  --input-file-type jsonschema \
  --output generated/python/common/types.py \
  --output-model-type pydantic_v2.BaseModel \
  --use-title-as-name
```

**TypeScript Generation**:
```bash
mise run generate:typescript
# Executes: scripts/generate_typescript.sh

# Internal: json-schema-to-zod (custom wrapper)
node scripts/json_to_zod.js \
  --input theboard/events/meeting_created.json \
  --output generated/typescript/theboard/events.ts
```

### Generated Python Example

```python
# Auto-generated: generated/python/theboard/events.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class MeetingCreatedEvent(BaseModel):
    """
    Emitted when TheBoard creates a new brainstorming meeting
    """
    event_type: str = Field(
        ...,
        const="theboard.meeting.created",
        description="Event type identifier for routing"
    )
    meeting_id: UUID = Field(
        ...,
        description="Unique meeting identifier"
    )
    topic: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Brainstorming topic or question"
    )
    participant_count: int = Field(
        ...,
        ge=1,
        le=10,
        description="Number of AI agents in meeting"
    )
    scheduled_time: datetime = Field(
        ...,
        description="Meeting start time (ISO8601)"
    )

    class Config:
        extra = "forbid"
```

### Generated TypeScript Example

```typescript
// Auto-generated: generated/typescript/theboard/events.ts
import { z } from 'zod';

/**
 * Emitted when TheBoard creates a new brainstorming meeting
 */
export const MeetingCreatedEventSchema = z.object({
  event_type: z.literal("theboard.meeting.created")
    .describe("Event type identifier for routing"),
  meeting_id: z.string().uuid()
    .describe("Unique meeting identifier"),
  topic: z.string().min(10).max(500)
    .describe("Brainstorming topic or question"),
  participant_count: z.number().int().min(1).max(10)
    .describe("Number of AI agents in meeting"),
  scheduled_time: z.string().datetime()
    .describe("Meeting start time (ISO8601)")
}).strict();

export type MeetingCreatedEvent = z.infer<typeof MeetingCreatedEventSchema>;
```

## Configuration

### mise Tasks

```toml
# .mise.toml
[tasks.install]
run = "uv sync && cd tests/typescript && bun install"

[tasks."validate:schemas"]
run = "python scripts/validate_schemas.py"

[tasks."generate:python"]
run = "./scripts/generate_python.sh"

[tasks."generate:typescript"]
run = "./scripts/generate_typescript.sh"

[tasks."generate:all"]
depends = ["generate:python", "generate:typescript"]

[tasks."test:python"]
run = "uv run pytest tests/python"

[tasks."test:typescript"]
run = "cd tests/typescript && bun test"

[tasks."test:all"]
depends = ["test:python", "test:typescript"]

[tasks.ci]
depends = ["install", "validate:schemas", "generate:all", "test:all"]
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-schemas
        name: Validate JSON Schemas
        entry: python scripts/validate_schemas.py
        language: system
        pass_filenames: false
        always_run: true

      - id: generate-artifacts
        name: Generate Language Artifacts
        entry: mise run generate:all
        language: system
        pass_filenames: false
        files: '.*\.json$'
```

## Integration Points

### Producer Integration (TheBoard)

```python
# In TheBoard service
from generated.python.theboard.events import MeetingCreatedEvent
from bloodbank import Publisher
import asyncio
from uuid import uuid4
from datetime import datetime

async def create_meeting(topic: str, participant_count: int):
    # Create validated event
    event = MeetingCreatedEvent(
        event_type="theboard.meeting.created",
        meeting_id=uuid4(),
        topic=topic,
        participant_count=participant_count,
        scheduled_time=datetime.utcnow()
    )

    # Publish to Bloodbank
    publisher = Publisher()
    await publisher.publish(
        routing_key="theboard.meeting.created",
        body=event.model_dump(),
        message_id=str(event.meeting_id)
    )
```

### Consumer Integration (TheBoardroom)

```typescript
// In TheBoardroom service
import { MeetingCreatedEventSchema } from '@/generated/typescript/theboard/events';
import type { MeetingCreatedEvent } from '@/generated/typescript/theboard/events';

async function handleMeetingEvent(rawData: unknown) {
  try {
    // Parse and validate with Zod
    const event: MeetingCreatedEvent = MeetingCreatedEventSchema.parse(rawData);

    // Type-safe access to properties
    console.log(`Meeting ${event.meeting_id} created`);
    console.log(`Topic: ${event.topic}`);
    console.log(`Participants: ${event.participant_count}`);

    // Update UI state
    await updateMeetingVisualization(event);
  } catch (error) {
    console.error('Schema validation failed:', error);
    // Handle invalid event
  }
}
```

## Performance Characteristics

### Generation Speed

- **Python**: ~100ms per schema file
- **TypeScript**: ~150ms per schema file
- **Full regeneration**: <5 seconds for 50 schemas
- **Incremental**: Only regenerate changed schemas

### Contract Test Performance

- **Python (pytest)**: ~2 seconds for 100 test cases
- **TypeScript (vitest)**: ~1.5 seconds for 100 test cases
- **CI Pipeline**: <30 seconds total (validate + generate + test)

## Edge Cases & Troubleshooting

### Breaking Change Detection

**Problem**: Field type change breaks consumers
**Solution**: Automated breaking change detection

```python
# scripts/detect_breaking_changes.py
def detect_breaking_changes(old_schema, new_schema):
    """Detect incompatible schema modifications"""
    breaking = []

    # Field removal
    old_props = set(old_schema.get("properties", {}).keys())
    new_props = set(new_schema.get("properties", {}).keys())
    removed = old_props - new_props
    if removed:
        breaking.append(f"Removed fields: {removed}")

    # Type changes
    for prop in old_props & new_props:
        old_type = old_schema["properties"][prop]["type"]
        new_type = new_schema["properties"][prop]["type"]
        if old_type != new_type:
            breaking.append(f"Type change on {prop}: {old_type} -> {new_type}")

    # Required field additions
    old_required = set(old_schema.get("required", []))
    new_required = set(new_schema.get("required", []))
    added_required = new_required - old_required
    if added_required:
        breaking.append(f"New required fields: {added_required}")

    return breaking
```

### Circular Dependency Resolution

**Problem**: Schema A references Schema B which references Schema A
**Solution**: Use `$ref` pointers with lazy resolution

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://33god.dev/schemas/common/types.json",
  "definitions": {
    "Agent": {
      "type": "object",
      "properties": {
        "id": { "type": "string", "format": "uuid" },
        "team": {
          "$ref": "#/definitions/Team"
        }
      }
    },
    "Team": {
      "type": "object",
      "properties": {
        "members": {
          "type": "array",
          "items": { "$ref": "#/definitions/Agent" }
        }
      }
    }
  }
}
```

### Version Migration

**Problem**: Need to support multiple schema versions
**Solution**: Semantic versioning with migration adapters

```python
# migration_adapters/theboard/meeting_v1_to_v2.py
def migrate_meeting_created_v1_to_v2(event_v1: dict) -> dict:
    """Migrate meeting created event from v1 to v2"""
    event_v2 = event_v1.copy()

    # v2 added 'strategy' field (default to 'sequential')
    event_v2["strategy"] = event_v1.get("strategy", "sequential")

    # v2 renamed 'participant_count' to 'agent_count'
    event_v2["agent_count"] = event_v1.pop("participant_count")

    return event_v2
```

## Code Examples

### Custom Validator

```python
# In schema JSON
{
  "properties": {
    "email": {
      "type": "string",
      "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    },
    "age": {
      "type": "integer",
      "minimum": 0,
      "maximum": 150
    }
  }
}

# Generated Pydantic includes validators
from pydantic import EmailStr, Field

class UserEvent(BaseModel):
    email: EmailStr
    age: int = Field(..., ge=0, le=150)
```

### Contract Test Example

```python
# tests/python/test_meeting_events.py
import pytest
from generated.python.theboard.events import MeetingCreatedEvent
from datetime import datetime
from uuid import uuid4

def test_valid_meeting_created_event():
    """Valid event passes validation"""
    event = MeetingCreatedEvent(
        event_type="theboard.meeting.created",
        meeting_id=uuid4(),
        topic="How can we improve API design?",
        participant_count=5,
        scheduled_time=datetime.utcnow()
    )
    assert event.event_type == "theboard.meeting.created"
    assert 10 <= len(event.topic) <= 500

def test_invalid_participant_count():
    """Participant count outside range fails validation"""
    with pytest.raises(ValueError, match="participant_count"):
        MeetingCreatedEvent(
            event_type="theboard.meeting.created",
            meeting_id=uuid4(),
            topic="Test topic that meets minimum length",
            participant_count=11,  # Exceeds max of 10
            scheduled_time=datetime.utcnow()
        )

def test_missing_required_field():
    """Missing required field fails validation"""
    with pytest.raises(ValueError, match="topic"):
        MeetingCreatedEvent(
            event_type="theboard.meeting.created",
            meeting_id=uuid4(),
            # topic field omitted
            participant_count=5,
            scheduled_time=datetime.utcnow()
        )
```

## Deployment Best Practices

1. **Version Control**: Commit both schemas and generated artifacts
2. **CI Integration**: Regenerate on every PR, block merge if validation fails
3. **Changelog**: Document schema changes in component `version.json`
4. **Deprecation**: Mark deprecated fields with `deprecated: true` annotation
5. **Backward Compatibility**: Prefer additive changes (optional fields)

## Versioning Strategy

### Component Versioning

```json
// theboard/version.json
{
  "component": "theboard",
  "version": "2.1.0",
  "schema_version": "2.1",
  "changelog": {
    "2.1.0": {
      "date": "2026-01-29",
      "changes": [
        "Added 'convergence_metrics' to meeting.completed event",
        "Deprecated 'notetaker_version' (use 'agent_versions' instead)"
      ],
      "breaking": false
    },
    "2.0.0": {
      "date": "2026-01-15",
      "changes": [
        "Renamed 'participant' to 'agent' across all events",
        "Changed 'status' from string to enum"
      ],
      "breaking": true
    }
  }
}
```

### Migration Ticket Example

```markdown
# Integration Ticket: TheBoard v2.1 Schema Migration

## Component
TheBoard

## Version
2.1.0

## Schema Changes
- **Added**: `convergence_metrics` object to `meeting.completed` event
- **Deprecated**: `notetaker_version` field (backward compatible)

## Affected Consumers
- TheBoardroom (visualization)
- Candystore (event storage)

## Migration Guide

### TheBoardroom Updates Required
Update event handler to access new metrics:
\`\`\`typescript
interface MeetingCompletedEvent {
  // ... existing fields
  convergence_metrics?: {
    final_novelty_score: number;
    rounds_to_convergence: number;
  };
}
\`\`\`

### Candystore Updates (Optional)
No action required - stores full payload

## Acceptance Criteria
- [ ] TheBoardroom displays convergence metrics when available
- [ ] Backward compatibility: old events still render correctly
- [ ] Contract tests pass for both v2.0 and v2.1 schemas

## Timeline
Target: Sprint 3 (Week of Feb 5, 2026)
```

## Related Components

- **Bloodbank**: Event transport layer (Holyfields defines schemas, Bloodbank delivers)
- **TheBoard**: Event producer (meeting orchestration events)
- **TheBoardroom**: Event consumer (visualization client)
- **Candystore**: Universal consumer (stores all event types)

---

**Quick Reference**:
- GitHub: `33GOD/holyfields`
- Schema Catalog: `docs/catalog/`
- CI Validation: `.github/workflows/validate-contracts.yml`
- Integration Tickets: `docs/integration-tickets/`
