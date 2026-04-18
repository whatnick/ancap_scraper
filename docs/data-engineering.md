# Data Engineering Workflows

This document covers the automated data pipelines: the Argo CronWorkflow for ingestion, the embedding pipeline, S3 synchronisation, and how to operate the system day-to-day.

## Pipeline Overview

The ingestion pipeline is a 5-step DAG (directed acyclic graph) orchestrated by Argo Workflows as a `CronWorkflow` running every Sunday at 2 AM UTC.

```
                    ┌───────────┐
                    │  Scrape   │
                    │  PDFs     │
                    └─────┬─────┘
                          │
              ┌───────────┼───────────┐
              ▼                       ▼
       ┌──────────┐           ┌──────────┐
       │  Render  │           │  Embed   │
       │  Pages   │           │  Vectors │
       └─────┬────┘           └─────┬────┘
             ▼                      │
       ┌──────────┐                 │
       │  Extract │                 │
       │  Tables  │                 │
       └─────┬────┘                 │
             │                      │
             └──────────┬───────────┘
                        ▼
                 ┌──────────┐
                 │  Sync S3 │
                 └──────────┘
```

**Key insight:** The embed step runs in parallel with render+extract because it works on the raw PDFs (text extraction), not the rendered images. This cuts total pipeline time significantly.

## Step 1: Scraper

**Image:** `ancap-scraper-pipeline`
**Module:** `ancap_scraper.get_model`

Hits the ANCAP API to discover all make/model/year combinations, then downloads each safety rating PDF. Skips files that already exist on the shared PVC.

```
ANCAP /api/config → makes/models
ANCAP /api/search → vehicle IDs + years
ANCAP /safety-ratings/{make}/{model}/{id} → scrape PDF link
Download PDF → /app/safety_data/{make}_{model}_{year}_{id}.pdf
```

**Output:** PDFs on `ancap-pdfs` PVC
**Duration:** 10-30 minutes (network-bound, first run is longest)
**Idempotent:** Yes — checks file existence before downloading

## Step 2: Renderer

**Image:** `ancap-scraper-pipeline`
**Module:** `ancap_scraper.get_table_image`

Renders every page of every PDF at 300 DPI to JPEG. Needed by the OCR step.

```python
for pdf in glob('/app/safety_data/*.pdf'):
    get_table(pdf)  # outputs out_{page}_{id}.jpg
```

**Output:** JPEG images alongside PDFs
**Duration:** 5-15 minutes (CPU-bound)
**Dependencies:** Scraper must complete first

## Step 3: Table Extractor

**Image:** `ancap-scraper-pipeline`
**Module:** `ancap_scraper.get_table_content`

For each PDF, takes the rendered last page (which contains the safety features table), runs Tesseract OCR for feature names, slices the AU/NZ availability columns into individual cells, classifies each cell using the SVM model, and saves as Excel.

```
Rendered page image
  → OCR (Tesseract) → feature names
  → Crop AU/NZ columns → slice into cells
  → SVM predict each cell → nought/cross/dash/sun/donut
  → Map to STANDARD/NOT AVAILABLE/OPTIONAL/...
  → Save → /app/excel/{make}_{model}_{year}_{id}.xlsx
```

**Output:** Excel files on `ancap-excel` PVC
**Duration:** 15-45 minutes (OCR is CPU-intensive)
**Dependencies:** Renderer must complete first
**Skips:** Files that already exist in the Excel output directory

## Step 4: Embedder

**Image:** `ancap-scraper-embedder`
**Module:** `services/embedder.py`

Loads all PDFs, splits them into ~1000-character chunks with 200-character overlap, embeds each chunk using Amazon Titan Embeddings v2 via Bedrock, and upserts into ChromaDB.

```
safety_data/*.pdf
  → PyPDFDirectoryLoader → raw document pages
  → RecursiveCharacterTextSplitter (chunk_size=1000, overlap=200)
  → BedrockEmbeddings (amazon.titan-embed-text-v2:0)
  → ChromaDB (collection: ancap_safety)
```

### Chunking Strategy

| Parameter | Value | Rationale |
|---|---|---|
| `chunk_size` | 1000 chars | Balances context richness with retrieval precision |
| `chunk_overlap` | 200 chars | Ensures sentences split at boundaries remain discoverable |
| `separators` | `\n\n`, `\n`, `. `, ` `, `` | Prefers paragraph/sentence boundaries over arbitrary splits |

### Metadata

Each chunk retains LangChain's default metadata:
- `source` — the PDF file path
- `page` — the 0-indexed page number

This metadata flows through to the query API's `sources` field in responses.

