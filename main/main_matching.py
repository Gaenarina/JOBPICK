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


def format_experience(experience):
    if isinstance(experience, dict):
        if experience.get("raw"):
            return str(experience.get("raw"))
        if experience.get("type"):
            return str(experience.get("type"))
        if experience.get("minYears") is not None:
            return f"경력 {experience.get('minYears')}년 이상"
        return ""

    return str(experience or "")


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

        job_posting = job_raw.get("jobPosting", {}) or {}
        requirements = job_posting.get("requirements", {}) or {}

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

        rule_details = result.get("rule_details", {})
        semantic_details = result.get("semantic_details", {})

        final_score = round(result.get("final_score", 0), 2)

        final_result = {
            "id": job_doc_id,
            "jobId": job_doc_id,

            "title": job_posting.get("title", ""),
            "company": job_posting.get("company", ""),
            "location": job_posting.get("location", ""),
            "career": format_experience(requirements.get("experience", "")),
            "category": job_posting.get("category", ""),
            "salary": job_posting.get("salary", ""),

            "matchRate": round(final_score),
            "finalScore": final_score,
            "ruleTotal": round(result.get("rule_total", 0), 2),
            "semanticTotal": round(result.get("semantic_total", 0), 2),

            "embeddingSimilarity": round(full_sim, 4),
            "embeddingScore": round(full_score, 2),

            "unmetConditions": result.get("unmet_conditions", []),

            "matchDetail": {
                "skills": {
                    "score": round(rule_details.get("skill_score", 0), 2),
                    "maxScore": 30,
                    "matchCount": rule_details.get("skill_match_count", 0),
                    "totalCount": rule_details.get("skill_total_count", 0),
                    "matchedSkills": rule_details.get("matched_skills", []),
                    "used": rule_details.get("skill_used", False),
                },
                "education": {
                    "score": round(rule_details.get("edu_score", 0), 2),
                    "maxScore": 10,
                    "jobLevel": rule_details.get("job_edu_level", ""),
                    "resumeLevel": rule_details.get("resume_edu_level", ""),
                    "used": rule_details.get("edu_used", False),
                },
                "experience": {
                    "score": round(rule_details.get("exp_score", 0), 2),
                    "maxScore": rule_details.get("exp_score_max", 20),
                    "minExp": rule_details.get("min_exp", 0),
                    "resumeExp": rule_details.get("resume_exp", 0),
                    "yearScore": round(rule_details.get("exp_year_score", 0), 2),
                    "yearMax": rule_details.get("exp_year_max", 10),
                    "relevanceScore": round(rule_details.get("exp_relevance_score", 0), 2),
                    "relevanceMax": rule_details.get("exp_relevance_max", 10),
                    "relevanceSimilarity": round(rule_details.get("exp_relevance_sim", 0), 4),
                    "relevanceUsed": rule_details.get("exp_relevance_used", False),
                },
                "certifications": {
                    "score": round(rule_details.get("cert_score", 0), 2),
                    "maxScore": 10,
                    "matchCount": rule_details.get("cert_match_count", 0),
                    "totalCount": rule_details.get("cert_total_count", 0),
                    "matchedCerts": rule_details.get("matched_certs", []),
                    "used": rule_details.get("cert_used", False),
                },
                "qualifications": {
                    "score": round(rule_details.get("qual_rule_score", 0), 2),
                    "maxScore": 10,
                    "matchedQuals": rule_details.get("matched_quals", []),
                    "totalCount": rule_details.get("qual_total_count", 0),
                    "used": rule_details.get("qual_used", False),
                },
                "semantic": {
                    "responsibilityScore": round(semantic_details.get("resp_score", 0), 2),
                    "responsibilitySimilarity": round(semantic_details.get("resp_sim", 0), 4),
                    "qualificationScore": round(semantic_details.get("qual_score", 0), 2),
                    "qualificationSimilarity": round(semantic_details.get("qual_sim", 0), 4),
                },
            },
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