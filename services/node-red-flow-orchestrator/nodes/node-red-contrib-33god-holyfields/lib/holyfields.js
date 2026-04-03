const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const Ajv = require("ajv");
const addFormats = require("ajv-formats");

const DEFAULT_SCHEMAS_DIR =
  process.env.HOLYFIELDS_SCHEMAS_DIR || "";

const VETTED_SCHEMA_PATHS = new Set([
  "agent/heartbeat.v1.json",
  "agent/thread/prompt.v1.json",
  "agent/thread/response.v1.json",
  "agent/thread/error.v1.json",
  "agent/message.sent.v1.json",
  "agent/message.received.v1.json",
  "session/thread/start.v1.json",
  "session/thread/message.v1.json",
  "session/thread/end.v1.json",
  "session/thread/error.v1.json",
  "session/thread/agent/action.v1.json",
  "session/thread/agent/thinking.v1.json",
  "fireflies/transcript/upload.v1.json",
  "fireflies/transcript/ready.v1.json",
  "fireflies/transcript/processed.v1.json",
  "fireflies/transcript/failed.v1.json",
  "artifact/audio/detected.v1.json",
]);

let catalogCache = null;
let validatorCache = new Map();
let adminRoutesRegistered = false;

function isVettedSchema(schemaPath) {
  if (schemaPath.startsWith("command/")) return true;
  return VETTED_SCHEMA_PATHS.has(schemaPath);
}

function normalizePath(relPath) {
  return relPath.replace(/\\/g, "/");
}

function walkJsonFiles(rootDir, currentDir = rootDir, out = []) {
  const entries = fs.readdirSync(currentDir, { withFileTypes: true });

  for (const entry of entries) {
    const abs = path.join(currentDir, entry.name);
    if (entry.isDirectory()) {
      walkJsonFiles(rootDir, abs, out);
      continue;
    }

    if (!entry.isFile() || !entry.name.endsWith(".json")) continue;

    const rel = normalizePath(path.relative(rootDir, abs));
    out.push({ relPath: rel, absPath: abs });
  }

  return out;
}

function getPrimaryType(schema) {
  if (!schema) return undefined;
  if (typeof schema.type === "string") return schema.type;
  if (Array.isArray(schema.type)) {
    return schema.type.find((t) => t !== "null") || schema.type[0];
  }
  return undefined;
}

function mergeSchemas(a, b) {
  const merged = { ...a, ...b };
  const props = { ...(a.properties || {}), ...(b.properties || {}) };
  if (Object.keys(props).length > 0) merged.properties = props;

  const required = Array.from(new Set([...(a.required || []), ...(b.required || [])]));
  if (required.length > 0) merged.required = required;

  return merged;
}

function dirnamePosix(p) {
  const idx = p.lastIndexOf("/");
  if (idx <= 0) return "";
  return p.slice(0, idx);
}

function joinPosix(a, b) {
  if (!a) return b;
  if (!b) return a;
  return `${a}/${b}`;
}

function normalizePosixPath(p) {
  const stack = [];
  for (const seg of p.split("/")) {
    if (!seg || seg === ".") continue;
    if (seg === "..") {
      stack.pop();
      continue;
    }
    stack.push(seg);
  }
  return stack.join("/");
}

