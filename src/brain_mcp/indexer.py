"""Delete + re-upsert a single markdown file's chunks."""
import os
import uuid
from pathlib import Path

from qdrant_client import models

from . import config
from .chunking import chunks
from .embed_client import embed
from .qdrant_client import get_client


def reindex_file(file_path: str) -> int:
    vault = os.path.abspath(config.VAULT)
    rel = os.path.relpath(file_path, vault)
    client = get_client()

    client.delete(
        config.COLLECTION,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="path",
                        match=models.MatchValue(value=rel),
                    )
                ]
            )
        ),
    )

    try:
        text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0

    parts = chunks(text)
    if not parts:
        return 0

    dense_vectors = embed(parts, "dense")["dense"]
    sparse_vectors = embed(parts, "sparse")["sparse"]
    mtime = int(os.path.getmtime(file_path))
    title = Path(file_path).stem
    points: list[models.PointStruct] = []

    for index, (part, dense_vec, sparse_vec) in enumerate(
        zip(parts, dense_vectors, sparse_vectors)
    ):
        points.append(
            models.PointStruct(
                id=str(uuid.uuid5(config.POINT_NAMESPACE, f"{rel}:{index}")),
                vector={
                    "dense": dense_vec,
                    "sparse": models.SparseVector(
                        indices=sparse_vec["indices"],
                        values=sparse_vec["values"],
                    ),
                },
                payload={
                    "path": rel,
                    "chunk": index,
                    "title": title,
                    "mtime": mtime,
                    "text": part,
                },
            )
        )

    client.upsert(config.COLLECTION, points)
    return len(points)
