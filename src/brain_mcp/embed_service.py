#!/usr/bin/env python3
"""Shared embedding HTTP service.  Loads dense + sparse models once."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from fastembed import SparseTextEmbedding, TextEmbedding

from . import config

print("embed-service: loading models...", flush=True)
_dense = TextEmbedding(config.DENSE_MODEL)
_sparse = SparseTextEmbedding(config.SPARSE_MODEL)
list(_dense.embed(["warm"]))
list(_sparse.embed(["warm"]))
print(f"embed-service: ready on 127.0.0.1:{config.EMBED_PORT}", flush=True)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args) -> None:
        return

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            texts = body.get("texts", [])
            kind = body.get("kind", "dense")

            if kind == "sparse":
                sparse = [
                    {
                        "indices": vector.indices.tolist(),
                        "values": vector.values.tolist(),
                    }
                    for vector in _sparse.embed(texts)
                ]
                self._send(200, {"sparse": sparse})
            else:
                dense = [vector.tolist() for vector in _dense.embed(texts)]
                self._send(200, {"dense": dense})
        except Exception as exc:
            self._send(500, {"error": str(exc)})


def main() -> None:
    HTTPServer(("127.0.0.1", config.EMBED_PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
