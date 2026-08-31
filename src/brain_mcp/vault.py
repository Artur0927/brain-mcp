"""Vault path safety and file helpers."""
import os
from pathlib import Path

from . import config


def safe_path(relative: str) -> str:
    vault = os.path.abspath(config.VAULT)
    full = os.path.normpath(os.path.join(vault, relative))
    if not (full == vault or full.startswith(vault + os.sep)):
        raise ValueError("path escapes vault")
    return full


def read_file(relative: str, max_chars: int) -> str:
    return Path(safe_path(relative)).read_text(encoding="utf-8", errors="ignore")[:max_chars]
