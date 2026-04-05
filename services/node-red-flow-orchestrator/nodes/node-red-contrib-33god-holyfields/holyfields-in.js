module.exports = function (RED) {
  const amqp = require("amqplib");
  const {
    getSchemaDetails,
    getValidator,
    registerAdminRoutes,
  } = require("./lib/holyfields");

  registerAdminRoutes(RED);

  function HolyfieldsInNode(config) {
    RED.nodes.createNode(this, config);
    const node = this;

    const rabbitUrl = (config.rabbitUrl || process.env.RABBIT_URL || "amqp://127.0.0.1:5672/").trim();
    const exchange = (config.exchange || "bloodbank.events.v1").trim();
    const routingKey = (config.routingKey || "#").trim();
    const queueName = (config.queueName || "").trim();
    const outputMode = config.outputMode || "envelope";
    const validationMode = config.validationMode || "warn";
    const schemaPath = config.schemaPath || "";

    let conn = null;
    let channel = null;
    let consumerTag = null;
    let closed = false;
    let reconnectAttempt = 0;
    let reconnectTimer = null;

    const BACKOFF_BASE_MS = 1000;
    const BACKOFF_MAX_MS = 30000;

    const schemaDetails = schemaPath ? getSchemaDetails(schemaPath) : null;
    const validator = schemaPath ? getValidator(schemaPath) : null;

    function ackSafe(msg) {
      try {
        if (channel && msg) channel.ack(msg);
      } catch {
        // noop
      }
    }

    function getBackoffMs() {
      const ms = Math.min(BACKOFF_BASE_MS * Math.pow(2, reconnectAttempt), BACKOFF_MAX_MS);
      return ms;
    }

    function scheduleReconnect() {
      if (closed) return;
      const delayMs = getBackoffMs();
      reconnectAttempt++;
      node.status({ fill: "yellow", shape: "ring", text: `reconnecting in ${(delayMs / 1000).toFixed(0)}s` });
      node.warn(`AMQP connection lost. Reconnecting in ${delayMs}ms (attempt ${reconnectAttempt})`);
      reconnectTimer = setTimeout(() => {
        if (closed) return;
        node.status({ fill: "yellow", shape: "ring", text: "reconnecting" });
        startConsumer().catch((error) => {
          node.error(`Reconnect attempt ${reconnectAttempt} failed: ${error.message}`);
          scheduleReconnect();
        });
      }, delayMs);
    }

    function cleanupConnection() {
      const oldChannel = channel;
      const oldConn = conn;
      channel = null;
      conn = null;
      consumerTag = null;
      if (oldChannel) {
        try { oldChannel.removeAllListeners(); oldChannel.close(); } catch { /* noop */ }
      }
      if (oldConn) {
        try { oldConn.removeAllListeners(); oldConn.close(); } catch { /* noop */ }
      }
    }

    function normalizeOutput(envelope, fields) {
      if (outputMode === "payload") {
        return {
          payload: envelope.payload,
          envelope,
          event_type: envelope.event_type,
          routing_key: fields?.routingKey || envelope.event_type,
          holyfields: {
            schemaPath: schemaPath || null,
          },
        };
      }

      return {
        payload: envelope,
        envelope,
        event_type: envelope.event_type,
        routing_key: fields?.routingKey || envelope.event_type,
        holyfields: {
          schemaPath: schemaPath || null,
        },
      };
    }

    async function startConsumer() {
      cleanupConnection();
      node.status({ fill: "yellow", shape: "ring", text: "connecting" });

      conn = await amqp.connect(rabbitUrl);

      conn.on("error", (err) => {
        if (closed) return;
        node.error(`AMQP connection error: ${err.message}`);
      });

      conn.on("close", () => {
        if (closed) return;
        cleanupConnection();
        scheduleReconnect();
      });

      channel = await conn.createChannel();

      channel.on("error", (err) => {
        if (closed) return;
        node.error(`AMQP channel error: ${err.message}`);
      });

      channel.on("close", () => {
        if (closed) return;
        channel = null;
        consumerTag = null;
      });

      await channel.assertExchange(exchange, "topic", { durable: true });

      const queueOptions = queueName
        ? { durable: true, autoDelete: false, exclusive: false }
        : { durable: false, autoDelete: true, exclusive: true };

      const assertedQueue = await channel.assertQueue(
        queueName || `nodered.holyfields.in.${node.id}`,
        queueOptions
      );

      await channel.bindQueue(assertedQueue.queue, exchange, routingKey);

      const consumed = await channel.consume(assertedQueue.queue, (msg) => {
        if (!msg || closed) return;

        try {
          const raw = msg.content.toString("utf8");
          const envelope = JSON.parse(raw);
          const out = normalizeOutput(envelope, msg.fields);

          if (validator && validationMode !== "off") {
            const valid = validator(envelope);
            if (!valid) {
              const errors = (validator.errors || []).map((e) => `${e.instancePath || "/"} ${e.message || "invalid"}`);
              out.holyfields.validation = {
                valid: false,
                mode: validationMode,
                schemaPath,
                errors,
              };

              if (validationMode === "strict") {
                node.warn(`Dropped invalid message for ${schemaPath}: ${errors.join("; ")}`);
                ackSafe(msg);
                return;
              }

              if (validationMode === "warn") {
                node.warn(`Validation warning (${schemaPath}): ${errors.join("; ")}`);
              }
            } else {
              out.holyfields.validation = {
                valid: true,
                mode: validationMode,
                schemaPath,
              };
            }
          }

          node.status({ fill: "green", shape: "dot", text: `${out.event_type || "event"}` });
          node.send(out);
          ackSafe(msg);
        } catch (error) {
          node.error(error, {
            payload: msg.content.toString("utf8"),
            routing_key: msg.fields?.routingKey,
          });
          ackSafe(msg);
        }
      });

      consumerTag = consumed.consumerTag;
      reconnectAttempt = 0;

      node.status({
        fill: "green",
        shape: "dot",
        text: schemaDetails ? `listening ${schemaDetails.eventType}` : `listening ${routingKey}`,
      });
    }

    startConsumer().catch((error) => {
      node.error(error);
      scheduleReconnect();
    });

    node.on("close", function (_removed, done) {
      closed = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }

      Promise.resolve()
        .then(async () => {
          if (channel && consumerTag) {
            try {
              await channel.cancel(consumerTag);
            } catch {
              // noop
            }
          }
          if (channel) {
            try {
              channel.removeAllListeners();
              await channel.close();
            } catch {
              // noop
            }
          }
          if (conn) {
            try {
              conn.removeAllListeners();
              await conn.close();
            } catch {
              // noop
            }
          }
        })
        .finally(() => {
          node.status({});
          done();
        });
    });
  }

  RED.nodes.registerType("holyfields-in", HolyfieldsInNode);
};
