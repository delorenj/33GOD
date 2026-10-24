# G7 enrichment worker — real typed extraction pass over the BLOODBANK bus.
#
# ONE real pass, no fake enrichment: reads canonical bloodbank.evt.* events,
# extracts typed records into a side table (worker-owned Postgres), and
# publishes derived canonical events (bloodbank.<domain>.<entity>.enriched,
# 4-token type / 5-token subject) whose causationid = the source event id.
# No LLM involved anywhere in this pass — deterministic extraction only.
ARG GOD_PYTHON_IMAGE=python:3.12-alpine
FROM ${GOD_PYTHON_IMAGE}
WORKDIR /app
COPY worker.py jsclient.py /app/
# Fresh named volumes inherit this mount point's ownership (docker
# copy-up), so /data must be writable by the runtime user, not root.
RUN mkdir -p /data && chown 65532:65532 /data
USER 65532:65532
CMD ["python", "-u", "/app/worker.py"]