function resolveJsonPointer(target, pointer) {
  const segments = pointer
    .replace(/^#\/?/, "")
    .split("/")
    .filter(Boolean)
    .map((seg) => seg.replace(/~1/g, "/").replace(/~0/g, "~"));

  let current = target;
  for (const seg of segments) {
    if (current && typeof current === "object" && seg in current) {
      current = current[seg];
    } else {
      return {};
    }
  }

  return current && typeof current === "object" ? current : {};
}

function resolveSchema(node, currentPath, byPath, byId, depth = 0, seen = new Set()) {
  if (!node || typeof node !== "object") return {};
  if (depth > 20) return node;

  if (node.$ref && typeof node.$ref === "string") {
    const ref = node.$ref;
    const cacheKey = `${currentPath}::${ref}`;
    if (seen.has(cacheKey)) return node;
    seen.add(cacheKey);

    const [refPathRaw, pointerRaw] = ref.split("#");
    const pointer = pointerRaw ? `#${pointerRaw}` : "";

    let resolvedRef = {};

    if (!refPathRaw) {
      resolvedRef = resolveJsonPointer(byPath.get(currentPath) || {}, pointer || "#");
    } else if (refPathRaw.startsWith("http://") || refPathRaw.startsWith("https://")) {
      const target = byId.get(refPathRaw) || {};
      resolvedRef = pointer ? resolveJsonPointer(target, pointer) : target;
    } else {
      const absRefPath = normalizePosixPath(joinPosix(dirnamePosix(currentPath), refPathRaw));
      const target = byPath.get(absRefPath) || {};
      resolvedRef = pointer ? resolveJsonPointer(target, pointer) : target;
    }

    const resolvedNode = resolveSchema(resolvedRef, currentPath, byPath, byId, depth + 1, seen);
    const withoutRef = { ...node };
    delete withoutRef.$ref;
    return resolveSchema(mergeSchemas(resolvedNode, withoutRef), currentPath, byPath, byId, depth + 1, seen);
  }

  if (Array.isArray(node.oneOf) && node.oneOf.length > 0) {
    return resolveSchema(node.oneOf[0], currentPath, byPath, byId, depth + 1, seen);
  }
  if (Array.isArray(node.anyOf) && node.anyOf.length > 0) {
    return resolveSchema(node.anyOf[0], currentPath, byPath, byId, depth + 1, seen);
  }

  let working = { ...node };

  if (Array.isArray(working.allOf) && working.allOf.length > 0) {
    const merged = working.allOf
      .map((item) => resolveSchema(item, currentPath, byPath, byId, depth + 1, seen))
      .reduce((acc, item) => mergeSchemas(acc, item), {});

    const withoutAllOf = { ...working };
    delete withoutAllOf.allOf;
    working = mergeSchemas(merged, withoutAllOf);
  }

  if (working.properties && typeof working.properties === "object") {
    const nextProps = {};
    for (const [key, child] of Object.entries(working.properties)) {
      nextProps[key] = resolveSchema(child, currentPath, byPath, byId, depth + 1, seen);
    }
    working.properties = nextProps;
  }

  if (working.items && typeof working.items === "object") {
    working.items = resolveSchema(working.items, currentPath, byPath, byId, depth + 1, seen);
  }

  return working;
}

function pickDefaultString(propName, schema) {
  if (typeof schema.const === "string") return schema.const;
  if (typeof schema.default === "string") return schema.default;

  const enumVals = Array.isArray(schema.enum) ? schema.enum.filter((v) => typeof v === "string") : [];
  if (enumVals.length > 0) return enumVals[0];

  if (schema.format === "date-time") return new Date().toISOString();
  if (schema.format === "uuid" || propName === "event_id" || propName.endsWith("_id")) {
    return crypto.randomUUID();
  }

  if (propName === "version") return "1.0.0";
  if (propName === "event_type") return "custom.event";
  if (propName === "host") return "node-red";
  if (propName === "app") return "node-red-holyfields";
  if (propName === "trigger_type") return "api";
  if (propName === "type") return "manual";

  if (typeof schema.minLength === "number" && schema.minLength > 0) {
    return "x".repeat(Math.min(schema.minLength, 16));
  }

  return "";
}

function buildDefaultValue(schema, propName = "") {
  if (!schema || typeof schema !== "object") return null;
  if (schema.const !== undefined) return schema.const;
  if (schema.default !== undefined) return schema.default;

  const pType = getPrimaryType(schema);

  if (Array.isArray(schema.enum) && schema.enum.length > 0) {
    return schema.enum[0];
  }

  if (pType === "object" || (!pType && schema.properties)) {
    const output = {};
    const required = new Set(schema.required || []);
    for (const [key, child] of Object.entries(schema.properties || {})) {
      const shouldInclude =
        required.has(key) ||
        child.const !== undefined ||
        child.default !== undefined ||
        key === "event_type" ||
        key === "version";

      if (!shouldInclude) continue;
      output[key] = buildDefaultValue(child, key);
    }
    return output;
  }

  if (pType === "array") {
    const minItems = typeof schema.minItems === "number" ? schema.minItems : 0;
    if (schema.items && minItems > 0) {
      return Array.from({ length: minItems }, () => buildDefaultValue(schema.items));
    }
    return [];
  }

  if (pType === "boolean") return false;
  if (pType === "integer" || pType === "number") {
    if (typeof schema.minimum === "number") return schema.minimum;
    return 0;
  }

  return pickDefaultString(propName, schema);
}

function deriveEventType(schema, schemaPath) {
  const ev = schema?.properties?.event_type;
  if (ev && typeof ev === "object" && typeof ev.const === "string") return ev.const;
  return schemaPath.replace(/\.v\d+\.json$/i, "").replace(/\.json$/i, "").replace(/\//g, ".");
}

function ensureEnvelopeCompat(value, fallbackEventType) {
  const root = value && typeof value === "object" && !Array.isArray(value) ? value : {};

  if (!root.event_id || typeof root.event_id !== "string") root.event_id = crypto.randomUUID();
  if (!root.event_type || typeof root.event_type !== "string") root.event_type = fallbackEventType;
  if (!root.timestamp || typeof root.timestamp !== "string") root.timestamp = new Date().toISOString();
  if (!root.version || typeof root.version !== "string") root.version = "1.0.0";
  if (!Array.isArray(root.correlation_ids)) root.correlation_ids = [];

  const source = root.source && typeof root.source === "object" && !Array.isArray(root.source)
    ? root.source
    : {};

  if (!source.host) source.host = "node-red";
  if (!source.app) source.app = "node-red-holyfields";
  if (!source.type) source.type = "manual";
  if (!source.trigger_type) source.trigger_type = "api";

  root.source = source;
  return root;
}

function loadCatalog() {
  if (catalogCache) return catalogCache;

  const byPath = new Map();
  const byId = new Map();

  for (const file of walkJsonFiles(DEFAULT_SCHEMAS_DIR)) {
    if (file.relPath.endsWith("manifest.json")) continue;

    let parsed;
    try {
      parsed = JSON.parse(fs.readFileSync(file.absPath, "utf8"));
    } catch {
      continue;
    }

    byPath.set(file.relPath, parsed);
    if (parsed.$id && typeof parsed.$id === "string") {
      byId.set(parsed.$id, parsed);
    }
  }

  const entries = [];

  for (const [schemaPath, rawSchema] of byPath.entries()) {
    if (schemaPath.startsWith("_common/")) continue;

    const resolved = resolveSchema(rawSchema, schemaPath, byPath, byId);
    const eventType = deriveEventType(resolved, schemaPath);
    const kind = schemaPath.startsWith("command/") ? "command" : "event";

    const defaultEnvelope = ensureEnvelopeCompat(buildDefaultValue(resolved), eventType);
    const payloadSchema = resolved?.properties?.payload || {};
    const defaultPayload = defaultEnvelope.payload && typeof defaultEnvelope.payload === "object"
      ? defaultEnvelope.payload
      : {};

    entries.push({
      id: resolved.$id || schemaPath,
      schemaPath,
      title: resolved.title || schemaPath,
      description: resolved.description || "",
      eventType,
      kind,
      resolvedSchema: resolved,
      payloadSchema,
      defaultEnvelope,
      defaultPayload,
      rawSchema,
    });
  }

  entries.sort((a, b) => {
    if (a.kind !== b.kind) return a.kind === "command" ? -1 : 1;
    return a.eventType.localeCompare(b.eventType);
  });

  const allRawSchemas = Array.from(byPath.values()).filter((s) => s && typeof s === "object");

  catalogCache = { entries, byPath, byId, allRawSchemas };
  return catalogCache;
}

function getSchemaCatalog(mode = "vetted") {
  const { entries } = loadCatalog();
  const filtered = mode === "all" ? entries : entries.filter((e) => isVettedSchema(e.schemaPath));
  return filtered.map((e) => ({
    schemaPath: e.schemaPath,
    title: e.title,
    description: e.description,
    eventType: e.eventType,
    kind: e.kind,
  }));
}

function getSchemaDetails(schemaPath) {
  const { entries } = loadCatalog();
  return entries.find((entry) => entry.schemaPath === schemaPath) || null;
}

function getValidator(schemaPath) {
  if (validatorCache.has(schemaPath)) return validatorCache.get(schemaPath);

  const details = getSchemaDetails(schemaPath);
  if (!details) return null;

  const ajv = new Ajv({
    strict: false,
    allErrors: true,
    allowUnionTypes: true,
    validateFormats: true,
  });
  addFormats(ajv);

  const { allRawSchemas } = loadCatalog();
  for (const schema of allRawSchemas) {
    try {
      ajv.addSchema(schema);
    } catch {
      // ignore duplicate schema registrations
    }
  }

  const validate = ajv.compile(details.rawSchema);
  validatorCache.set(schemaPath, validate);
  return validate;
}

function registerAdminRoutes(RED) {
  if (adminRoutesRegistered) return;
  adminRoutesRegistered = true;

  const needsPermission = RED.auth && RED.auth.needsPermission
    ? RED.auth.needsPermission("flows.read")
    : (_req, _res, next) => next();

  RED.httpAdmin.get("/holyfields/schemas", needsPermission, (req, res) => {
    try {
      const mode = req.query.mode === "all" ? "all" : "vetted";
      res.json({ ok: true, schemas: getSchemaCatalog(mode) });
    } catch (error) {
      res.status(500).json({ ok: false, error: error.message || String(error) });
    }
  });

  RED.httpAdmin.get("/holyfields/schema", needsPermission, (req, res) => {
    try {
      const schemaPath = String(req.query.path || "");
      if (!schemaPath) {
        res.status(400).json({ ok: false, error: "Missing query param: path" });
        return;
      }

      const details = getSchemaDetails(schemaPath);
      if (!details) {
        res.status(404).json({ ok: false, error: `Schema not found: ${schemaPath}` });
        return;
      }

      res.json({
        ok: true,
        schema: {
          schemaPath: details.schemaPath,
          title: details.title,
          description: details.description,
          eventType: details.eventType,
          kind: details.kind,
          payloadSchema: details.payloadSchema,
          defaultPayload: details.defaultPayload,
          defaultEnvelope: details.defaultEnvelope,
        },
      });
    } catch (error) {
      res.status(500).json({ ok: false, error: error.message || String(error) });
    }
  });
}

function deepMerge(a, b) {
  if (Array.isArray(a) || Array.isArray(b)) return b;
  if (!a || typeof a !== "object") return b;
  if (!b || typeof b !== "object") return b;

  const out = { ...a };
  for (const [key, val] of Object.entries(b)) {
    if (
      val &&
      typeof val === "object" &&
      !Array.isArray(val) &&
      out[key] &&
      typeof out[key] === "object" &&
      !Array.isArray(out[key])
    ) {
      out[key] = deepMerge(out[key], val);
    } else {
      out[key] = val;
    }
  }
  return out;
}

module.exports = {
  DEFAULT_SCHEMAS_DIR,
  VETTED_SCHEMA_PATHS,
  loadCatalog,
  getSchemaCatalog,
  getSchemaDetails,
  getValidator,
  registerAdminRoutes,
  ensureEnvelopeCompat,
  deepMerge,
};