**Output:** Vectors in ChromaDB (accessed via `chromadb.ancap.svc.cluster.local:8000`)
**Duration:** 5-20 minutes (Bedrock API throughput-bound)
**Dependencies:** Scraper must complete first (embeds raw PDFs, not rendered images)
**Cloud cost:** ~$1-2 for initial ~500 PDFs; delta weekly runs are negligible

## Step 5: S3 Sync

**Image:** `amazon/aws-cli`

Synchronises PDFs and Excel files to S3 as a durable backup. Uses `--size-only` to avoid re-uploading unchanged files.

```bash
aws s3 sync /data/pdfs  s3://${S3_BUCKET}/pdfs/  --size-only
aws s3 sync /data/excel s3://${S3_BUCKET}/excel/ --size-only
```

**Dependencies:** All other steps must complete first
**Cloud cost:** ~$0.05/month for ~2 GB of data

## Scheduling

### CronWorkflow

The pipeline runs as an Argo `CronWorkflow`:

```yaml
schedule: "0 2 * * 0"  # Every Sunday at 2 AM UTC
concurrencyPolicy: Replace  # If a run overlaps, cancel the old one
```

ANCAP publishes new reports sporadically (not weekly), so a weekly cadence catches new data promptly without being wasteful.

### Manual Trigger

From the Tilt UI:
- Click the **trigger-ingestion** button

From the CLI:
```bash
# Submit from the CronWorkflow definition
argo submit -n ancap deploy/argo/ingestion-workflow.yaml --from=cronwf/ancap-ingestion

# Or create a standalone Workflow
argo submit -n ancap deploy/argo/ingestion-workflow.yaml
```

### One-Shot Embedding

To re-embed all PDFs without running the full pipeline (e.g., after changing the chunking strategy):

From the Tilt UI:
- Click the **run-embedder** button

From the CLI:
```bash
kubectl run ancap-embed-manual --rm -it --restart=Never -n ancap \
  --image=ancap-scraper-embedder \
  --env=CHROMA_HOST=chromadb \
  --env=CHROMA_PORT=8000 \
  -- python embedder.py --pdf-dir=/data/pdfs
```

## Shared Storage

All pipeline steps share data through Kubernetes PersistentVolumeClaims:

| PVC | Access Mode | Size | Contents |
|---|---|---|---|
| `ancap-pdfs` | ReadWriteMany | 10 Gi | Downloaded PDFs + rendered images |
| `ancap-excel` | ReadWriteMany | 2 Gi | Extracted Excel files |
| `ancap-chromadb` | ReadWriteMany | 5 Gi | ChromaDB persistent storage |
| `ancap-models` | ReadOnlyMany | 1 Gi | `img_model.p`, `table-detect/` configs |

Argo Workflow steps use a `volumeClaimTemplate` for scratch workspace and mount the shared PVCs for inputs/outputs.

## Monitoring

### Argo UI

Port-forward the Argo server to view workflow DAGs, logs, and status:

```bash
kubectl port-forward -n argo svc/argo-workflows-server 2746:2746
# Open http://localhost:2746
```

### Pipeline Logs

```bash
# List recent workflows
argo list -n ancap

# Watch a running workflow
argo watch -n ancap <workflow-name>

# Get logs from a specific step
argo logs -n ancap <workflow-name> --step scrape-pdfs
```

### ChromaDB Stats

```bash
# Check collection size
curl -s http://localhost:8000/api/v1/collections | python -m json.tool

# Count documents in the ancap_safety collection
curl -s http://localhost:8000/api/v1/collections/ancap_safety/count
```

## Recovery

### Re-run Failed Step

Argo supports retrying individual failed steps:

```bash
argo retry -n ancap <workflow-name> --node-field-selector=phase=Failed
```

### Full Re-index

To wipe and rebuild the vector store:

```bash
# Delete the ChromaDB PVC data
kubectl exec -n ancap chromadb-0 -- rm -rf /chroma/chroma/*

# Restart ChromaDB
kubectl rollout restart statefulset -n ancap chromadb

# Run the embedder
# (via Tilt button or kubectl run as shown above)
```

### Restore from S3

If local PVC data is lost:

```bash
kubectl run s3-restore --rm -it --restart=Never -n ancap \
  --image=amazon/aws-cli \
  --env=AWS_ACCESS_KEY_ID=$KEY \
  --env=AWS_SECRET_ACCESS_KEY=$SECRET \
  -- aws s3 sync s3://ancap-data/pdfs/ /data/pdfs/
```

## Data Lineage

Every answer from the query API includes source attribution:

```
User question
  → Embedded by Titan v2 → similarity search in ChromaDB
  → Top-4 chunks returned with metadata:
      source: "safety_data/toyota_corolla_2022_abc123.pdf"
      page: 7
  → Claude generates answer citing these chunks
  → Frontend displays sources as expandable section
```

This means you can always trace an answer back to the specific PDF page it came from.
