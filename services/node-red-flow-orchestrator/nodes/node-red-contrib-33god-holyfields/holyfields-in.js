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

    const schemaDetails = schemaPath ? getSchemaDetails(schemaPath) : null;
    const validator = schemaPath ? getValidator(schemaPath) : null;

    function ackSafe(msg) {
      try {
        if (channel && msg) channel.ack(msg);
      } catch {
        // noop
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
      node.status({ fill: "yellow", shape: "ring", text: "connecting" });

      conn = await amqp.connect(rabbitUrl);
      channel = await conn.createChannel();

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

      node.status({
        fill: "green",
        shape: "dot",
        text: schemaDetails ? `listening ${schemaDetails.eventType}` : `listening ${routingKey}`,
      });
    }

    startConsumer().catch((error) => {
      node.status({ fill: "red", shape: "ring", text: "connect failed" });
      node.error(error);
    });

    node.on("close", function (_removed, done) {
      closed = true;

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
              await channel.close();
            } catch {
              // noop
            }
          }
          if (conn) {
            try {
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
