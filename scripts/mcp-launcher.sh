#!/usr/bin/env bash
# SSH stdio launcher with ControlMaster multiplexing.
# Env: BRAIN_SSH_HOST (required), BRAIN_SSH_KEY, BRAIN_VAULT, BRAIN_REMOTE_PYTHON.

set -euo pipefail

SSH_KEY="${BRAIN_SSH_KEY:-$HOME/.ssh/id_ed25519}"
BRAIN_HOST="${BRAIN_SSH_HOST:?Set BRAIN_SSH_HOST (e.g. user@brain-server)}"
CM_SOCK="${BRAIN_CM_SOCK:-$HOME/.ssh/cm-brain.sock}"
REMOTE_PYTHON="${BRAIN_REMOTE_PYTHON:-/opt/brain-mcp/.venv/bin/brain-mcp}"
REMOTE_VAULT="${BRAIN_VAULT:-/data/vault}"

SSH_OPTS=(
  -i "$SSH_KEY"
  -o BatchMode=yes
  -o StrictHostKeyChecking=accept-new
  -o ControlMaster=auto
  -o "ControlPath=$CM_SOCK"
  -o ControlPersist=1h
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=4
  -o ConnectTimeout=12
)

if ! ssh "${SSH_OPTS[@]}" -O check "$BRAIN_HOST" &>/dev/null; then
  ssh "${SSH_OPTS[@]}" -fN "$BRAIN_HOST" 2>/dev/null || true
fi

exec ssh "${SSH_OPTS[@]}" "$BRAIN_HOST" \
  env BRAIN_VAULT="$REMOTE_VAULT" "$REMOTE_PYTHON"
