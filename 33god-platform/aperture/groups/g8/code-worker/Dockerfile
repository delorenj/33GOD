# G8 code-worker — the REAL lane: real git commits + real test runs.
# git is REQUIRED (apk add git) — the lane's whole point is real evidence.
ARG GOD_PYTHON_IMAGE=python:3.12-alpine
FROM ${GOD_PYTHON_IMAGE}
RUN apk add --no-cache git
WORKDIR /app
COPY worker.py jsclient.py /app/
RUN mkdir -p /data && chown 65532:65532 /data
USER 65532:65532
CMD ["python", "-u", "/app/worker.py"]
