#!/usr/bin/env python3
"""Full vault indexer — hybrid dense + sparse vectors into Qdrant."""
import glob
import os
import sys
from pathlib import Path

from qdrant_client import models
from fastembed import SparseTextEmbedding, TextEmbedding

from . import config
from .chunking import chunks
from .qdrant_client import get_client


def main() -> None:
    print("loading models (first run downloads ONNX)...", flush=True)
    dense = TextEmbedding(config.DENSE_MODEL)
    sparse = SparseTextEmbedding(config.SPARSE_MODEL)
    client = get_client()

    client.recreate_collection(
        config.COLLECTION,
        vectors_config={
            "dense": models.VectorParams(
                size=config.DENSE_DIM,
                distance=models.Distance.COSINE,
            )
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
        },
    )
    client.create_payload_index(
        config.COLLECTION,
        "path",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )

    files = sorted(glob.glob(f"{config.VAULT}/**/*.md", recursive=True))
    metas: list[dict] = []
    texts: list[str] = []

    for file_path in files:
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        rel = os.path.relpath(file_path, config.VAULT)
        mtime = int(os.path.getmtime(file_path))
        title = Path(file_path).stem

        for index, part in enumerate(chunks(content)):
            metas.append(
                {
                    "path": rel,
                    "chunk": index,
                    "title": title,
                    "mtime": mtime,
                    "text": part,
                }
            )
            texts.append(part)

    print(f"{len(files)} files -> {len(texts)} chunks. embedding+upserting...", flush=True)

    dense_gen = dense.embed(texts, batch_size=32)
    sparse_gen = sparse.embed(texts, batch_size=32)
    batch: list[models.PointStruct] = []
    point_id = 0
    total = 0
    batch_size = 256

    for meta, dense_vec, sparse_vec in zip(metas, dense_gen, sparse_gen):
        batch.append(
            models.PointStruct(
                id=point_id,
                vector={
                    "dense": dense_vec.tolist(),
                    "sparse": models.SparseVector(
                        indices=sparse_vec.indices.tolist(),
                        values=sparse_vec.values.tolist(),
                    ),
                },
                payload=meta,
            )
        )
        point_id += 1

        if len(batch) >= batch_size:
            client.upsert(config.COLLECTION, batch)
            total += len(batch)
            batch = []
            print(f"  upserted {total}", flush=True)

    if batch:
        client.upsert(config.COLLECTION, batch)
        total += len(batch)

    print(f"DONE indexed {total} chunks from {len(files)} files", flush=True)


if __name__ == "__main__":
    if not os.path.isdir(config.VAULT):
        print(f"vault not found: {config.VAULT}", file=sys.stderr)
        sys.exit(1)
    main()
