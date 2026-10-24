# CPU packaging of voxxy core and Vinyl server; see vendor/SOURCES.json.
FROM ghcr.io/astral-sh/uv:0.9.7@sha256:ba4857bf2a068e9bc0e64eed8563b065908a4cd6bfb66b531a9c424c8e25e142 AS uv
FROM python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 ffmpeg espeak-ng ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY vendor/vox/pyproject.toml vendor/vox/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
ENV PATH="/app/.venv/bin:$PATH"
COPY requirements.lock.txt ./
RUN uv pip install --python /app/.venv/bin/python -r requirements.lock.txt
COPY vendor/vox/app /app/app
COPY vendor/vinyl/vinyl /app/vinyl
COPY runtime /app/runtime
COPY models.lock.json /app/models.lock.json
COPY smoke /app/smoke
RUN useradd -m -u 10001 -g voice voice && mkdir -p /data/voices /data/audio-cache /pipeline/inbox /pipeline/input /pipeline/receipts /models && chown -R voice:voice /data /pipeline /models
USER voice
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
