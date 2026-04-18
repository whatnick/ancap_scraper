# Architecture

## System Overview

ANCAP Scraper is a hybrid local-K8s + cloud architecture that minimises cloud spend by running all compute-local workloads on-premise and only reaching out to AWS for services that require GPU inference (Bedrock LLM/embeddings) or durable storage (S3).

```
┌─────────────────── LOCAL KUBERNETES CLUSTER ───────────────────────────┐
│                                                                        │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐               │
│  │  Streamlit   │   │  FastAPI      │   │  ChromaDB    │               │
│  │  Frontend    │◄─▶│  Query API    │◄─▶│  Vector      │               │
│  │  (Pod)       │   │  (Pod)        │   │  Store (PVC) │               │
│  └──────┬──────┘   └──────┬───────┘   └──────────────┘               │
│         │                  │                                           │
│         │                  │ Bedrock API (LLM + Embeddings)            │
│         │                  ▼                                           │
│  ┌──────┴──────────────────────────────────────┐                      │
│  │        Cloudflare Tunnel (cloudflared)       │                      │
│  │        Exposes frontend on public domain     │                      │
│  └──────────────────┬──────────────────────────┘                      │
│                     │                                                  │
│  ┌─────────────────────────────────────┐                              │
│  │    Argo Workflows  (CronWorkflow)   │                              │
│  │                                     │                              │
│  │  ┌───────────┐  ┌───────────────┐  │                              │
│  │  │ 1. Scrape │─▶│ 2. PDF→Image  │  │                              │
│  │  │   PDFs    │  │    Render     │  │                              │
│  │  └───────────┘  └───────┬──────┘  │                              │
│  │                          ▼         │                              │
│  │  ┌───────────────┐  ┌──────────┐  │                              │
│  │  │ 3. OCR+SVM    │─▶│ 4. Embed │  │                              │
│  │  │   Extract     │  │  + Index │  │                              │
│  │  └───────────────┘  └──────────┘  │                              │
│  │                          │         │                              │
│  │                          ▼         │                              │
│  │               ┌──────────────┐     │                              │
│  │               │ 5. Sync S3   │     │                              │
│  │               └──────────────┘     │                              │
│  └─────────────────────────────┘                                      │
│                                                                        │
│  Shared Volumes:                                                       │
│    PVC: ancap-pdfs      (safety_data/*.pdf)                           │
│    PVC: ancap-excel     (safety_data_excel/*.xlsx)                    │
│    PVC: ancap-chromadb  (vector store)                                │
│    PVC: ancap-models    (img_model.p, table-detect/)                  │
└────────────────────────────────────────────────────────────────────────┘
         │
         │  HTTPS (Cloudflare Tunnel)
         ▼
┌─────────────────── CLOUD (AWS + Cloudflare) ───────────────────┐
│                                                                  │
│  ┌──────────────────┐   ┌───────────────────────┐               │
│  │  Amazon Bedrock   │   │  S3 Bucket             │               │
│  │  - Titan Embed v2 │   │  s3://ancap-data/      │               │
│  │  - Claude 3.5     │   │    /pdfs/              │               │
│  │    Sonnet         │   │    /excel/             │               │
│  └──────────────────┘   │    /chromadb-backup/   │               │
│                          └───────────────────────┘               │
│                                                                  │
│  ┌──────────────────┐                                            │
│  │  Cloudflare DNS   │                                            │
│  │  ancap.yourdomain │                                            │
│  └──────────────────┘                                            │
└──────────────────────────────────────────────────────────────────┘
```

## Component Map

### Always-On Services (K8s Deployments)

| Service | Image | Port | Purpose |
|---|---|---|---|
| **frontend** | `ancap-scraper-frontend` | 8501 | Streamlit chat UI |
| **query-api** | `ancap-scraper-query-api` | 8000 | FastAPI RAG service |
| **chromadb** | `chromadb/chroma` | 8000 | Vector store (StatefulSet) |
| **cloudflared** | `cloudflare/cloudflared` | — | Tunnel to public internet |

