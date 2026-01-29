FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/

# Install dependencies
RUN uv sync --no-dev

# Run consumer
CMD ["uv", "run", "python", "-m", "src.theboard_meeting_trigger.consumer"]
