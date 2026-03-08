module.exports = function (RED) {
  const crypto = require("crypto");
  const {
    getSchemaDetails,
    registerAdminRoutes,
    ensureEnvelopeCompat,
    deepMerge,
  } = require("./lib/holyfields");

  registerAdminRoutes(RED);

  function safeJsonParse(text, fallback) {
    if (!text || typeof text !== "string") return fallback;
    try {
      return JSON.parse(text);
    } catch {
      return fallback;
    }
  }

  function toArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function normalizePublishUrl(url) {
    if (url && typeof url === "string" && url.trim()) return url.trim();
    return "http://127.0.0.1:8682/events/custom";
  }

  function HolyfieldsOutNode(config) {
    RED.nodes.createNode(this, config);
    const node = this;

    const schemaPath = config.schemaPath || "";
    const schemaDetails = schemaPath ? getSchemaDetails(schemaPath) : null;
    const staticPayloadTemplate = safeJsonParse(config.payloadTemplate, {});

    const sourceDefaults = {
      host: config.sourceHost || "node-red",
      app: config.sourceApp || "node-red-holyfields",
      type: config.sourceType || "manual",
      trigger_type: config.triggerType || "api",
    };

    function normalizeSourceType(value) {
      const raw = String(value || "").trim().toLowerCase();
      if (!raw) return "manual";
      if (raw === "watcher" || raw === "watch") return "file_watch";
      return raw;
    }

    function normalizeTriggerType(value) {
      const raw = String(value || "").trim().toLowerCase();
      if (!raw) return "api";
      return raw;
    }

    const publishUrl = normalizePublishUrl(config.publishUrl);

    node.status({ fill: "grey", shape: "ring", text: schemaDetails ? schemaDetails.eventType : "ready" });

    node.on("input", async function (msg, send, done) {
      send = send || function () { node.send.apply(node, arguments); };
      done = done || function (err) { if (err) node.error(err, msg); };

      try {
        const selectedSchemaPath = msg.schemaPath || schemaPath;
        const selectedSchema = selectedSchemaPath ? getSchemaDetails(selectedSchemaPath) : schemaDetails;

        const msgEnvelope = msg.envelope && typeof msg.envelope === "object" && !Array.isArray(msg.envelope)
          ? msg.envelope
          : {};

        const msgPayload = msg.payload && typeof msg.payload === "object" && !Array.isArray(msg.payload)
          ? msg.payload
          : {};

        const templatePayload =
          msg.holyfields && typeof msg.holyfields === "object" && msg.holyfields.payload && typeof msg.holyfields.payload === "object"
            ? msg.holyfields.payload
            : staticPayloadTemplate;

        const mergedPayload = deepMerge(templatePayload || {}, msgPayload || {});

        let eventType =
          msg.event_type ||
          msg.routing_key ||
          msgEnvelope.event_type ||
          (selectedSchema ? selectedSchema.eventType : null) ||
          "custom.event";

        if (selectedSchema && selectedSchema.schemaPath === "command/envelope.v1.json") {
          const targetAgent = mergedPayload.target_agent || "lenoon";
          const action = mergedPayload.action || "run_drift_check";
          mergedPayload.command_id = mergedPayload.command_id || crypto.randomUUID();
          eventType = `command.${targetAgent}.${action}`;
        }

        const baseEnvelope = selectedSchema && selectedSchema.defaultEnvelope
          ? selectedSchema.defaultEnvelope
          : {};

        const envelope = ensureEnvelopeCompat(
          deepMerge(baseEnvelope, {
            ...msgEnvelope,
            event_id: msg.event_id || msgEnvelope.event_id || crypto.randomUUID(),
            event_type: eventType,
            timestamp: msg.timestamp || msgEnvelope.timestamp || new Date().toISOString(),
            version: msg.version || msgEnvelope.version || "1.0.0",
            source: (() => {
              const mergedSource = deepMerge(sourceDefaults, msg.source || msgEnvelope.source || {});
              mergedSource.type = normalizeSourceType(mergedSource.type);
              mergedSource.trigger_type = normalizeTriggerType(mergedSource.trigger_type);
              return mergedSource;
            })(),
            correlation_ids: toArray(msg.correlation_ids || msgEnvelope.correlation_ids || []),
            payload: mergedPayload,
          }),
          eventType
        );

        node.status({ fill: "yellow", shape: "dot", text: `posting ${eventType}` });

        const controller = new AbortController();
        const timeoutMs = Number.parseInt(config.timeoutMs || "10000", 10) || 10000;
        const timeout = setTimeout(() => controller.abort(), timeoutMs);

        let response;
        try {
          response = await fetch(normalizePublishUrl(msg.publishUrl || publishUrl), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(envelope),
            signal: controller.signal,
          });
        } finally {
          clearTimeout(timeout);
        }

        const bodyText = await response.text();
        let body = bodyText;
        try {
          body = JSON.parse(bodyText);
        } catch {
          // leave as text
        }

        msg.event_type = eventType;
        msg.routing_key = eventType;
        msg.envelope = envelope;
        msg.holyfields = {
          ...(msg.holyfields || {}),
          schemaPath: selectedSchemaPath || null,
          publishUrl: msg.publishUrl || publishUrl,
          responseStatus: response.status,
          responseBody: body,
        };

        if (!response.ok) {
          node.status({ fill: "red", shape: "ring", text: `HTTP ${response.status}` });
          done(new Error(`Bloodbank publish failed (${response.status}): ${bodyText}`));
          return;
        }

        node.status({ fill: "green", shape: "dot", text: `published ${eventType}` });
        send(msg);
        done();
      } catch (error) {
        node.status({ fill: "red", shape: "ring", text: "publish failed" });
        done(error);
      }
    });
  }

  RED.nodes.registerType("holyfields-out", HolyfieldsOutNode);
};
