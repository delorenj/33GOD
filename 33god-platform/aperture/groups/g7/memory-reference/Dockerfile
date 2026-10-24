# G7 memory-reference — REAL reference memory backend (SQLite FTS5 keyword
# store) implementing the pluggable-backend contract (POST /ingest,
# POST /query). No LLM. See memory-reference/server.py.
ARG GOD_PYTHON_IMAGE=python:3.12-alpine
FROM ${GOD_PYTHON_IMAGE}
WORKDIR /app
COPY server.py /app/server.py
# Fresh named volumes inherit this mount point's ownership (docker
# copy-up), so /data must be writable by the runtime user, not root.
RUN mkdir -p /data && chown 65532:65532 /data
USER 65532:65532
CMD ["python", "-u", "/app/server.py"]
