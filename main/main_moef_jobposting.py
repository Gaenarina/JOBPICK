"""Synchronize MOEF/JOB-ALIO recruitment postings into Firestore."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sources.moef_recruitment import (
    MoefRecruitmentClient,
    normalize_recruitment,
)


def sync_moef_job_postings(
    db,
    client: MoefRecruitmentClient,
    *,
    num_of_rows: int = 100,
    max_pages: int | None = None,
    ongoing_only: bool = True,
    dry_run: bool = False,
):
    """
    JOB-ALIO API에서 채용공고를 가져와 정규화한 뒤 Firestore에 저장한다.

    dry_run=True인 경우:
    - Firestore에 접근하지 않는다.
    - 정규화 결과만 JSON으로 출력한다.
    """

    filters = {
        "ongoingYn": "Y"
    } if ongoing_only else {}

    stats = {
        "received": 0,
        "created": 0,
        "updated": 0,
        "failed": 0,
    }

    for raw_item in client.iter_recruitments(
        num_of_rows=num_of_rows,
        max_pages=max_pages,
        **filters,
    ):
        stats["received"] += 1

        try:
            # --------------------------------------------------
            # 1. API 원본 데이터 → JOBPICK 공통 구조 정규화
            # --------------------------------------------------
            normalized = normalize_recruitment(raw_item)

            # --------------------------------------------------
            # 2. Dry Run
            #
            # Firestore에 접근하지 않고
            # 정규화 결과만 출력한다.
            # --------------------------------------------------
            if dry_run:
                print(
                    json.dumps(
                        normalized,
                        ensure_ascii=False,
                        indent=2,
                    )
                )

                stats["created"] += 1
                continue

            # --------------------------------------------------
            # 3. 실제 Firestore 저장
            # --------------------------------------------------
            doc_ref = (
                db
                .collection("job_postings")
                .document(normalized["documentId"])
            )

            exists = doc_ref.get().exists

            now = datetime.now(
                timezone.utc
            ).isoformat()

            save_data = {
                "jobPosting":
                    normalized["jobPosting"],

                "meta":
                    normalized["meta"],

                "rawApiData":
                    normalized["rawApiData"],

                "updatedAt":
                    now,
            }

            # 새 문서일 때만 createdAt 추가
            if not exists:
                save_data["createdAt"] = now

            doc_ref.set(
                save_data,
                merge=True,
            )

            if exists:
                stats["updated"] += 1
            else:
                stats["created"] += 1

        except Exception as error:
            stats["failed"] += 1

            print(
                f"[MOEF] failed to normalize/save item: {error}",
                file=sys.stderr,
            )

    return stats


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Sync MOEF public-institution "
            "job postings"
        )
    )

    parser.add_argument(
        "--rows",
        type=int,
        default=100,
        help="items per API page",
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="optional page limit",
    )

    parser.add_argument(
        "--include-closed",
        action="store_true",
        help="also request closed postings",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "print normalized data "
            "without Firestore writes"
        ),
    )

    args = parser.parse_args()

    # ------------------------------------------------------
    # API Client
    # ------------------------------------------------------
    client = MoefRecruitmentClient.from_env()

    # ------------------------------------------------------
    # Firestore
    #
    # dry-run에서는 Firestore 초기화 자체를 하지 않는다.
    # ------------------------------------------------------
    db = None

    if not args.dry_run:
        from database.firebase_init import init_firebase

        db, _ = init_firebase(
            os.getenv(
                "FIREBASE_KEY_PATH",
                "config/firebase_key.json",
            )
        )

    # ------------------------------------------------------
    # 동기화 실행
    # ------------------------------------------------------
    stats = sync_moef_job_postings(
        db,
        client,
        num_of_rows=args.rows,
        max_pages=args.max_pages,
        ongoing_only=not args.include_closed,
        dry_run=args.dry_run,
    )

    print(
        f"[MOEF] sync complete: {stats}"
    )


if __name__ == "__main__":
    main()