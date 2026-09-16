FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PORT=8080

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY requirements-render.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-render.txt

# SBERT 모델을 빌드할 때 미리 받아둠
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('jhgan/ko-sroberta-multitask')"

COPY . .

CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 1 --timeout 0 server:app"]