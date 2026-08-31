#!/usr/bin/env bash
# Brain MCP — one-command deploy (local dev or VPS server).
#
# Usage:
#   bash scripts/deploy.sh                    # local: venv + docker + sample vault + index
#   bash scripts/deploy.sh --vault /path/to/md  # use existing markdown vault
#   bash scripts/deploy.sh --server             # VPS: install to /opt/brain-mcp + systemd
#   bash scripts/deploy.sh --help
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODE="local"
VAULT_PATH=""
SKIP_INDEX=0
SKIP_DOCKER=0
INSTALL_PREFIX="/opt/brain-mcp"
DATA_DIR="/data"

log()  { printf '\033[1;34m[brain]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[brain]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[brain]\033[0m %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Brain MCP deploy script

  bash scripts/deploy.sh [options]

Options:
  --local          Local development setup (default)
  --server         VPS/server setup (/opt/brain-mcp + systemd)
  --vault PATH     Markdown vault directory (default: ./vault from sample)
  --skip-index     Skip initial Qdrant indexing
  --skip-docker    Skip docker compose (if Qdrant/embed run elsewhere)
  --help           Show this help

Examples:
  bash scripts/deploy.sh
  bash scripts/deploy.sh --vault ~/my-knowledge-base
  sudo bash scripts/deploy.sh --server --vault /data/vault
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --local)       MODE="local"; shift ;;
    --server)      MODE="server"; shift ;;
    --vault)       VAULT_PATH="${2:?--vault requires path}"; shift 2 ;;
    --skip-index)  SKIP_INDEX=1; shift ;;
    --skip-docker) SKIP_DOCKER=1; shift ;;
    --help|-h)     usage; exit 0 ;;
    *)             die "Unknown option: $1 (try --help)" ;;
  esac
done

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

check_prereqs() {
  log "Checking prerequisites..."
  need_cmd python3
  need_cmd curl
  need_cmd rg

  PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
  PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
  if [[ "$PY_MAJOR" -lt 3 ]] || { [[ "$PY_MAJOR" -eq 3 ]] && [[ "$PY_MINOR" -lt 11 ]]; }; then
    die "Python 3.11+ required (found $(python3 --version))"
  fi

  if [[ "$SKIP_DOCKER" -eq 0 ]]; then
    need_cmd docker
    docker compose version >/dev/null 2>&1 || die "docker compose v2 required"
  fi
}

setup_venv() {
  local target="$1"
  log "Installing Python package into venv..."
  if [[ ! -d "$target/.venv" ]]; then
    python3 -m venv "$target/.venv"
  fi
  # shellcheck disable=SC1091
  source "$target/.venv/bin/activate"
  pip install -q --upgrade pip
  pip install -q -e "$ROOT"
}

setup_vault() {
  if [[ -n "$VAULT_PATH" ]]; then
    VAULT_PATH="$(cd "$VAULT_PATH" && pwd)"
    [[ -d "$VAULT_PATH" ]] || die "Vault not found: $VAULT_PATH"
    log "Using vault: $VAULT_PATH"
    return
  fi

  if [[ "$MODE" == "server" ]]; then
    VAULT_PATH="$DATA_DIR/vault"
    mkdir -p "$VAULT_PATH"
    if [[ -z "$(find "$VAULT_PATH" -name '*.md' -print -quit)" ]]; then
      cp -r "$ROOT/examples/sample-vault/." "$VAULT_PATH/"
      log "Initialized $VAULT_PATH from sample vault"
    fi
  else
    VAULT_PATH="$ROOT/vault"
    if [[ ! -d "$VAULT_PATH" ]]; then
      cp -r "$ROOT/examples/sample-vault" "$VAULT_PATH"
      log "Created ./vault from sample"
    else
      log "Using existing ./vault"
    fi
  fi
}

start_docker() {
  [[ "$SKIP_DOCKER" -eq 1 ]] && return 0
  local compose_dir="$ROOT"
  [[ "$MODE" == "server" ]] && compose_dir="$INSTALL_PREFIX"
  log "Starting Qdrant + embed service (docker compose)..."
  (cd "$compose_dir" && docker compose up -d --build qdrant embed)

  log "Waiting for embed service (first run downloads models, ~1-3 min)..."
  local ok=0
  for _ in $(seq 1 90); do
    if curl -sf http://127.0.0.1:8091/ >/dev/null 2>&1; then
      ok=1
      break
    fi
    sleep 2
  done
  [[ "$ok" -eq 1 ]] || die "Embed service did not start on :8091"

  if ! curl -sf http://127.0.0.1:6333/ >/dev/null 2>&1; then
    warn "Qdrant health check on :6333 failed — continuing anyway"
  else
    log "Qdrant ready on :6333"
  fi
  log "Embed service ready on :8091"
}

