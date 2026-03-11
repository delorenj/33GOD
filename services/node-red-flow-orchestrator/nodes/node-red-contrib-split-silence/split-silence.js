module.exports = function (RED) {
  const { execFile } = require("child_process");
  const path = require("path");
  const fs = require("fs");

  function SplitSilenceNode(config) {
    RED.nodes.createNode(this, config);
    const node = this;

    // Config with defaults
    this.minSilenceMin = parseFloat(config.minSilence) || 20;
    this.thresholdDb = parseFloat(config.threshold) || -40;
    this.minActivitySec = parseFloat(config.minActivity) || 60;
    this.outputDir = config.outputDir || "";
    this.outputFormat = config.outputFormat || "mp3";

    node.on("input", function (msg, send, done) {
      send = send || function () { node.send.apply(node, arguments); };
      done = done || function (err) { if (err) node.error(err, msg); };

      const inputFile = msg.filename || msg.payload;
      if (!inputFile || typeof inputFile !== "string") {
        done(new Error("No input file. Set msg.filename or msg.payload to a file path."));
        return;
      }

      if (!fs.existsSync(inputFile)) {
        done(new Error("File not found: " + inputFile));
        return;
      }

      const minSilenceSec = node.minSilenceMin * 60;
      const outDir = node.outputDir || path.dirname(inputFile);
      const baseName = path.basename(inputFile, path.extname(inputFile));

      node.status({ fill: "blue", shape: "dot", text: "detecting silence..." });

      // Step 1: get duration via ffprobe
      getDuration(inputFile, function (err, totalDuration) {
        if (err) {
          node.status({ fill: "red", shape: "ring", text: "ffprobe failed" });
          done(err);
          return;
        }

        // Step 2: detect silence regions
        detectSilence(inputFile, minSilenceSec, node.thresholdDb, function (err, silences) {
          if (err) {
            node.status({ fill: "red", shape: "ring", text: "detection failed" });
            done(err);
            return;
          }

          // No silence regions found = file is already all-activity, pass through as-is
          if (silences.length === 0) {
            node.status({ fill: "green", shape: "dot", text: "no silence, pass-through" });
            var passMsg = {
              payload: inputFile,
              filename: inputFile,
              event: msg.event,
              topic: msg.topic,
              chunk: {
                file: inputFile,
                chunk: 1,
                total_chunks: 1,
                start: 0,
                end: totalDuration,
                duration: totalDuration,
                source: inputFile,
                passthrough: true
              },
              parts: { id: msg._msgid, type: "array", count: 1, index: 0, len: 1 },
              meta: msg.meta || {}
            };
            send(passMsg);
            done();
            return;
          }

          // Step 3: invert silence to activity regions
          var activities = invertSilences(silences, totalDuration);

          // Filter short activity chunks
          activities = activities.filter(function (a) {
            return (a.end - a.start) >= node.minActivitySec;
          });

          if (activities.length === 0) {
            node.status({ fill: "yellow", shape: "ring", text: "no activity found" });
            node.warn("No activity chunks found above minimum duration");
            done();
            return;
          }

          node.status({
            fill: "blue", shape: "dot",
            text: "extracting " + activities.length + " chunk(s)..."
          });

          // Step 4: extract chunks sequentially
          var results = [];
          var idx = 0;

          function extractNext() {
            if (idx >= activities.length) {
              // All done, send one message per chunk
              node.status({
                fill: "green", shape: "dot",
                text: activities.length + " chunk(s) extracted"
              });

              for (var i = 0; i < results.length; i++) {
                var outMsg = {
                  payload: results[i].file,
                  filename: results[i].file,
                  event: msg.event,
                  topic: msg.topic,
                  chunk: results[i],
                  parts: {
                    id: msg._msgid,
                    type: "array",
                    count: results.length,
                    index: i,
                    len: results.length
                  },
                  // Preserve upstream context
                  meta: msg.meta || {},
                  _msgid: undefined
                };
                send(outMsg);
              }
              done();
              return;
            }

            var activity = activities[idx];
            var duration = activity.end - activity.start;
            var chunkNum = String(idx + 1).padStart(3, "0");
            var chunkName = baseName + "_chunk_" + chunkNum + "." + node.outputFormat;
            var chunkPath = path.join(outDir, chunkName);

            node.status({
              fill: "blue", shape: "dot",
              text: "chunk " + (idx + 1) + "/" + activities.length
            });

            extractChunk(inputFile, chunkPath, activity.start, duration, node.outputFormat,
              function (err) {
                if (err) {
                  node.warn("Failed to extract chunk " + (idx + 1) + ": " + err.message);
                  idx++;
                  extractNext();
                  return;
                }

                results.push({
                  file: chunkPath,
                  chunk: idx + 1,
                  total_chunks: activities.length,
                  start: activity.start,
                  end: activity.end,
                  duration: duration,
                  source: inputFile
                });
                idx++;
                extractNext();
              }
            );
          }

          extractNext();
        });
      });
    });

    node.on("close", function () {
      node.status({});
    });
  }

  /**
   * Get file duration via ffprobe.
   */
  function getDuration(filePath, callback) {
    execFile("ffprobe", [
      "-v", "quiet",
      "-print_format", "json",
      "-show_format",
      filePath
    ], { maxBuffer: 1024 * 1024 }, function (err, stdout) {
      if (err) return callback(err);
      try {
        var data = JSON.parse(stdout);
        callback(null, parseFloat(data.format.duration));
      } catch (e) {
        callback(new Error("Failed to parse ffprobe output: " + e.message));
      }
    });
  }

  /**
   * Run ffmpeg silencedetect and parse silence intervals from stderr.
   */
  function detectSilence(filePath, minSilenceSec, thresholdDb, callback) {
    var args = [
      "-i", filePath,
      "-af", "silencedetect=noise=" + thresholdDb + "dB:d=" + minSilenceSec,
      "-f", "null", "-"
    ];

    // silencedetect on large files can take a while, no timeout
    var proc = execFile("ffmpeg", args, {
      maxBuffer: 10 * 1024 * 1024,
      timeout: 0
    }, function (err, stdout, stderr) {
      // ffmpeg exits non-zero sometimes with null output, but stderr has our data
      if (!stderr) {
        return callback(err || new Error("No ffmpeg output"));
      }

      var starts = [];
      var ends = [];
      var match;

      var startRe = /silence_start:\s*([\d.]+)/g;
      while ((match = startRe.exec(stderr)) !== null) {
        starts.push(parseFloat(match[1]));
      }

      var endRe = /silence_end:\s*([\d.]+)/g;
      while ((match = endRe.exec(stderr)) !== null) {
        ends.push(parseFloat(match[1]));
      }

      var silences = [];
      for (var i = 0; i < starts.length; i++) {
        silences.push({
          start: starts[i],
          end: i < ends.length ? ends[i] : null
        });
      }

      callback(null, silences);
    });
  }

  /**
   * Invert silence intervals into activity intervals.
   */
  function invertSilences(silences, totalDuration) {
    var activities = [];
    var cursor = 0.0;

    for (var i = 0; i < silences.length; i++) {
      if (silences[i].start > cursor) {
        activities.push({ start: cursor, end: silences[i].start });
      }
      cursor = silences[i].end !== null ? silences[i].end : totalDuration;
    }

    if (cursor < totalDuration) {
      activities.push({ start: cursor, end: totalDuration });
    }

    return activities;
  }

  /**
   * Extract a time range from input file.
   */
  function extractChunk(inputFile, outputFile, startSec, durationSec, format, callback) {
    // Ensure output directory exists
    var dir = path.dirname(outputFile);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    var codecArgs;
    switch (format) {
      case "wav":
        codecArgs = ["-acodec", "pcm_s16le"];
        break;
      case "ogg":
        codecArgs = ["-acodec", "libvorbis", "-q:a", "5"];
        break;
      case "m4a":
        codecArgs = ["-acodec", "aac", "-b:a", "192k"];
        break;
      default: // mp3
        codecArgs = ["-acodec", "libmp3lame", "-q:a", "2"];
    }

    var args = [
      "-ss", String(startSec),
      "-i", inputFile,
      "-t", String(durationSec),
      "-vn" // strip video track
    ].concat(codecArgs).concat(["-y", outputFile]);

    execFile("ffmpeg", args, {
      maxBuffer: 1024 * 1024,
      timeout: 0
    }, function (err) {
      if (err) return callback(err);
      if (!fs.existsSync(outputFile)) {
        return callback(new Error("ffmpeg did not create output: " + outputFile));
      }
      callback(null);
    });
  }

  RED.nodes.registerType("split-silence", SplitSilenceNode);
};
