FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# --- Plane domain ---
# Install plane-mcp-server from the `plane_mcp` named build context. The compose
# file passes it via:
#   build:
#     additional_contexts:
#       plane_mcp: /home/delorenj/code/plane-mcp-server
COPY --from=plane_mcp . /src/plane-mcp-server
RUN uv pip install --system --no-cache /src/plane-mcp-server

# --- Hub ---
COPY pyproject.toml README.md ./
COPY pipeline_hub/ ./pipeline_hub/
RUN uv pip install --system --no-cache .

EXPOSE 8080
ENV HUB_PORT=8080

ENTRYPOINT ["python", "-m", "pipeline_hub"]
CMD ["http"]
