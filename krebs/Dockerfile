FROM python:3.12-slim
ARG PILOT_REVISION
LABEL org.opencontainers.image.title="Krebs execution controller"
LABEL org.opencontainers.image.version="2.0.0"
RUN apt-get update && apt-get install -y --no-install-recommends nodejs ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN pip install --no-cache-dir uv==0.8.22 && uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"
# Runtime must mount an immutable Pilot artifact at /opt/pilot, op credential
# resolver, enrolled manifests, and a compatible supervisor adapter. Container
# cannot claim readiness without those; host systemd is the supported v2 mode.
HEALTHCHECK CMD krebs health
ENTRYPOINT ["krebs"]
CMD ["serve"]
