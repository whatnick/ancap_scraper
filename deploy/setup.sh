#!/usr/bin/env bash
# Bootstrap script for local ANCAP development environment
# Usage: ./deploy/setup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SOPS_DIR="$SCRIPT_DIR/sops"
AGE_KEY="$SOPS_DIR/age-key.txt"

echo "=== ANCAP Scraper — Local K8s Setup ==="
echo ""

# ---- Check prerequisites ----
check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        echo "ERROR: $1 is not installed. $2"
        exit 1
    fi
}

check_cmd kubectl "Install: https://kubernetes.io/docs/tasks/tools/"
check_cmd tilt    "Install: brew install tilt-dev/tap/tilt"
check_cmd sops    "Install: brew install sops"
check_cmd age     "Install: brew install age"
check_cmd helm    "Install: brew install helm"

echo "[OK] All prerequisites installed"
echo ""

# ---- Check K8s context ----
CONTEXT=$(kubectl config current-context 2>/dev/null || echo "")
if [[ -z "$CONTEXT" ]]; then
    echo "ERROR: No K8s context found. Start a local cluster first:"
    echo "  kind create cluster --name ancap"
    echo "  minikube start"
    echo "  k3d cluster create ancap"
    exit 1
fi
echo "[OK] K8s context: $CONTEXT"
echo ""

# ---- Generate age key if not present ----
if [[ ! -f "$AGE_KEY" ]]; then
    echo "Generating age keypair for SOPS..."
    mkdir -p "$SOPS_DIR"
    age-keygen -o "$AGE_KEY" 2>&1
    AGE_PUB=$(grep "public key:" "$AGE_KEY" | awk '{print $NF}')

    echo ""
    echo ">>> Your age public key: $AGE_PUB"
    echo ""

    # Auto-update .sops.yaml with the generated public key
    if [[ -f "$PROJECT_DIR/.sops.yaml" ]]; then
        sed -i "s|age1REPLACE_WITH_YOUR_AGE_PUBLIC_KEY|$AGE_PUB|g" "$PROJECT_DIR/.sops.yaml"
        echo "[OK] Updated .sops.yaml with your public key"
    fi
else
    AGE_PUB=$(grep "public key:" "$AGE_KEY" | awk '{print $NF}')
    echo "[OK] age key exists: $AGE_PUB"
fi
echo ""

# ---- Export SOPS env var ----
export SOPS_AGE_KEY_FILE="$AGE_KEY"

# ---- Create encrypted secrets if not done ----
ENC_FILE="$SOPS_DIR/secrets.enc.yaml"
TEMPLATE="$SOPS_DIR/secrets.template.yaml"

# Check if the enc file is still the placeholder
if grep -q "REPLACE_ME" "$ENC_FILE" 2>/dev/null; then
    echo "Secrets not yet configured. Let's set them up."
    echo ""

    DEC_FILE="$SOPS_DIR/secrets.dec.yaml"
    cp "$TEMPLATE" "$DEC_FILE"

    read -rp "AWS_ACCESS_KEY_ID: " AWS_KEY
    read -rsp "AWS_SECRET_ACCESS_KEY: " AWS_SECRET
    echo ""
    read -rp "AWS_DEFAULT_REGION [us-east-1]: " AWS_REGION
    AWS_REGION=${AWS_REGION:-us-east-1}
    read -rp "Cloudflare Tunnel Token (or press Enter to skip): " CF_TOKEN
    CF_TOKEN=${CF_TOKEN:-SKIP}

    sed -i "s|YOUR_AWS_ACCESS_KEY_ID|$AWS_KEY|g" "$DEC_FILE"
    sed -i "s|YOUR_AWS_SECRET_ACCESS_KEY|$AWS_SECRET|g" "$DEC_FILE"
    sed -i "s|us-east-1|$AWS_REGION|g" "$DEC_FILE"
    sed -i "s|YOUR_CLOUDFLARE_TUNNEL_TOKEN|$CF_TOKEN|g" "$DEC_FILE"

    sops --encrypt "$DEC_FILE" > "$ENC_FILE"
    rm -f "$DEC_FILE"
    echo ""
    echo "[OK] Secrets encrypted to $ENC_FILE"
else
    echo "[OK] Encrypted secrets already configured"
fi
echo ""

# ---- Verify decryption works ----
echo "Verifying SOPS decryption..."
DECRYPTED_DIR="$SCRIPT_DIR/k8s"
sops --decrypt "$ENC_FILE" > "$DECRYPTED_DIR/secrets.decrypted.yaml"
echo "[OK] Decryption successful"
rm -f "$DECRYPTED_DIR/secrets.decrypted.yaml"
echo ""

# ---- Summary ----
echo "=== Setup Complete ==="
echo ""
echo "Add this to your shell profile (~/.bashrc, ~/.zshrc):"
echo "  export SOPS_AGE_KEY_FILE=$AGE_KEY"
echo ""
echo "Start the dev environment:"
echo "  cd $PROJECT_DIR"
echo "  tilt up"
echo ""
echo "Optional — enable Cloudflare Tunnel:"
echo "  ENABLE_TUNNEL=1 tilt up"
echo ""
echo "Trigger ingestion manually (after tilt up):"
echo "  Press the 'trigger-ingestion' button in the Tilt UI"
echo "  or: argo submit -n ancap deploy/argo/ingestion-workflow.yaml"
