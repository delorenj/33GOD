FROM python:3.12-slim

WORKDIR /app

# Install uv for fast, deterministic installs
RUN pip install --no-cache-dir uv

COPY pyproject.toml .
COPY src/ src/

RUN uv pip install --system --no-cache .

ENV PORT=18696

EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn src.app:app --host 0.0.0.0 --port ${PORT}"]