run_index() {
  [[ "$SKIP_INDEX" -eq 1 ]] && return 0
  log "Indexing vault into Qdrant..."
  export BRAIN_VAULT="$VAULT_PATH"
  export BRAIN_QDRANT_HOST="${BRAIN_QDRANT_HOST:-127.0.0.1}"
  export BRAIN_EMBED_URL="${BRAIN_EMBED_URL:-http://127.0.0.1:8091/embed}"
  brain-index
  brain-stats
}

write_mcp_config() {
  local python_bin="$1"
  local cfg_path="$2"
  mkdir -p "$(dirname "$cfg_path")"
  cat >"$cfg_path" <<EOF
{
  "mcpServers": {
    "brain-search": {
      "type": "stdio",
      "command": "${python_bin}",
      "env": {
        "BRAIN_VAULT": "${VAULT_PATH}",
        "BRAIN_QDRANT_HOST": "127.0.0.1",
        "BRAIN_EMBED_URL": "http://127.0.0.1:8091/embed"
      }
    }
  }
}
EOF
  log "Wrote MCP config: $cfg_path"
}

install_systemd() {
  [[ "$MODE" != "server" ]] && return 0
  need_cmd systemctl
  [[ "$(id -u)" -eq 0 ]] || die "--server requires root (sudo bash scripts/deploy.sh --server)"

  log "Installing to $INSTALL_PREFIX ..."
  mkdir -p "$INSTALL_PREFIX" "$DATA_DIR/.brain" "$DATA_DIR/agentlogs"
  rsync -a --exclude '.venv' --exclude '.git' --exclude 'vault' --exclude 'agentlogs' \
    "$ROOT/" "$INSTALL_PREFIX/"

  setup_venv "$INSTALL_PREFIX"

  install_unit() {
    local name="$1"
    sed \
      -e "s|/opt/brain-mcp|$INSTALL_PREFIX|g" \
      -e "s|/data/vault|$VAULT_PATH|g" \
      -e "s|/data/agentlogs|$DATA_DIR/agentlogs|g" \
      -e "s|/data/.brain|$DATA_DIR/.brain|g" \
      "$INSTALL_PREFIX/deploy/systemd/${name}" \
      >"/etc/systemd/system/${name}"
  }

  log "Installing systemd units (reindex timer + dashboard)..."
  install_unit "brain-reindex.service"
  install_unit "brain-reindex.timer"
  install_unit "brain-dashboard.service"

  if [[ "$SKIP_DOCKER" -eq 1 ]]; then
    install_unit "brain-embed.service"
    systemctl enable --now brain-embed.service
  else
    log "Embed via Docker — skipping brain-embed.service"
  fi

  systemctl daemon-reload
  systemctl enable --now brain-reindex.timer
  systemctl enable --now brain-dashboard.service 2>/dev/null || warn "Dashboard optional"

  log "Systemd units installed"
}

deploy_local() {
  setup_venv "$ROOT"
  setup_vault
  start_docker
  run_index

  local py="$ROOT/.venv/bin/brain-mcp"
  write_mcp_config "$py" "$ROOT/examples/mcp/mcp.generated.json"

  cat <<EOF

Brain MCP ready (local)

  Vault:     $VAULT_PATH
  Qdrant:    http://127.0.0.1:6333
  Embed:     http://127.0.0.1:8091
  MCP:       $py

  1. Merge examples/mcp/mcp.generated.json into the MCP client config
  2. Reload the MCP server
  3. Call brain_stats

  docs/setup.md
EOF
}

deploy_server() {
  [[ "$(id -u)" -eq 0 ]] || die "--server requires: sudo bash scripts/deploy.sh --server"
  setup_vault
  install_systemd
  start_docker
  # shellcheck disable=SC1091
  source "$INSTALL_PREFIX/.venv/bin/activate"
  run_index

  local py="$INSTALL_PREFIX/.venv/bin/brain-mcp"
  write_mcp_config "$py" "$INSTALL_PREFIX/examples/mcp/mcp.generated.json"

  cat <<EOF

Brain MCP ready (server)

  Prefix:    $INSTALL_PREFIX
  Vault:     $VAULT_PATH
  Dashboard: http://127.0.0.1:8090

  Remote stdio: $INSTALL_PREFIX/scripts/mcp-launcher.sh
  BRAIN_SSH_HOST=user@host BRAIN_VAULT=$VAULT_PATH

EOF
}

main() {
  log "Brain MCP deploy (mode=$MODE)"
  check_prereqs
  if [[ "$MODE" == "server" ]]; then
    deploy_server
  else
    deploy_local
  fi
}

main
