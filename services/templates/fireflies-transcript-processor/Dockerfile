FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install -e .

# Copy source code
COPY src/ ./src/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import {{ cookiecutter.service_module }}.consumer" || exit 1

# Run the consumer
CMD ["python", "-m", "{{ cookiecutter.service_module }}.consumer"]
