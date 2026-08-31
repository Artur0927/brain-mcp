FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ripgrep \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/
RUN pip install --no-cache-dir .

ENV BRAIN_VAULT=/vault
ENV BRAIN_QDRANT_HOST=qdrant
ENV BRAIN_EMBED_URL=http://127.0.0.1:8091/embed
