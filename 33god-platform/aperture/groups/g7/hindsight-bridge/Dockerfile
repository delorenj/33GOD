# G7 hindsight-bridge — pluggable external memory backends via HTTP.
#
# DEGRADED BY DESIGN, CLIENT-OWNED LLM (zero AAI): the bridge never calls any
# built-in LLM. If GOD_LLM_BASE_URL/GOD_LLM_API_KEY are empty it comes up
# DEGRADED (keyword search only, no embeddings/rerank) and says so in
# /healthz — it must never crash. The config surface mirrors D1: ANY
# OpenAI-compatible endpoint the client chooses; nothing is hardcoded.
ARG GOD_PYTHON_IMAGE=python:3.12-alpine
FROM ${GOD_PYTHON_IMAGE}
WORKDIR /app
COPY server.py jsclient.py /app/
# Fresh named volumes inherit this mount point's ownership (docker
# copy-up), so /data must be writable by the runtime user, not root.
RUN mkdir -p /data && chown 65532:65532 /data
USER 65532:65532
CMD ["python", "-u", "/app/server.py"]
