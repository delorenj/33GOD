FROM python:3.11-slim
WORKDIR /app
# Install system deps required for building psycopg2 and running
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Bake model into image
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3002"]
