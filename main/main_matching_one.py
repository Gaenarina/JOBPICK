import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.firebase_init import init_firebase
from main.main_matching import build_match_result


def process_matching_one_by_ids(resume_doc_id, job_doc_id):
    db, _ = init_firebase("config/firebase_key.json")

    resume_snapshot = db.collection("resumes").document(resume_doc_id).get()

    if not resume_snapshot.exists:
        raise Exception(f"이력서 문서가 없습니다: {resume_doc_id}")

    job_snapshot = db.collection("job_postings").document(job_doc_id).get()

    if not job_snapshot.exists:
        raise Exception(f"공고 문서가 없습니다: {job_doc_id}")

    resume_raw = resume_snapshot.to_dict()
    job_raw = job_snapshot.to_dict()

    from matching.matchtest import flatten_resume

    resume_for_score = flatten_resume(resume_raw)

    result = build_match_result(
        job_doc_id=job_doc_id,
        job_raw=job_raw,
        resume_raw=resume_raw,
        resume_for_score=resume_for_score,
    )

    return {
        "resumeId": resume_doc_id,
        "jobId": job_doc_id,
        **result,
    }


def main():
    if len(sys.argv) < 3:
        print("사용법: py main/main_matching_one.py <resume_doc_id> <job_doc_id>")
        return

    resume_doc_id = sys.argv[1]
    job_doc_id = sys.argv[2]

    result = process_matching_one_by_ids(resume_doc_id, job_doc_id)

    print("\n[1:1 매칭 결과]")
    print(result)


if __name__ == "__main__":
    main()