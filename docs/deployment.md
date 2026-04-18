# Deployment

This document covers all deployment options: Tilt for local development, Docker Compose for a quick non-K8s stack, full Kubernetes manifests, Helm charts, SOPS secret management, and Cloudflare Tunnel for public access.

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Docker | 24+ | Container builds |
| kubectl | 1.28+ | K8s API client |
| Tilt | 0.33+ | Local K8s dev orchestrator |
| Helm | 3.14+ | Argo Workflows chart |
| sops | 3.8+ | Secret encryption |
| age | 1.1+ | Encryption key generation |
| A local K8s cluster | — | kind, minikube, k3d, or Docker Desktop |

## Tilt (Recommended)

Tilt is the primary development tool. It manages builds, deploys, port-forwards, and live-updates in a single `tilt up` command.

### First-Time Setup

```bash
# Interactive setup — generates age key, encrypts secrets, validates K8s context
./deploy/setup.sh
```

This script:
1. Checks all prerequisites are installed
2. Verifies a K8s context is active
3. Generates an `age` keypair for SOPS
4. Prompts for AWS and Cloudflare credentials
5. Encrypts secrets and writes `deploy/sops/secrets.enc.yaml`

### Starting

```bash
tilt up
# Opens Tilt UI at http://localhost:10350
```

### What Tilt Does

1. **Decrypts secrets** — runs `sops --decrypt` on `deploy/sops/secrets.enc.yaml`
2. **Builds 4 Docker images** from the multi-stage Dockerfile:
   - `ancap-scraper-pipeline` — scraper, renderer, extractor
   - `ancap-scraper-query-api` — FastAPI service
   - `ancap-scraper-frontend` — Streamlit app
   - `ancap-scraper-embedder` — embedding batch job
3. **Installs Argo Workflows** via Helm chart into the `argo` namespace
4. **Applies K8s manifests** — namespace, PVCs, ChromaDB, query-api, frontend
5. **Registers the CronWorkflow** for weekly ingestion
6. **Sets up port-forwards**:
   - ChromaDB → `localhost:8000`
   - Query API → `localhost:8080`
   - Frontend → `localhost:8501`

### Live Update

Tilt syncs code changes directly into running containers without rebuilding:

| Source File | Container Path | Reload |
|---|---|---|
| `ancap_scraper/**` | `/app/ancap_scraper/` | Manual restart |
| `services/query_api.py` | `/app/query_api.py` | Uvicorn auto-reload |
| `services/frontend_app.py` | `/app/frontend_app.py` | Streamlit auto-reload |
| `services/embedder.py` | `/app/embedder.py` | Next run picks up changes |

### Manual Triggers

The Tilt UI provides two manual trigger buttons:

| Button | What It Does |
|---|---|
| **trigger-ingestion** | Submits the Argo CronWorkflow for immediate execution |
| **run-embedder** | Runs a one-shot embedding job against the current PDFs |

### Cloudflare Tunnel (Optional)

```bash
ENABLE_TUNNEL=1 tilt up
```

Only deploys the `cloudflared` pod when the environment variable is set.

### Allowed K8s Contexts

The Tiltfile restricts to known local clusters to prevent accidental deployment to production:

- `kind-ancap`
- `minikube`
- `docker-desktop`
- `k3d-ancap`
- `rancher-desktop`

## Docker Compose (No K8s)

For quick testing without Kubernetes:

```bash
# Copy and fill in credentials
cp deploy/.env.example deploy/.env
vim deploy/.env

# Start the stack
docker compose -f deploy/docker-compose.yml up

# Run embedder once (after PDFs are in safety_data/)
docker compose -f deploy/docker-compose.yml --profile ingest up embedder
```

Services and ports:
- ChromaDB → `localhost:8000`
- Query API → `localhost:8080`
- Frontend → `localhost:8501`

No Argo Workflows or Cloudflare Tunnel in this mode.

## Dockerfile

The multi-stage Dockerfile builds all service images from a single file:

```
python:3.11-slim
  └─ base (+ Tesseract, system libs, ancap_scraper package)
       ├─ pipeline     (+ ML deps, training data, table-detect configs)
       ├─ query-api    (+ FastAPI, LangChain, ChromaDB client, Bedrock)
       ├─ embedder     (+ LangChain, ChromaDB client, Bedrock)
       └─ frontend     (Streamlit + requests only, no base deps)
```

Build individual targets:
```bash
docker build --target query-api -t ancap-scraper-query-api .
docker build --target frontend -t ancap-scraper-frontend .
docker build --target pipeline -t ancap-scraper-pipeline .
docker build --target embedder -t ancap-scraper-embedder .
```

## Kubernetes Manifests

All manifests are in `deploy/k8s/` and target the `ancap` namespace.

### Resources

