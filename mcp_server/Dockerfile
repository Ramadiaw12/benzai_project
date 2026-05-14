# Dockerfile — Serveur MCP
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt* ./
RUN pip install --no-cache-dir fastapi uvicorn httpx langchain-core 2>/dev/null || true

COPY . .

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]