"""Precompute reusable JOB-ALIO and NCS sentence embeddings."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.firebase_init import init_firebase
from main.main_matching import is_enabled_job_source
from matching.matchtest import (
    MODEL_NAME,
    flatten_job,
    get_job_embedding_text,
    get_model,
    get_score_semantic_texts,
    get_similarity_cache_key,
)
from matching.vector_store import METADATA_PATH, STORE_DIR, VECTOR_PATH, text_hash


def _add_text(by_hash, text):
    text = str(text or "").strip()
    if not text:
        return

    # 기존 키도 유지한다.
    by_hash.setdefault(text_hash(text), text)

    # calculate_text_similarity() -> get_text_embedding()이 실제로 조회하는
    # 최종 cache key도 함께 저장한다.
    runtime_key = get_similarity_cache_key(text)
    if runtime_key:
        by_hash.setdefault(text_hash(runtime_key), runtime_key)


def collect_texts(include_jobs=True, include_ncs=True):
    by_hash = {}
    counts = {
        "jobs": 0,
        "jobTexts": 0,
        "ncsUnits": 0,
    }

    if include_jobs:
        db, _ = init_firebase("config/firebase_key.json")

        for snapshot in db.collection("job_postings").stream():
            raw = snapshot.to_dict() or {}

            if not is_enabled_job_source(raw):
                continue

            flat = flatten_job(raw)
            score_texts = get_score_semantic_texts(flat, {})

            job_texts = [
                score_texts[1],
                score_texts[3],
                score_texts[4],
                get_job_embedding_text(raw),
            ]

            before_count = len(by_hash)

            for text in job_texts:
                _add_text(by_hash, text)

            counts["jobTexts"] += max(
                0,
                len(by_hash) - before_count,
            )
            counts["jobs"] += 1

    if include_ncs:
        ncs_path = PROJECT_ROOT / "data" / "ncs_units.json"
        payload = json.loads(
            ncs_path.read_text(encoding="utf-8")
        )

        for unit in payload.get("units", []):
            text = str(
                unit.get("matchText", "")
                or ""
            ).strip()

            if text:
                # NCS matcher는 raw matchText hash를 직접 조회하므로
                # 기존 키를 그대로 유지한다.
                by_hash.setdefault(
                    text_hash(text),
                    text,
                )
                counts["ncsUnits"] += 1

    return by_hash, counts


def precompute_embeddings(
    batch_size=64,
    include_jobs=True,
    include_ncs=True,
):
    texts_by_hash, counts = collect_texts(
        include_jobs,
        include_ncs,
    )

    hashes = list(texts_by_hash)
    texts = [
        texts_by_hash[value]
        for value in hashes
    ]

    model = get_model()

    vectors = model.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).astype(np.float32)

    STORE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_vectors = VECTOR_PATH.with_suffix(
        ".tmp.npy"
    )
    temporary_metadata = METADATA_PATH.with_suffix(
        ".tmp.json"
    )

    np.save(
        temporary_vectors,
        vectors,
    )

    temporary_metadata.write_text(
        json.dumps(
            {
                "model": MODEL_NAME,
                "createdAt": datetime.now(
                    timezone.utc
                ).isoformat(),
                "count": len(hashes),
                "dimension": (
                    int(vectors.shape[1])
                    if len(vectors)
                    else 0
                ),
                "sourceCounts": counts,
                "hashes": hashes,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    temporary_vectors.replace(
        VECTOR_PATH
    )
    temporary_metadata.replace(
        METADATA_PATH
    )

    return {
        "count": len(hashes),
        "sourceCounts": counts,
        "vectorBytes": VECTOR_PATH.stat().st_size,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
    )
    parser.add_argument(
        "--jobs-only",
        action="store_true",
    )
    parser.add_argument(
        "--ncs-only",
        action="store_true",
    )

    args = parser.parse_args()

    result = precompute_embeddings(
        batch_size=max(
            1,
            args.batch_size,
        ),
        include_jobs=not args.ncs_only,
        include_ncs=not args.jobs_only,
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
