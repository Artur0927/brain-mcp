#!/usr/bin/env python3
"""Rebuild knowledge/agent-lessons/INDEX.md grouped by frontmatter category."""
import glob
import os
import re

from . import config
from .indexer import reindex_file


def frontmatter(path: str) -> dict[str, str]:
    text = open(path, encoding="utf-8", errors="ignore").read()
    match = re.match(r"^---\n(.*?)\n---", text, re.S)
    data: dict[str, str] = {}
    if match:
        for line in match.group(1).splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip()
    return data


def main() -> None:
    lessons_dir = os.path.join(config.VAULT, "knowledge", "agent-lessons")
    os.makedirs(lessons_dir, exist_ok=True)

    files = [
        path
        for path in sorted(glob.glob(f"{lessons_dir}/*.md"))
        if os.path.basename(path) != "INDEX.md"
    ]

    by_category: dict[str, list[tuple[str, dict[str, str]]]] = {}
    for path in files:
        meta = frontmatter(path)
        by_category.setdefault(meta.get("category", "other"), []).append((path, meta))

    lines = [
        "# Agent Lessons — Index",
        "",
        f"> Auto-generated. Total: {len(files)}.",
        "",
    ]

    for category in sorted(by_category):
        lines.append(f"## {category} ({len(by_category[category])})")
        for path, meta in sorted(
            by_category[category], key=lambda item: item[1].get("date", ""), reverse=True
        ):
            name = os.path.basename(path)[:-3]
            lines.append(
                f"- `{meta.get('date', '')}` **{meta.get('agent', '?')}** — {name}"
            )
        lines.append("")

    index_path = os.path.join(lessons_dir, "INDEX.md")
    with open(index_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    reindex_file(index_path)
    print(f"INDEX.md rebuilt: {len(files)} lessons, {len(by_category)} categories")


if __name__ == "__main__":
    main()
