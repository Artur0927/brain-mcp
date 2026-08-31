# MCP client setup

## Deploy, then wire stdio

```bash
git clone https://github.com/Artur0927/brain-mcp.git
cd brain-mcp
bash scripts/deploy.sh
```

Generated config: `examples/mcp/mcp.generated.json`. Merge the `brain-search` entry into the client's MCP config file.

Verify:

```bash
export BRAIN_VAULT="$(pwd)/vault"
brain-stats
```

Expect `points > 0` and `embed_service: UP`.

## Config fragment

```json
{
  "mcpServers": {
    "brain-search": {
      "type": "stdio",
      "command": "/absolute/path/to/brain-mcp/.venv/bin/brain-mcp",
      "env": {
        "BRAIN_VAULT": "/absolute/path/to/brain-mcp/vault",
        "BRAIN_QDRANT_HOST": "127.0.0.1",
        "BRAIN_EMBED_URL": "http://127.0.0.1:8091/embed"
      }
    }
  }
}
```

Without `deploy.sh`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp -r examples/sample-vault vault
docker compose up -d qdrant embed
export BRAIN_VAULT=./vault
brain-index
```

## Remote (SSH stdio)

MCP process runs on the server. Client config:

```json
{
  "mcpServers": {
    "brain-search": {
      "type": "stdio",
      "command": "/opt/brain-mcp/scripts/mcp-launcher.sh",
      "env": {
        "BRAIN_SSH_KEY": "~/.ssh/id_ed25519",
        "BRAIN_SSH_HOST": "user@host",
        "BRAIN_VAULT": "/data/vault"
      }
    }
  }
}
```

`mcp-launcher.sh` uses SSH `ControlMaster` / `ControlPersist`.

## Failures

| Symptom | Action |
|---------|--------|
| Stale tool schema | restart the MCP connection |
| `embed_service: DOWN` | `docker compose up -d embed` |
| `no results` | `brain-index` |
| `rg: command not found` | install ripgrep |
