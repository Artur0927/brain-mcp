#!/usr/bin/env python3
"""Incremental reindex: re-embed files whose mtime exceeds the marker."""
import glob
import os
import sys
import time

from . import config
from .indexer import reindex_file


def main() -> None:
    marker = os.environ.get(
        "BRAIN_REINDEX_MARKER_PATH",
        os.path.join(
            os.path.dirname(os.path.abspath(config.VAULT)),
            ".brain",
            ".last_reindex",
        ),
    )

    if not os.path.exists(marker):
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write(str(time.time()))
        print("init marker (index assumed current), skip")
        return

    try:
        last = float(open(marker, encoding="utf-8").read().strip())
    except OSError:
        last = 0.0

    start = time.time()
    changed = [
        path
        for path in glob.glob(f"{config.VAULT}/**/*.md", recursive=True)
        if os.path.getmtime(path) > last
    ]

    count = 0
    for path in changed:
        try:
            reindex_file(path)
            count += 1
        except Exception as exc:
            print("ERR", path, exc)

    with open(marker, "w", encoding="utf-8") as handle:
        handle.write(str(start))
    print(f"reindexed {count}/{len(changed)} changed .md")


if __name__ == "__main__":
    if not os.path.isdir(config.VAULT):
        print(f"vault not found: {config.VAULT}", file=sys.stderr)
        sys.exit(1)
    main()
