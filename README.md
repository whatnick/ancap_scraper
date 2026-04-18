# ANCAP Scraper

End-to-end pipeline that scrapes vehicle safety test data from the [ANCAP website](https://www.ancap.com.au), extracts structured tables from PDF reports using OCR and ML classification, generates vector embeddings for semantic search, and serves a conversational Q&A interface — all running on a local Kubernetes cluster with minimal cloud dependencies.

## What It Does

1. **Scrapes** every published ANCAP safety rating PDF via their public API
2. **Renders** PDF pages to images and **extracts** feature availability tables using Tesseract OCR + an SVM image classifier
3. **Embeds** the full PDF text into a vector store (ChromaDB) using Amazon Titan embeddings
4. **Serves** a Streamlit chat UI backed by a FastAPI RAG service powered by Claude on Bedrock
5. **Syncs** all data to S3 for durable backup

## Quick Start

```bash
# Prerequisites: Python 3.11+, Tesseract OCR
pip install -r ancap_scraper/requirements.txt

# Scrape PDFs
PYTHONPATH=. python ancap_scraper/get_model.py

# Extract tables from PDFs (batch — years 2018-2022)
PYTHONPATH=. python ancap_scraper/parse_all_reports.py

# Ask questions via LLM (requires OpenAI key or Bedrock setup)
PYTHONPATH=. python ancap_scraper/langchain_parse.py
```

For the full Kubernetes deployment with Tilt:

```bash
./deploy/setup.sh   # one-time: installs age key, encrypts secrets
tilt up              # starts all services on local K8s
```

## Architecture

```
 ANCAP Website ──► Scraper ──► PDFs ──► OCR + SVM ──► Excel
                                  │
                                  └──► Chunker ──► Bedrock Titan ──► ChromaDB
                                                                        │
                    Streamlit ◄── FastAPI ◄── RAG Chain ◄── Claude 3.5 ◄┘
                       │
                  Cloudflare Tunnel ──► Public Internet
```

> Full architecture diagram and rationale → [docs/architecture.md](docs/architecture.md)

## Documentation

| Document | Description |
|---|---|
| [docs/architecture.md](docs/architecture.md) | System architecture, component diagram, design decisions |
| [docs/backend.md](docs/backend.md) | Scraper, OCR pipeline, SVM classifier, ML models |
| [docs/frontend.md](docs/frontend.md) | Streamlit UI, FastAPI query service, RAG chain |
| [docs/deployment.md](docs/deployment.md) | Kubernetes, Tilt, Docker, Helm, SOPS, Cloudflare |
| [docs/data-engineering.md](docs/data-engineering.md) | Argo Workflows, embedding pipeline, S3 sync, scheduling |

## Project Structure

```
ancap_scraper/              # Core Python package
├── get_model.py            # Web scraper — downloads PDFs from ANCAP
├── get_table_image.py      # PDF → image renderer (pypdfium2)
├── get_table_content.py    # OCR + classification → Excel extraction
├── classify_result.py      # SVM image classifier (nought/cross/dash/sun/donut)
├── detect_table.py         # Experimental DETR-based table detection
├── parse_all_reports.py    # Batch orchestrator for years 2018-2022
├── langchain_parse.py      # LLM Q&A over PDFs and Excel
├── prepare_yolov5.py       # YOLOv5 dataset splitting utility
├── headers.py              # HTTP headers for ANCAP API
└── requirements.txt        # Python dependencies

services/                   # Microservice entrypoints
├── query_api.py            # FastAPI RAG service (Bedrock + ChromaDB)
├── frontend_app.py         # Streamlit chat UI
└── embedder.py             # PDF embedding batch job

deploy/                     # Infrastructure & deployment
├── setup.sh                # Interactive bootstrap script
├── docker-compose.yml      # Local dev stack (no K8s)
├── cloudflared-config.yaml # Cloudflare Tunnel routing
├── k8s/                    # Kubernetes manifests
├── argo/                   # Argo CronWorkflow (ingestion DAG)
├── helm/                   # Helm chart values (Argo Workflows)
└── sops/                   # SOPS-encrypted secrets

training/                   # SVM training images (5 classes)
table-detect/               # HuggingFace model configs (DETR, Table Transformer)
page_samples/               # YOLOv5 annotated dataset
data/                       # Symbol templates for training augmentation
tests/                      # Unit tests
```

## Roadmap

- [ ] Template matching for fine-aligning table crop regions ([#1](https://github.com/whatnick/ancap_scraper/issues/1))
- [ ] ML-based table detection to replace hard-coded coordinates ([#2](https://github.com/whatnick/ancap_scraper/issues/2))
- [ ] Retrain SVM using augmented template data ([#3](https://github.com/whatnick/ancap_scraper/issues/3))
- [ ] Random forest / neural network classifiers for symbology
- [ ] Vehicle image linking and impact test photo extraction
- [ ] Manual canonical safety features for OCR error correction
- [ ] Bedrock Knowledge Base as a fully managed alternative to local ChromaDB

## License

See repository for license information.