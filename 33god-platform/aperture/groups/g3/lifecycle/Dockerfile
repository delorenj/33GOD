ARG GOD_PYTHON_IMAGE=python:3.12-alpine
FROM ${GOD_PYTHON_IMAGE}
WORKDIR /app
COPY __init__.py models.py reconciler.py main.py nats_publish.py /app/lifecycle/
USER 65532:65532
CMD ["python", "-u", "-m", "lifecycle.main"]