### Batch Jobs (Argo Workflow Steps)

| Step | Image | Trigger | Purpose |
|---|---|---|---|
| **scraper** | `ancap-scraper-pipeline` | Weekly CronWorkflow | Downloads PDFs from ANCAP |
| **renderer** | `ancap-scraper-pipeline` | After scraper | Renders PDFs to page images |
| **extractor** | `ancap-scraper-pipeline` | After renderer | OCR + SVM → Excel |
| **embedder** | `ancap-scraper-embedder` | After scraper | PDF → chunks → Titan embeddings → ChromaDB |
| **s3-sync** | `amazon/aws-cli` | After all above | Syncs everything to S3 |

## Data Flow

```
ANCAP API
  │
  ├─ /api/config        → list of all makes/models
  ├─ /api/search        → vehicle IDs + rating years
  └─ /safety-ratings/…  → HTML page with PDF download link
        │
        ▼
  safety_data/*.pdf     (PVC: ancap-pdfs)
        │
        ├──────────────────────────────┐
        │                              │
        ▼                              ▼
  Page images (*.jpg)            PDF text chunks
        │                              │
        ▼                              ▼
  OCR features + SVM classify    Bedrock Titan Embed v2
        │                              │
        ▼                              ▼
  safety_data_excel/*.xlsx       ChromaDB collection
  (PVC: ancap-excel)             (PVC: ancap-chromadb)
        │                              │
        ├──────────┬───────────────────┤
        ▼          ▼                   ▼
      S3 backup   User question   Semantic retrieval
                       │                │
                       └──► Claude 3.5 ◄┘
                              │
                              ▼
                         Answer + sources
```

## Design Decisions

| Decision | Rationale |
|---|---|
| **Local ChromaDB** over OpenSearch Serverless | Saves ~$345/month AOSS minimum OCU cost; the ANCAP dataset (a few hundred PDFs) fits comfortably in a local vector store |
| **Local Argo Workflows** over AWS Step Functions | Free, runs natively on K8s, full DAG support, visual UI, CronWorkflow scheduling |
| **Bedrock** for LLM + Embeddings | Only service that *must* be remote (GPU inference); pay-per-token with no minimum commitment |
| **S3** as backup only, not primary store | Durable archive of PDFs and Excel; the working dataset lives on K8s PVCs for fast local access |
| **Cloudflare Tunnel** over ALB/CloudFront | Free tier available, zero inbound port requirements, automatic TLS, works behind NAT/firewalls |
| **Streamlit** over React/Next.js | Built-in chat widget, one-file app, no build step, sufficient for an internal data tool |
| **SOPS + age** over Vault/AWS Secrets Manager | Zero infrastructure, Git-native, simple key distribution for small teams |
| **Tilt** over Skaffold/DevSpace | Excellent Helm integration, live_update without rebuilds, built-in UI for manual triggers |

## Cloud Cost Estimate

| Service | Usage | Est. Monthly Cost |
|---|---|---|
| Bedrock Titan Embeddings | ~500 PDFs initial + weekly delta | ~$1-2 |
| Bedrock Claude 3.5 Sonnet | ~100 queries/day | ~$5-15 |
| S3 Standard | ~2 GB PDFs + Excel | ~$0.05 |
| Cloudflare Tunnel | Free tier | $0 |
| **Total** | | **~$6-18/month** |

Everything else runs on your local K8s cluster at zero cloud cost.

## Security Model

- **Secrets**: SOPS-encrypted with age keys; decrypted only at deploy time by Tilt, never stored in plaintext on disk or in Git
- **Network**: Cloudflare Tunnel provides TLS termination and DDoS protection; no ports exposed to public internet
- **AWS IAM**: Minimal permissions — `bedrock:InvokeModel` for Titan+Claude, `s3:PutObject`/`s3:GetObject` for the backup bucket
- **K8s RBAC**: Argo Workflows service account has permissions scoped to the `ancap` namespace only
