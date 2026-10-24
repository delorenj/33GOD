FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY candystore/ ./candystore/
RUN pip install --no-cache-dir -e "."

COPY migrations/ ./migrations/
COPY static/ ./static/

ENV PYTHONUNBUFFERED=1
ENV APP_PORT=3001

EXPOSE 3001
CMD ["python", "-m", "candystore.main"]
