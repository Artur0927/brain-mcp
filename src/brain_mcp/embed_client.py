"""HTTP client for the shared embedding service."""
import json
import time
import urllib.request

from . import config


def embed(texts: list[str], kind: str = "dense", retries: int = 2) -> dict:
    last_err: Exception | None = None
    payload = json.dumps({"texts": texts, "kind": kind}).encode()
    headers = {"Content-Type": "application/json"}

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(config.EMBED_URL, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as response:
                return json.loads(response.read().decode())
        except Exception as exc:
            last_err = exc
            if attempt == retries:
                raise
            time.sleep(0.5 * (attempt + 1))

    if last_err:
        raise last_err
    raise RuntimeError("embed failed without error")
