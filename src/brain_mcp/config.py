"""Environment-based configuration.  All knobs via env vars."""
import os
import uuid

VAULT = os.environ.get("BRAIN_VAULT", "./vault")
COLLECTION = os.environ.get("BRAIN_COLLECTION", "brain")
MAX_CHUNK = int(os.environ.get("BRAIN_MAX_CHUNK", "1500"))

EMBED_URL = os.environ.get("BRAIN_EMBED_URL", "http://127.0.0.1:8091/embed")
EMBED_PORT = int(os.environ.get("BRAIN_EMBED_PORT", "8091"))

QDRANT_HOST = os.environ.get("BRAIN_QDRANT_HOST", "127.0.0.1")
QDRANT_PORT = int(os.environ.get("BRAIN_QDRANT_PORT", "6333"))
QDRANT_TIMEOUT = int(os.environ.get("BRAIN_QDRANT_TIMEOUT", "60"))

DENSE_MODEL = os.environ.get(
    "BRAIN_DENSE_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
SPARSE_MODEL = os.environ.get("BRAIN_SPARSE_MODEL", "Qdrant/bm25")
DENSE_DIM = int(os.environ.get("BRAIN_DENSE_DIM", "384"))

POINT_NAMESPACE = uuid.UUID(
    os.environ.get("BRAIN_POINT_NAMESPACE", "b7a10000-0000-0000-0000-000000000000")
)

SKIP_DIRS = {".git", "venv", "__pycache__", ".locks", "node_modules"}
REINDEX_MARKER = os.environ.get("BRAIN_REINDEX_MARKER", ".last_reindex")

DASHBOARD_HOST = os.environ.get("BRAIN_DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_PORT = int(os.environ.get("BRAIN_DASHBOARD_PORT", "8090"))
AGENT_LOGS_DIR = os.environ.get("BRAIN_AGENT_LOGS", "./agentlogs")
