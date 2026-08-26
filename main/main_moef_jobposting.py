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

from sources.moef_recruitment import MoefRecruitmentClient, normalize_recruitment


def sync_moef_job_postings(
    db,
    client: MoefRecruitmentClient,
    *,
    num_of_rows: int = 100,
    max_pages: int | None = None,
    ongoing_only: bool = True,
    dry_run: bool = False,
):
    filters = {"ongoingYn": "Y"} if ongoing_only else {}
    stats = {"received": 0, "created": 0, "updated": 0, "failed": 0}

    for raw_item in client.iter_recruitments(
        num_of_rows=num_of_rows,
        max_pages=max_pages,
        **filters,
    ):
        stats["received"] += 1
        try:
            normalized = normalize_recruitment(raw_item)
            doc_ref = db.collection("job_postings").document(normalized["documentId"])
            exists = doc_ref.get().exists if not dry_run else False
            now = datetime.now(timezone.utc).isoformat()
            save_data = {
                "jobPosting": normalized["jobPosting"],
                "meta": normalized["meta"],
                "rawApiData": normalized["rawApiData"],
                "updatedAt": now,
            }
            if not exists:
                save_data["createdAt"] = now

            if dry_run:
                print(json.dumps(normalized, ensure_ascii=False, indent=2))
            else:
                doc_ref.set(save_data, merge=True)
            stats["updated" if exists else "created"] += 1
        except Exception as error:
            stats["failed"] += 1
            print(f"[MOEF] failed to normalize/save item: {error}", file=sys.stderr)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Sync MOEF public-institution job postings")
    parser.add_argument("--rows", type=int, default=100, help="items per API page")
    parser.add_argument("--max-pages", type=int, default=None, help="optional page limit")
    parser.add_argument("--include-closed", action="store_true", help="also request closed postings")
    parser.add_argument("--dry-run", action="store_true", help="print normalized data without Firestore writes")
    args = parser.parse_args()

    client = MoefRecruitmentClient.from_env()
    if args.dry_run:
        db = None
    else:
        from database.firebase_init import init_firebase

        db, _ = init_firebase(os.getenv("FIREBASE_KEY_PATH", "config/firebase_key.json"))

    if db is None:
        class DryRunDb:
            pass
        db = DryRunDb()

    stats = sync_moef_job_postings(
        db,
        client,
        num_of_rows=args.rows,
        max_pages=args.max_pages,
        ongoing_only=not args.include_closed,
        dry_run=args.dry_run,
    )
    print(f"[MOEF] sync complete: {stats}")


if __name__ == "__main__":
    main()
