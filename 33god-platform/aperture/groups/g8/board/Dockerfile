# G8 board adapter — real sandbox board with Plane's state vocabulary.
# stdlib-only Python (no pip installs; bus via jsclient.py g7 byte-copy).
ARG GOD_PYTHON_IMAGE=python:3.12-alpine
FROM ${GOD_PYTHON_IMAGE}
WORKDIR /app
COPY adapter.py jsclient.py /app/
# Fresh named volumes inherit the mount point's ownership (docker copy-up),
# so /data must be writable by the runtime user, not root.
RUN mkdir -p /data && chown 65532:65532 /data
USER 65532:65532
CMD ["python", "-u", "/app/adapter.py"]
