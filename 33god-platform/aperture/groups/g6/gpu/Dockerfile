# GPU-only source package from voxxy engine; no production image adoption.
FROM ghcr.io/astral-sh/uv:0.9.7@sha256:ba4857bf2a068e9bc0e64eed8563b065908a4cd6bfb66b531a9c424c8e25e142 AS uv
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04@sha256:517da2300c184c9999ec203c2665244bdebd3578d12fcc7065e83667932643d9
COPY --from=uv /uv /usr/local/bin/uv
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_INSTALL_DIR=/opt/python UV_PROJECT_ENVIRONMENT=/opt/venv HF_HOME=/models/huggingface
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 ca-certificates gcc g++ ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN uv python install 3.12
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
ENV PATH="/opt/venv/bin:$PATH"
COPY engine ./engine
CMD ["uvicorn", "engine.main:app", "--host", "0.0.0.0", "--port", "8000"]
