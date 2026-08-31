"""Shared Qdrant client singleton."""
from qdrant_client import QdrantClient

from . import config

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            host=config.QDRANT_HOST,
            port=config.QDRANT_PORT,
            timeout=config.QDRANT_TIMEOUT,
        )
    return _client
