# Base image for all ancap_scraper services
FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ancap_scraper/ ancap_scraper/
COPY img_model.p .
COPY setup.cfg .

# ---- Scraper / Pipeline worker ----
FROM base AS pipeline
COPY ancap_scraper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt boto3
COPY data/ data/
COPY training/ training/
COPY table-detect/ table-detect/

# ---- Query API ----
FROM base AS query-api
RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] \
    langchain langchain-aws langchain-community \
    chromadb boto3 pypdf tiktoken
COPY services/query_api.py .
EXPOSE 8000
CMD ["uvicorn", "query_api:app", "--host", "0.0.0.0", "--port", "8000"]

# ---- Streamlit Frontend ----
FROM python:3.11-slim AS frontend
WORKDIR /app
RUN pip install --no-cache-dir streamlit requests
COPY services/frontend_app.py .
EXPOSE 8501
CMD ["streamlit", "run", "frontend_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]

# ---- Embedder ----
FROM base AS embedder
RUN pip install --no-cache-dir \
    langchain langchain-aws langchain-community \
    chromadb boto3 pypdf tiktoken
COPY services/embedder.py .
CMD ["python", "embedder.py"]

# ---- S3 Sync ----
FROM amazon/aws-cli:latest AS s3-sync
# Used as a step container in Argo; no custom code needed
