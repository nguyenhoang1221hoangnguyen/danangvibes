from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.bundle import EMPTY_FAISS_SENTINEL


class FaissBuilder:
    def __init__(self) -> None:
        self._index: Any | None = None
        self._dimension: int | None = None
        self._count = 0

    def add_embedding(self, embedding: list[float]) -> int:
        try:
            import faiss
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("Install faiss-cpu and numpy to enable face indexing") from exc

        vector = np.array([embedding], dtype="float32")
        faiss.normalize_L2(vector)
        if self._index is None:
            self._dimension = int(vector.shape[1])
            self._index = faiss.IndexFlatIP(self._dimension)
        vector_id = int(self._index.ntotal)
        self._index.add(vector)
        self._count += 1
        return vector_id

    def save(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if self._index is None:
            output_path.write_bytes(EMPTY_FAISS_SENTINEL)
            return
        import faiss

        faiss.write_index(self._index, str(output_path))

    @property
    def count(self) -> int:
        return self._count
