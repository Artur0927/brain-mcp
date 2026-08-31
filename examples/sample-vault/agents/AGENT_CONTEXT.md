# Agent Context

> Single entry point for AI agents working with this knowledge vault.

## Live Status

| Area | Status |
|------|--------|
| Sample project | Ready for indexing |
| Tasks | See `tasks/REGISTRY.md` |

## Boot Protocol

1. `brain_search "<your task keywords>"`
2. `brain_batch_read(["agents/AGENT_CONTEXT.md", "tasks/REGISTRY.md"])`
3. Read 1–2 more files based on routing below
4. Use `brain_grep` for exact terms (error codes, filenames, IPs)

## Task Routing

| Task type | Read first |
|-----------|------------|
| General dev | `knowledge/infra/AGENT_BOOT.md` |
| After completing work | `knowledge/infra/POST_TASK_REPORT.md` |
| Lessons / gotchas | `knowledge/agent-lessons/INDEX.md` |

## Updates

Agents should append a one-line status here after verified task completion.
