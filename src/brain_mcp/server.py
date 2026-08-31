#!/usr/bin/env python3
"""MCP stdio server — hybrid search, vault I/O, agent workflow tools."""
import fnmatch
import json
import os
import shutil
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from qdrant_client import models

from . import config
from .embed_client import embed
from .indexer import reindex_file
from .qdrant_client import get_client
from .vault import read_file, safe_path

mcp = FastMCP("brain-search")


@mcp.tool()
def brain_grep(pattern: str, limit: int = 40) -> str:
    """Exact/regex search via ripgrep.  Returns file:line:match."""
    try:
        result = subprocess.run(
            ["rg", "-n", "--max-count", "3", "-i", "--", pattern, config.VAULT],
            capture_output=True,
            text=True,
            timeout=25,
        )
        vault = os.path.abspath(config.VAULT)
        lines = [line.replace(vault + os.sep, "") for line in result.stdout.splitlines()][
            :limit
        ]
        return "\n".join(lines) if lines else "no matches"
    except Exception as exc:
        return f"error: {exc}"


@mcp.tool()
def brain_search(query: str, limit: int = 8, path_prefix: str = "") -> str:
    """Dense + BM25 prefetch, RRF fusion.  Optional path_prefix narrows scope."""
    try:
        dense_vec = embed([query], "dense")["dense"][0]
        sparse_vec = embed([query], "sparse")["sparse"][0]
        filter_cond = None
        if path_prefix:
            filter_cond = models.Filter(
                must=[
                    models.FieldCondition(
                        key="path",
                        match=models.MatchText(text=path_prefix),
                    )
                ]
            )

        points = get_client().query_points(
            config.COLLECTION,
            prefetch=[
                models.Prefetch(query=dense_vec, using="dense", limit=limit * 3),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=sparse_vec["indices"],
                        values=sparse_vec["values"],
                    ),
                    using="sparse",
                    limit=limit * 3,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            query_filter=filter_cond,
            with_payload=True,
        ).points

        blocks = [
            f"[{point.score:.3f}] {point.payload['path']} (chunk {point.payload['chunk']})\n"
            f"{point.payload['text'][:900]}"
            for point in points
        ]
        return "\n\n---\n\n".join(blocks) if blocks else "no results"
    except Exception as exc:
        return f"error: search failed ({exc})"


@mcp.tool()
def brain_read(path: str, max_chars: int = 16000) -> str:
    """Read a vault file by relative path."""
    try:
        return read_file(path, max_chars)
    except Exception as exc:
        return f"error: {exc}"


@mcp.tool()
def brain_batch_read(paths: list[str], max_chars: int = 12000) -> str:
    """Read up to 5 vault files in one call."""
    results: list[str] = []
    for path in (paths or [])[:5]:
        try:
            text = read_file(path, max_chars)
            results.append(f"=== {path} ===\n{text}")
        except Exception as exc:
            results.append(f"=== {path} ===\nERROR: {exc}")
    return "\n\n".join(results) if results else "no paths given"


@mcp.tool()
def brain_list(path: str = "", depth: int = 2, pattern: str = "*.md") -> str:
    """List files in the vault with depth and pattern limits."""
    try:
        base = safe_path(path)
        if not os.path.isdir(base):
            return f"not a directory: {path or '.'}"

        vault = os.path.abspath(config.VAULT)
        entries: list[str] = []
        for root, dirs, files in os.walk(base):
            dirs[:] = [name for name in dirs if name not in config.SKIP_DIRS]
            rel_depth = root.replace(base, "").count(os.sep)
            if rel_depth >= depth:
                dirs.clear()
                continue

            rel = os.path.relpath(root, vault)
            matched = [name for name in sorted(files) if fnmatch.fnmatch(name, pattern)]
            if matched:
                entries.append(f"{rel}/ ({len(matched)} files)")
                for name in matched[:20]:
                    entries.append(f"  {name}")
                if len(matched) > 20:
                    entries.append(f"  ... and {len(matched) - 20} more")

        return "\n".join(entries[:200]) if entries else "empty"
    except Exception as exc:
        return f"error: {exc}"


@mcp.tool()
def brain_stats() -> str:
    """Collection size, disk usage, embed service health, .md count."""
    try:
        info = get_client().get_collection(config.COLLECTION)
        disk = shutil.disk_usage(config.VAULT)
        try:
            health_url = config.EMBED_URL.replace("/embed", "/")
            import urllib.request

            urllib.request.urlopen(health_url, timeout=3)
            embed_ok = "UP"
        except Exception:
            embed_ok = "DOWN"

        md_count = sum(1 for _ in Path(config.VAULT).rglob("*.md"))
        return (
            f"points: {info.points_count}, vectors: {info.indexed_vectors_count}\n"
            f"disk: {disk.used // 1024 // 1024}MB used / {disk.total // 1024 // 1024}MB total\n"
            f"embed_service: {embed_ok}\n"
            f"vault_files: {md_count}"
        )
    except Exception as exc:
        return f"error: {exc}"


