import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.firebase_init import init_firebase
from matching.matchtest import (
    flatten_resume,
    flatten_job,
    calculate_full_score,
    get_resume_embedding_text,
    get_job_embedding_text,
    calculate_full_embedding_similarity,
)


def process_matching_by_resume_id(resume_doc_id, limit=5):
    db, _ = init_firebase("config/firebase_key.json")

    resume_snapshot = db.collection("resumes").document(resume_doc_id).get()

    if not resume_snapshot.exists:
        raise Exception(f"이력서 문서가 없습니다: {resume_doc_id}")

    resume_raw = resume_snapshot.to_dict()
    resume_for_score = flatten_resume(resume_raw)
    resume_embedding_text = get_resume_embedding_text(resume_raw)

    job_snapshots = db.collection("job_postings").stream()

    results = []

    for job_snapshot in job_snapshots:
        job_doc_id = job_snapshot.id
        job_raw = job_snapshot.to_dict()

        job_for_score = flatten_job(job_raw)

        result = calculate_full_score(
            job_for_score,
            resume_for_score,
            label=f"resume {resume_doc_id} - job {job_doc_id}"
        )

        job_embedding_text = get_job_embedding_text(job_raw)

        full_sim, full_score = calculate_full_embedding_similarity(
            resume_embedding_text,
            job_embedding_text
        )

        final_result = {
            "jobId": job_doc_id,
            "title": job_raw.get("jobPosting", {}).get("title", ""),
            "company": job_raw.get("jobPosting", {}).get("company", ""),
            "finalScore": round(result.get("final_score", 0), 2),
            "ruleTotal": round(result.get("rule_total", 0), 2),
            "semanticTotal": round(result.get("semantic_total", 0), 2),
            "embeddingSimilarity": round(full_sim, 4),
            "embeddingScore": round(full_score, 2),
            "unmetConditions": result.get("unmet_conditions", []),
        }

        results.append(final_result)

    results.sort(key=lambda x: x["finalScore"], reverse=True)

    return results[:limit]


def main():
    if len(sys.argv) < 2:
        print("사용법: py main/main_matching.py <resume_doc_id>")
        return

    resume_doc_id = sys.argv[1]
    results = process_matching_by_resume_id(resume_doc_id)

    print("\n[매칭 결과]")
    for item in results:
        print(item)


if __name__ == "__main__":
    main()