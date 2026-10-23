ARG GOD_PYTHON_IMAGE=python:3.12-alpine
FROM ${GOD_PYTHON_IMAGE}
WORKDIR /app
COPY main.py nats_publish.py /app/
USER 65532:65532
CMD ["python", "-u", "/app/main.py"]
