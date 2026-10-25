# G8 momod — Momo-shaped orchestration worker (WIP-lease discipline).
# stdlib-only Python; no pip installs.
ARG GOD_PYTHON_IMAGE=python:3.12-alpine
FROM ${GOD_PYTHON_IMAGE}
WORKDIR /app
COPY orchestrator.py jsclient.py /app/
RUN mkdir -p /data && chown 65532:65532 /data
USER 65532:65532
CMD ["python", "-u", "/app/orchestrator.py"]
