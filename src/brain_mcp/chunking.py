"""Markdown chunking for vault indexing."""
import re

from . import config


def chunks(text: str) -> list[str]:
    out: list[str] = []
    for block in re.split(r"(?m)^(?=#{1,6}\s)", text):
        block = block.strip()
        if not block:
            continue
        if len(block) <= config.MAX_CHUNK:
            out.append(block)
            continue
        current = ""
        for para in block.split("\n\n"):
            if len(current) + len(para) > config.MAX_CHUNK and current:
                out.append(current.strip())
                current = ""
            current += para + "\n\n"
        if current.strip():
            out.append(current.strip())
    return out
