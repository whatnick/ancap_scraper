# Tiltfile — orchestrates all ANCAP microservices on local K8s
# Prerequisites:
#   brew install tilt-dev/tap/tilt  (or curl -fsSL https://raw.githubusercontent.com/tilt-dev/tilt/master/scripts/install.sh | bash)
#   A local K8s context (kind, minikube, k3d, Docker Desktop)
#   sops + age installed (see deploy/sops/README.md)
#
# Usage:
#   cd /path/to/ancap_scraper
#   tilt up

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
allow_k8s_contexts([
    'kind-ancap',
    'minikube',
    'docker-desktop',
    'k3d-ancap',
    'rancher-desktop',
])

load('ext://namespace', 'namespace_create')
namespace_create('ancap')
namespace_create('argo')

# ---------------------------------------------------------------------------
# SOPS secret decryption — decrypt at tilt-up time, never commit plaintext
# ---------------------------------------------------------------------------
local_resource(
    'sops-decrypt-secrets',
    cmd='sops --decrypt deploy/sops/secrets.enc.yaml > deploy/k8s/secrets.decrypted.yaml',
    deps=['deploy/sops/secrets.enc.yaml'],
    labels=['secrets'],
)

# Apply decrypted secrets (Tilt watches the output file)
k8s_yaml('deploy/k8s/secrets.decrypted.yaml')

# ---------------------------------------------------------------------------
# Shared K8s resources (namespace, PVCs, configmap)
# ---------------------------------------------------------------------------
k8s_yaml([
    'deploy/k8s/pvc.yaml',
])

# ---------------------------------------------------------------------------
# Docker builds — multi-stage targets
# ---------------------------------------------------------------------------
docker_build(
    'ancap-scraper-pipeline',
    context='.',
    dockerfile='Dockerfile',
    target='pipeline',
    live_update=[
        sync('./ancap_scraper', '/app/ancap_scraper'),
    ],
)

docker_build(
    'ancap-scraper-query-api',
    context='.',
    dockerfile='Dockerfile',
    target='query-api',
    live_update=[
        sync('./services/query_api.py', '/app/query_api.py'),
    ],
)

docker_build(
    'ancap-scraper-frontend',
    context='.',
    dockerfile='Dockerfile',
    target='frontend',
    live_update=[
        sync('./services/frontend_app.py', '/app/frontend_app.py'),
    ],
)

docker_build(
    'ancap-scraper-embedder',
    context='.',
    dockerfile='Dockerfile',
    target='embedder',
    live_update=[
        sync('./services/embedder.py', '/app/embedder.py'),
    ],
)

# ---------------------------------------------------------------------------
# Argo Workflows — install via Helm chart
# ---------------------------------------------------------------------------
load('ext://helm_resource', 'helm_resource', 'helm_repo')

helm_repo(
    'argo',
    'https://argoproj.github.io/argo-helm',
    labels=['argo'],
)

helm_resource(
    'argo-workflows',
    'argo/argo-workflows',
    namespace='argo',
    flags=[
        '--values=deploy/helm/argo-workflows-values.yaml',
        '--version=0.45.3',
    ],
    labels=['argo'],
    resource_deps=['sops-decrypt-secrets'],
)

# ---------------------------------------------------------------------------
# ChromaDB — vector store
# ---------------------------------------------------------------------------
k8s_yaml('deploy/k8s/chromadb.yaml')
k8s_resource(
    'chromadb',
    port_forwards=['8000:8000'],
    labels=['datastores'],
)

# ---------------------------------------------------------------------------
# Query API — FastAPI + Bedrock + ChromaDB
# ---------------------------------------------------------------------------
# Override the image name in the manifest at deploy time
k8s_yaml('deploy/k8s/query-api.yaml')
k8s_resource(
    'query-api',
    port_forwards=['8080:8000'],
    resource_deps=['chromadb', 'sops-decrypt-secrets'],
    labels=['services'],
)

# ---------------------------------------------------------------------------
# Frontend — Streamlit
# ---------------------------------------------------------------------------
k8s_yaml('deploy/k8s/frontend.yaml')
k8s_resource(
    'frontend',
    port_forwards=['8501:8501'],
    resource_deps=['query-api'],
    labels=['services'],
)

# ---------------------------------------------------------------------------
# Cloudflare Tunnel — only if ENABLE_TUNNEL env is set
# ---------------------------------------------------------------------------
if os.environ.get('ENABLE_TUNNEL', '') == '1':
    k8s_yaml('deploy/k8s/cloudflared.yaml')
    k8s_resource(
        'cloudflared',
        resource_deps=['frontend', 'sops-decrypt-secrets'],
        labels=['networking'],
    )

# ---------------------------------------------------------------------------
# Argo CronWorkflow — the ingestion pipeline
# ---------------------------------------------------------------------------
k8s_yaml('deploy/argo/ingestion-workflow.yaml')
k8s_resource(
    'ancap-ingestion',
    resource_deps=['argo-workflows', 'chromadb', 'sops-decrypt-secrets'],
    labels=['argo'],
)

# ---------------------------------------------------------------------------
# Manual trigger buttons for Tilt UI
# ---------------------------------------------------------------------------
local_resource(
    'trigger-ingestion',
    cmd='argo submit -n ancap deploy/argo/ingestion-workflow.yaml --from=cronwf/ancap-ingestion',
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL,
    resource_deps=['argo-workflows'],
    labels=['argo'],
)

local_resource(
    'run-embedder',
    cmd=' '.join([
        'kubectl run ancap-embed-manual --rm -it --restart=Never -n ancap',
        '--image=ancap-scraper-embedder',
        '--env=CHROMA_HOST=chromadb',
        '--env=CHROMA_PORT=8000',
        '--overrides=\'{"spec":{"containers":[{"name":"ancap-embed-manual","image":"ancap-scraper-embedder","envFrom":[{"configMapRef":{"name":"ancap-config"}},{"secretRef":{"name":"aws-credentials"}}],"volumeMounts":[{"name":"pdfs","mountPath":"/data/pdfs"}]}],"volumes":[{"name":"pdfs","persistentVolumeClaim":{"claimName":"ancap-pdfs"}}]}}\'',
    ]),
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL,
    resource_deps=['chromadb'],
    labels=['argo'],
)

# ---------------------------------------------------------------------------
# Tilt settings
# ---------------------------------------------------------------------------
update_settings(max_parallel_updates=3, k8s_upsert_timeout_secs=120)
