/**
 * P1 Tests for lib/holyfields.js - Catalog, Schema Catalog, Event Type Derivation
 *
 * Coverage: T14-T19 from test-design-epic-35.md
 */

import { describe, test, expect, beforeAll } from 'vitest';
import path from 'path';

const FIXTURE_SCHEMAS_DIR = path.join(__dirname, 'fixtures', 'schemas');
process.env.HOLYFIELDS_SCHEMAS_DIR = FIXTURE_SCHEMAS_DIR;

let holyfields;
beforeAll(async () => {
  holyfields = await import('../lib/holyfields.js');
});

// ---------------------------------------------------------------------------
// T14-T15: loadCatalog()
// ---------------------------------------------------------------------------
describe('loadCatalog', () => {
  test('T14: discovers all schema files from fixture dir', () => {
    const catalog = holyfields.loadCatalog();
    expect(catalog).toBeDefined();
    expect(catalog.byPath).toBeDefined();
    expect(catalog.byPath.size).toBeGreaterThan(0);

    // Should find our fixture schemas
    expect(catalog.byPath.has('agent/heartbeat.v1.json')).toBe(true);
    expect(catalog.byPath.has('command/envelope.v1.json')).toBe(true);
    expect(catalog.byPath.has('fireflies/transcript/upload.v1.json')).toBe(true);
    expect(catalog.byPath.has('circular/a.v1.json')).toBe(true);
    expect(catalog.byPath.has('circular/b.v1.json')).toBe(true);
    expect(catalog.byPath.has('nullable/union.v1.json')).toBe(true);
  });

  test('T15: skips _common/ entries from catalog entries list', () => {
    const catalog = holyfields.loadCatalog();

    // _common/source.v1.json should be in byPath (for $ref resolution)
    expect(catalog.byPath.has('_common/source.v1.json')).toBe(true);

    // But _common/ schemas should NOT appear in the entries list (filtered out)
    const commonEntries = catalog.entries.filter(e => e.schemaPath.startsWith('_common/'));
    expect(commonEntries).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// T16-T17: getSchemaCatalog()
// ---------------------------------------------------------------------------
describe('getSchemaCatalog', () => {
  test('T16: vetted mode returns only vetted schemas', () => {
    const vetted = holyfields.getSchemaCatalog('vetted');
    expect(Array.isArray(vetted)).toBe(true);

    // Every returned schema should be in VETTED_SCHEMA_PATHS or start with command/
    for (const schema of vetted) {
      const isVetted = holyfields.VETTED_SCHEMA_PATHS.has(schema.schemaPath) ||
                       schema.schemaPath.startsWith('command/');
      expect(isVetted).toBe(true);
    }
  });

  test('T17: all mode returns all schemas', () => {
    const all = holyfields.getSchemaCatalog('all');
    const vetted = holyfields.getSchemaCatalog('vetted');
    expect(Array.isArray(all)).toBe(true);

    // "all" should return >= "vetted" count
    expect(all.length).toBeGreaterThanOrEqual(vetted.length);

    // Should include non-vetted schemas like circular/a.v1.json
    const hasPaths = all.map(s => s.schemaPath);
    expect(hasPaths).toContain('circular/a.v1.json');
  });
});

// ---------------------------------------------------------------------------
// T18-T19: deriveEventType() (tested indirectly via getSchemaDetails)
// ---------------------------------------------------------------------------
describe('deriveEventType', () => {
  test('T18: extracts event type from schema event_type.const', () => {
    // agent/heartbeat.v1.json has event_type.const = "agent.heartbeat"
    const details = holyfields.getSchemaDetails('agent/heartbeat.v1.json');
    expect(details).not.toBeNull();
    expect(details.eventType).toBe('agent.heartbeat');
  });

  test('T19: falls back to path-based derivation when no const', () => {
    // circular/a.v1.json has event_type.const = "circular.a"
    const details = holyfields.getSchemaDetails('circular/a.v1.json');
    expect(details).not.toBeNull();
    expect(details.eventType).toBe('circular.a');

    // nullable/union.v1.json has event_type.const = "nullable.union"
    const details2 = holyfields.getSchemaDetails('nullable/union.v1.json');
    expect(details2).not.toBeNull();
    expect(details2.eventType).toBe('nullable.union');
  });
});
