# Post-Task Report

Agents write a structured report **after** task completion and DoD verification — without being asked.

## When to Write

Both conditions must be true:

1. Task work is complete
2. DoD / tests passed (command + actual result)

If blocked — log immediately with `brain_log` type=`blocker`.

## Minimum Package

1. `brain_log <agent> "<short milestone>" type=milestone`
2. Update header of `agents/AGENT_CONTEXT.md` (1–3 lines of live fact)
3. If production state changed — write status slice under `knowledge/status/YYYY-MM-DD-slug.md`
4. Update task file + `tasks/REGISTRY.md` when closing

## Report Template

```
What: <one line — what is now live or broken>
Where: <path / service / component>
DoD checks: <command → result> (2–5 items)
Not touched: <neighbors left unchanged>
Status slice: knowledge/status/<file> · task: tasks/...
Blocker (if any): <what is needed from human>
```

## Good vs Bad

**Good:** `Added health check endpoint /health → curl 200. Updated AGENT_CONTEXT. Task moved to done.`

**Bad:** `Done` / `Fixed` / `Deployed` — without verification evidence.

## MCP Tools

- `brain_log` — daily diary
- `brain_write` / `brain_append` — status files, AGENT_CONTEXT, REGISTRY
- `brain_lesson` — reusable gotchas for future agents