| File | Kind | Name | Notes |
|---|---|---|---|
| `namespace.yaml` | Namespace | `ancap` | Created by Tilt automatically |
| `pvc.yaml` | PVC × 4 | `ancap-pdfs`, `ancap-excel`, `ancap-chromadb`, `ancap-models` | ReadWriteMany; size the storage class for your cluster |
| `secrets.yaml` | Secret + ConfigMap | `aws-credentials`, `cloudflare-tunnel`, `ancap-config` | Deprecated — use SOPS instead |
| `chromadb.yaml` | StatefulSet + Service | `chromadb` | Persistent vector store |
| `query-api.yaml` | Deployment + Service | `query-api` | Health probes on `/health` |
| `frontend.yaml` | Deployment + Service | `frontend` | Health probe on `/healthz` |
| `cloudflared.yaml` | Deployment | `cloudflared` | Token from SOPS secret |

### Storage

PVCs use `ReadWriteMany` access mode. In `kind`, this requires a CSI driver that supports RWX (e.g., `nfs-provisioner`). For `minikube` or `k3d`, the default `hostPath` provisioner works for single-node clusters but only supports `ReadWriteOnce` — update the PVC access mode accordingly.

## Helm — Argo Workflows

Argo Workflows is installed via the [official Helm chart](https://github.com/argoproj/argo-helm) with custom values in `deploy/helm/argo-workflows-values.yaml`:

| Setting | Value | Why |
|---|---|---|
| `server.extraArgs` | `--auth-mode=server` | No SSO for local dev |
| `controller.containerRuntimeExecutor` | `emissary` | Works without Docker socket access |
| `controller.workflowNamespaces` | `[ancap]` | Scope to our namespace |
| `controller.persistence.archive` | `false` | No Postgres needed locally |
| Chart version | `0.45.3` | Pinned for reproducibility |

Tilt manages the Helm install automatically. For manual installation:

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm install argo-workflows argo/argo-workflows \
  -n argo --create-namespace \
  -f deploy/helm/argo-workflows-values.yaml
```

## SOPS Secret Management

All sensitive credentials are encrypted with [SOPS](https://github.com/getsops/sops) using [age](https://github.com/FiloSottile/age) keys. See `deploy/sops/README.md` for full instructions.

### File Layout

```
.sops.yaml                    # SOPS config — maps path patterns to age public keys
deploy/sops/
├── README.md                 # Setup guide
├── secrets.template.yaml     # Template with placeholder values (committed)
├── secrets.enc.yaml          # Encrypted secrets (committed — safe for Git)
├── age-key.txt               # Private key (NEVER committed — in .gitignore)
└── secrets.dec.yaml          # Plaintext (NEVER committed — in .gitignore)
```

### How Secrets Flow

```
secrets.template.yaml → (fill in) → secrets.dec.yaml
                                          ↓
                                    sops --encrypt
                                          ↓
              secrets.enc.yaml ← (committed to Git)
                     ↓
              Tiltfile: sops --decrypt
                     ↓
         secrets.decrypted.yaml → kubectl apply → K8s Secrets
              (gitignored)
```

### Commands

```bash
# Edit encrypted secrets in $EDITOR (decrypts, edits, re-encrypts)
sops deploy/sops/secrets.enc.yaml

# One-off decrypt to stdout
sops --decrypt deploy/sops/secrets.enc.yaml

# Re-encrypt after changing .sops.yaml keys
sops updatekeys deploy/sops/secrets.enc.yaml
```

### Team Sharing

Share `age-key.txt` via a secure channel (1Password, Vault, etc.). Each team member sets:

```bash
export SOPS_AGE_KEY_FILE=/path/to/age-key.txt
```

## Cloudflare Tunnel

Exposes the Streamlit frontend to the public internet without opening any inbound ports or configuring port forwarding.

### Setup

```bash
# 1. Install cloudflared
brew install cloudflared  # or download from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

# 2. Authenticate
cloudflared tunnel login

# 3. Create a tunnel
cloudflared tunnel create ancap-tunnel

# 4. Route DNS
cloudflared tunnel route dns ancap-tunnel ancap.yourdomain.com

# 5. Copy the tunnel token into SOPS secrets
sops deploy/sops/secrets.enc.yaml
# Set TUNNEL_TOKEN to the value from step 3

# 6. Enable in Tilt
ENABLE_TUNNEL=1 tilt up
```

### Routing

Defined in `deploy/cloudflared-config.yaml`:

| Hostname | Backend Service |
|---|---|
| `ancap.yourdomain.com` | `http://frontend:8501` |
| `ancap-api.yourdomain.com` | `http://query-api:8000` |
| (catch-all) | 404 |

### In K8s

The `cloudflared` Deployment runs the tunnel client using a token from the SOPS-encrypted secret. It connects outbound to Cloudflare's edge — no LoadBalancer or Ingress resource needed.

## AWS IAM Policy

Minimum required permissions for the `aws-credentials` secret:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::ancap-data",
        "arn:aws:s3:::ancap-data/*"
      ]
    }
  ]
}
```
