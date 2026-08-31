# Agent Boot — Brain MCP

Every agent session starts here.

## Boot Sequence (4 steps)

1. **`brain_search "<task keywords>"`** — semantic + keyword hybrid search
2. **`brain_batch_read(["agents/AGENT_CONTEXT.md", "tasks/REGISTRY.md"])`** — live context + tasks
3. **Route** — read 1–2 more files based on task type (see AGENT_CONTEXT routing table)
4. **`brain_grep "<exact term>"`** — for domains, IPs, error codes, filenames

## Optional

- `brain_stats` — check vault health before heavy sessions
- `brain_list path="knowledge/" depth=2` — explore vault structure

## Tools Overview

| Tool | Purpose |
|------|---------|
| `brain_search` | Hybrid RAG search (meaning + keywords) |
| `brain_grep` | Exact ripgrep search |
| `brain_read` / `brain_batch_read` | Read vault files |
| `brain_write` / `brain_append` | Write files (auto-reindex) |
| `brain_log` | Daily milestone log |
| `brain_lesson` | Reusable gotcha/workaround |
| `brain_task_claim` / `brain_task_release` | Parallel agent coordination |
| `brain_list` / `brain_stats` | Explore and health-check |

## Rules

- Search before reading random files
- Do not claim "done" without verification
- After DoD — write report (see POST_TASK_REPORT.md)
