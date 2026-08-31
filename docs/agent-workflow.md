# Agent protocol

Convention for using Brain MCP as a shared knowledge layer. Not required for search/read/write.

## Session start

1. `brain_search "<task keywords>"`
2. `brain_batch_read(["agents/AGENT_CONTEXT.md", "tasks/REGISTRY.md"])`
3. `brain_read` one or two routed files
4. `brain_grep` for exact identifiers (paths, error codes)

## During work

| Tool | When |
|------|------|
| `brain_log` | milestone |
| `brain_lesson` | non-trivial failure + fix (`gotcha`, `workaround`, `tip`, `win`, `error`) |
| `brain_task_claim` | before taking a task (TTL 2h; stale locks stealable) |

## After verified completion

1. `brain_log <agent> "<summary>" type=milestone`
2. Update `agents/AGENT_CONTEXT.md`
3. Status note under `knowledge/status/YYYY-MM-DD-slug.md` if live state changed
4. Move task file; update `tasks/REGISTRY.md`

Template: `examples/sample-vault/knowledge/infra/POST_TASK_REPORT.md`.

## Vault layout

```
vault/
├── agents/AGENT_CONTEXT.md
├── tasks/{REGISTRY.md,active,done,backlog,blocked,.locks}
├── knowledge/{infra,agent-lessons,status}
└── YYYY-MM-DD.md
```
