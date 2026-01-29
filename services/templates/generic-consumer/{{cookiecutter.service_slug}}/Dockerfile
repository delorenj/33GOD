FROM python:{{ cookiecutter.python_version }}-slim-bookworm

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency definitions
COPY pyproject.toml .

# Install dependencies
RUN uv pip install --system .

# Copy source code
COPY src/ src/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the consumer
CMD ["python", "-m", "src.consumer"]
