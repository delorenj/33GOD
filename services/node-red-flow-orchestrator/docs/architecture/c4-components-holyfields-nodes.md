# C4 Component Diagram - Holyfields Custom Nodes

The `node-red-contrib-33god-holyfields` package is the primary integration point between Node-RED and Bloodbank. It provides palette nodes for schema-aware event publishing and consuming.

```mermaid
C4Component
  title Component Diagram - node-red-contrib-33god-holyfields

  Container_Boundary(holyfieldsLib, "lib/holyfields.js - Schema Engine") {
    Component(catalogLoader, "Catalog Loader", "loadCatalog()", "Walks Holyfields schema directory, builds byPath/byId lookup maps")
    Component(schemaResolver, "Schema Resolver", "resolveSchema()", "Resolves $ref, allOf, oneOf, anyOf across schema files")
    Component(defaultBuilder, "Default Value Builder", "buildDefaultValue()", "Generates form-ready default payloads from resolved schemas")
    Component(envelopeCompat, "Envelope Compat", "ensureEnvelopeCompat()", "Ensures event_id, timestamp, source, correlation_ids on every envelope")
    Component(validator, "AJV Validator", "getValidator()", "Compiles and caches JSON Schema validators per schema path")
    Component(adminApi, "Admin REST API", "registerAdminRoutes()", "Exposes /holyfields/schemas and /holyfields/schema endpoints")
  }

  Container_Boundary(outNode, "holyfields-out Node") {
    Component(outHandler, "Output Handler", "HolyfieldsOutNode", "Merges template + msg.payload, builds envelope, POSTs to Bloodbank /events/custom")
    Component(commandRouter, "Command Router", "Command detection", "Routes command/ schemas to command.{agent}.{action} routing keys")
  }

  Container_Boundary(inNode, "holyfields-in Node") {
    Component(inHandler, "Input Handler", "HolyfieldsInNode", "Connects to RabbitMQ, binds queue to routing key, emits msg per event")
    Component(validationPipeline, "Validation Pipeline", "warn/strict/off modes", "Validates inbound envelopes against selected schema, drops or warns")
  }

  SystemDb(holyfieldsSchemas, "Holyfields Schemas", "JSON Schema files on disk")
  SystemQueue(bloodbankExchange, "Bloodbank Exchange", "bloodbank.events.v1 (topic)")
  Container(bloodbankApi, "Bloodbank HTTP API", "POST /events/custom")

  Rel(catalogLoader, holyfieldsSchemas, "Reads all *.json schemas", "fs.readFileSync")
  Rel(catalogLoader, schemaResolver, "Resolves $ref chains")
  Rel(schemaResolver, defaultBuilder, "Provides resolved schema")
  Rel(adminApi, catalogLoader, "Serves schema catalog to Node-RED UI")

  Rel(outHandler, envelopeCompat, "Wraps payload in valid envelope")
  Rel(outHandler, commandRouter, "Detects command/ schemas")
  Rel(outHandler, bloodbankApi, "POSTs envelope", "HTTP fetch")
  Rel(commandRouter, bloodbankApi, "Routes to command.{agent}.{action}")

  Rel(inHandler, bloodbankExchange, "Binds queue, consumes messages", "amqplib")
  Rel(inHandler, validationPipeline, "Validates inbound envelopes")
  Rel(validationPipeline, validator, "Compiles + runs AJV validation")
```

## holyfields-out Publish Flow

1. Node receives `msg` with optional `msg.payload`, `msg.envelope`, `msg.schemaPath`
2. Loads schema details from catalog (if schemaPath set)
3. Merges template payload with `msg.payload` via deep merge
4. For `command/envelope.v1.json`: auto-routes to `command.{target_agent}.{action}`
5. Wraps in envelope with `ensureEnvelopeCompat()` (event_id, timestamp, source, etc.)
6. POSTs to Bloodbank HTTP API at `/events/custom`

## holyfields-in Subscribe Flow

1. Connects to RabbitMQ via `amqplib`
2. Declares/asserts queue (named or auto-generated)
3. Binds queue to exchange with routing key pattern
4. For each message: parses JSON, optionally validates against schema
5. Validation modes: `warn` (log + forward), `strict` (drop invalid), `off` (no validation)
6. Emits `msg` with `payload` (envelope or payload-only) + `holyfields.validation` metadata

## Vetted Schema Paths

The catalog distinguishes "vetted" schemas (production-ready) from the full set:

- `agent/heartbeat.v1.json`
- `fireflies/transcript/upload.v1.json`, `ready.v1.json`, `processed.v1.json`, `failed.v1.json`
- `session/thread/*` schemas
- `artifact/audio/detected.v1.json`
- All `command/*` schemas (auto-vetted)
