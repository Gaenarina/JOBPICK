"""Read-only local embedding store shared by job and NCS matching."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Optional

import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[1]
STORE_DIR = ROOT_DIR / "data" / "embeddings"
METADATA_PATH = STORE_DIR / "text_vectors.json"
VECTOR_PATH = STORE_DIR / "text_vectors.npy"

_metadata_mtime = None
_hash_to_index = {}
_vectors = None


def text_hash(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def _load_store():
    global _metadata_mtime, _hash_to_index, _vectors
    if not METADATA_PATH.exists() or not VECTOR_PATH.exists():
        return
    mtime = max(METADATA_PATH.stat().st_mtime_ns, VECTOR_PATH.stat().st_mtime_ns)
    if _metadata_mtime == mtime and _vectors is not None:
        return
    try:
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        hashes = metadata.get("hashes", [])
        vectors = np.load(VECTOR_PATH, mmap_mode="r")
        if len(hashes) != len(vectors):
            return
        _hash_to_index = {value: index for index, value in enumerate(hashes)}
        _vectors = vectors
        _metadata_mtime = mtime
    except (OSError, ValueError, json.JSONDecodeError):
        _hash_to_index = {}
        _vectors = None


def get_vector(text: str) -> Optional[np.ndarray]:
    _load_store()
    index = _hash_to_index.get(text_hash(text))
    if index is None or _vectors is None:
        return None
    return np.asarray(_vectors[index], dtype=np.float32)


def get_vectors(texts: Iterable[str]) -> Optional[np.ndarray]:
    _load_store()
    indices = []
    for text in texts:
        index = _hash_to_index.get(text_hash(text))
        if index is None:
            return None
        indices.append(index)
    if _vectors is None or not indices:
        return None
    return np.asarray(_vectors[indices], dtype=np.float32)
