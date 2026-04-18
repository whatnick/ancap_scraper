# SOPS Secrets Management
#
# This directory holds SOPS-encrypted secret manifests that are safe to commit
# to Git. The Tiltfile automatically decrypts them at deploy time.
#
# ## Prerequisites
#
# ```bash
# # Install sops and age
# brew install sops age          # macOS
# # or
# apt install sops age           # Debian/Ubuntu
# # or
# nix-env -i sops age            # Nix
# ```
#
# ## Initial Setup (one-time)
#
# ```bash
# # 1. Generate an age keypair
# age-keygen -o deploy/sops/age-key.txt
#
# # 2. Copy the PUBLIC key from the output (starts with age1...)
# #    and paste it into .sops.yaml (replace age1REPLACE_WITH_YOUR_AGE_PUBLIC_KEY)
#
# # 3. Set the SOPS_AGE_KEY_FILE env var (add to your shell profile)
# export SOPS_AGE_KEY_FILE=$PWD/deploy/sops/age-key.txt
#
# # 4. Create the secrets file from the template
# cp deploy/sops/secrets.template.yaml deploy/sops/secrets.dec.yaml
# # Edit deploy/sops/secrets.dec.yaml with your real credentials
#
# # 5. Encrypt it
# sops --encrypt deploy/sops/secrets.dec.yaml > deploy/sops/secrets.enc.yaml
#
# # 6. Remove the plaintext
# rm deploy/sops/secrets.dec.yaml
# ```
#
# ## Day-to-day Usage
#
# ```bash
# # Edit secrets (opens in $EDITOR, re-encrypts on save)
# sops deploy/sops/secrets.enc.yaml
#
# # Decrypt to stdout (for debugging)
# sops --decrypt deploy/sops/secrets.enc.yaml
#
# # Tilt handles decryption automatically — just run:
# tilt up
# ```
#
# ## Team Sharing
#
# Share the `age-key.txt` file securely (1Password, Vault, etc.).
# Each team member sets `SOPS_AGE_KEY_FILE` to their local copy.
# The encrypted `secrets.enc.yaml` is safe to commit and push.
#
# ## Files
#
# | File | Git? | Purpose |
# |---|---|---|
# | `secrets.enc.yaml` | YES | Encrypted secrets — commit this |
# | `secrets.template.yaml` | YES | Template showing required fields |
# | `age-key.txt` | **NO** | Private key — NEVER commit |
# | `secrets.dec.yaml` | **NO** | Plaintext — NEVER commit |
