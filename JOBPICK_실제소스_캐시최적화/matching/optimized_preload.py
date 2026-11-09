"""Cache-accounted, batch SBERT preload for actual matching texts.

Uses the original JOBPICK semantic preprocessing, model, encoding settings,
embedding RAM cache, and precomputed vector lookup. Does not change scores.
"""
from __future__ import annotations

from typing import Any, Dict, List

import matching.matchtest as mt
from matching.vector_store import get_vector


def preload_prepared_score_embeddings(
    prepared_contexts: List[Dict[str, Any]],
    batch_size: int = 32,
    extra_similarity_texts: List[str] | None = None,
):
    """Preload only unseen texts, recording RAM/file/live counts separately."""
    seen = set()
    live_texts = []
    field_stats = {}
    stats = {
        "uniqueCount": 0,
        "memoryHitCount": 0,
        "vectorHitCount": 0,
        "duplicateCount": 0,
        "encodedCount": 0,
        "cacheCount": 0,
        "fieldStats": field_stats,
    }

    def collect(text: str, field: str):
        key = mt.get_similarity_cache_key(text)
        if not key:
            return
        field_info = field_stats.setdefault(
            field, {"memory": 0, "precomputed": 0, "live": 0, "duplicate": 0}
        )
        if key in seen:
            stats["duplicateCount"] += 1
            field_info["duplicate"] += 1
            return
        seen.add(key)
        if key in mt._embedding_cache:
            mt._embedding_cache.move_to_end(key)
            stats["memoryHitCount"] += 1
            field_info["memory"] += 1
            return
        # Keep exactly the original file-store lookup semantics.
        if get_vector(key) is not None:
            stats["vectorHitCount"] += 1
            field_info["precomputed"] += 1
            return
        live_texts.append(key)
        field_info["live"] += 1

    labels = (
        "resume_full", "job_full", "resume_experience",
        "job_responsibilities", "job_qualifications",
    )
    for context in prepared_contexts or []:
        for field, text in zip(labels, context.get("semantic_texts", ()) or ()):
            collect(text, field)
    for index, text in enumerate(extra_similarity_texts or []):
        collect(text, "resume_embedding" if index == 0 else "job_embedding")

    # Preserve the original encode order/options; only skip existing embeddings.
    if live_texts:
        embeddings = mt.get_model().encode(
            live_texts,
            convert_to_tensor=True,
            batch_size=batch_size,
            show_progress_bar=False,
        )
        for key, embedding in zip(live_texts, embeddings):
            mt._embedding_cache[key] = embedding
            mt._embedding_cache.move_to_end(key)
        while len(mt._embedding_cache) > mt.EMBEDDING_CACHE_LIMIT:
            mt._embedding_cache.popitem(last=False)

    stats["encodedCount"] = len(live_texts)
    stats["uniqueCount"] = len(seen)
    stats["cacheCount"] = len(mt._embedding_cache)
    return stats
