# ANCAP Scraper — Deployment

This directory contains all infrastructure and deployment configuration.

For full documentation, see:
- [Architecture](../docs/architecture.md) — system diagram, design decisions, cost estimate
- [Backend](../docs/backend.md) — scraper, OCR pipeline, SVM classifier, query API
- [Frontend](../docs/frontend.md) — Streamlit UI, API contract, conversation memory
- [Deployment](../docs/deployment.md) — Tilt, Docker, K8s, Helm, SOPS, Cloudflare
- [Data Engineering](../docs/data-engineering.md) — Argo Workflows, embedding pipeline, S3 sync

## Quick Start

```bash
# 1. One-time setup (generates age key, encrypts secrets)
./setup.sh

# 2. Start all services on local K8s
cd .. && tilt up

# 3. Access
#    Frontend:  http://localhost:8501
#    Query API: http://localhost:8080
#    ChromaDB:  http://localhost:8000
#    Tilt UI:   http://localhost:10350
```

## Directory Layout

```
deploy/
├── setup.sh                  # Interactive bootstrap script
├── docker-compose.yml        # Non-K8s local dev stack
├── cloudflared-config.yaml   # Cloudflare Tunnel routing rules
├── .env.example              # Template for docker-compose env vars
├── k8s/                      # Kubernetes manifests
│   ├── namespace.yaml
│   ├── pvc.yaml
│   ├── secrets.yaml          # Reference only — use SOPS
│   ├── chromadb.yaml
│   ├── query-api.yaml
│   ├── frontend.yaml
│   └── cloudflared.yaml
├── argo/                     # Argo Workflows
│   └── ingestion-workflow.yaml   # CronWorkflow (weekly DAG pipeline)
├── helm/                     # Helm chart values
│   └── argo-workflows-values.yaml
└── sops/                     # SOPS encrypted secrets
    ├── README.md             # Detailed setup guide
    ├── secrets.template.yaml # Template with placeholders
    ├── secrets.enc.yaml      # Encrypted (safe for Git)
    ├── age-key.txt           # Private key (NEVER commit)
    └── secrets.dec.yaml      # Plaintext (NEVER commit)
```