@mcp.tool()
def brain_write(path: str, content: str) -> str:
    """Create or overwrite a vault file. Auto-reindexes."""
    try:
        full = safe_path(path)
        os.makedirs(os.path.dirname(full) or config.VAULT, exist_ok=True)
        Path(full).write_text(content, encoding="utf-8")
        count = reindex_file(full)
        return f"wrote {path} ({len(content)} bytes), reindexed {count} chunks"
    except Exception as exc:
        return f"error: write/reindex failed ({exc})"


@mcp.tool()
def brain_append(path: str, content: str) -> str:
    """Append to a vault file. Auto-reindexes."""
    try:
        full = safe_path(path)
        os.makedirs(os.path.dirname(full) or config.VAULT, exist_ok=True)
        with open(full, "a", encoding="utf-8") as handle:
            handle.write(content if content.endswith("\n") else content + "\n")
        count = reindex_file(full)
        return f"appended to {path}, reindexed {count} chunks"
    except Exception as exc:
        return f"error: append/reindex failed ({exc})"


@mcp.tool()
def brain_log(agent: str, message: str, type: str = "note") -> str:
    """Timestamped daily log entry (YYYY-MM-DD.md). Auto-reindexes."""
    try:
        now = datetime.now()
        day = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%H:%M")
        full = safe_path(f"{day}.md")
        is_new = not os.path.exists(full)
        with open(full, "a", encoding="utf-8") as handle:
            if is_new:
                handle.write(f"# {day}\n\n")
            handle.write(f"- {timestamp} [{agent}] ({type}) {message}\n")
        count = reindex_file(full)
        return f"logged to {day}.md at {timestamp}, reindexed {count} chunks"
    except Exception as exc:
        return f"error: {exc}"


@mcp.tool()
def brain_lesson(
    agent: str,
    category: str,
    body: str,
    context: str = "",
) -> str:
    """Persist a reusable lesson under knowledge/agent-lessons/.  Auto-reindexes."""
    try:
        now = datetime.now()
        stamp = now.strftime("%Y%m%d-%H%M%S")
        date = now.strftime("%Y-%m-%d %H:%M")
        day = now.strftime("%Y-%m-%d")
        rel = f"knowledge/agent-lessons/{stamp}_{agent}_{category}.md"
        full = safe_path(rel)
        frontmatter = "\n".join(
            [
                "---",
                "type: lesson",
                f"agent: {agent}",
                f"category: {category}",
                "audience: [all]",
                f"context: {context or 'none'}",
                f"date: {date}",
                "useful_for: all",
                f"tags: [lesson, {agent}, {category}]",
                f"created: {day}",
                f"updated: {day}",
                "---",
                "",
                body,
                "",
            ]
        )
        os.makedirs(os.path.dirname(full), exist_ok=True)
        Path(full).write_text(frontmatter, encoding="utf-8")
        count = reindex_file(full)
        return f"lesson saved: {rel}, reindexed {count} chunks"
    except Exception as exc:
        return f"error: {exc}"


@mcp.tool()
def brain_task_claim(task_id: str, agent: str, ttl_hours: int = 2) -> str:
    """Atomically claim a task for parallel agent coordination."""
    lock_dir = os.path.join(config.VAULT, "tasks", ".locks")
    os.makedirs(lock_dir, exist_ok=True)
    lock_path = os.path.join(lock_dir, os.path.basename(task_id) + ".lock")
    now = time.time()

    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.write(fd, json.dumps({"agent": agent, "ts": now}).encode())
        os.close(fd)
        return f"claimed {task_id} by {agent}"
    except FileExistsError:
        try:
            current = json.loads(open(lock_path, encoding="utf-8").read())
        except Exception:
            current = {"agent": "?", "ts": 0}

        if current.get("agent") == agent:
            return f"already yours: {task_id}"

        age = now - current.get("ts", 0)
        if age > ttl_hours * 3600:
            with open(lock_path, "w", encoding="utf-8") as handle:
                handle.write(json.dumps({"agent": agent, "ts": now}))
            return f"claimed (stale-steal) {task_id} by {agent}"

        return (
            f"DENIED: {task_id} claimed by {current.get('agent')} "
            f"({int(age / 60)}m ago)"
        )


@mcp.tool()
def brain_task_release(task_id: str, agent: str) -> str:
    """Release a task claim if you own it."""
    lock_path = os.path.join(
        config.VAULT, "tasks", ".locks", os.path.basename(task_id) + ".lock"
    )
    if not os.path.exists(lock_path):
        return f"not claimed: {task_id}"

    try:
        current = json.loads(open(lock_path, encoding="utf-8").read())
    except Exception:
        current = {}

    if current.get("agent") != agent:
        return f"DENIED: owned by {current.get('agent')}"

    os.remove(lock_path)
    return f"released {task_id}"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
