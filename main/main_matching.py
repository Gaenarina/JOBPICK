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
from embedding.chroma_store import (
    get_chroma_collection,
    upsert_document,
    query_similar,
)


RESUME_DOC_ID = "b78i1EMnKNQUk1nUjjFh"
JOB_DOC_ID = "MospcNiJf0Q5u3fzRwdR"


def main():
    db = init_firebase("config/firebase_key.json")

    try:
        resume_snapshot = db.collection("resumes").document(RESUME_DOC_ID).get()
        job_snapshot = db.collection("job_postings").document(JOB_DOC_ID).get()

        if not resume_snapshot.exists:
            print("[오류] 이력서 문서가 없습니다.")
            print(f"resume doc id: {RESUME_DOC_ID}")
            return

        if not job_snapshot.exists:
            print("[오류] 공고 문서가 없습니다.")
            print(f"jobPosting doc id: {JOB_DOC_ID}")
            return

        resume_raw = resume_snapshot.to_dict()
        job_raw = job_snapshot.to_dict()

        resume_for_score = flatten_resume(resume_raw)
        job_for_score = flatten_job(job_raw)

        print("\n[정규화된 이력서 데이터]")
        print(resume_for_score)

        print("\n[정규화된 공고 데이터]")
        print(job_for_score)

        # 1. 룰 기반 + 의미 기반 점수 계산
        result = calculate_full_score(
            job_for_score,
            resume_for_score,
            label="실제 Firebase 데이터 비교"
        )

        # 2. fullForEmbedding 전체 임베딩 유사도 계산
        resume_embedding_text = get_resume_embedding_text(resume_raw)
        job_embedding_text = get_job_embedding_text(job_raw)

        print("\n[이력서 fullForEmbedding]")
        print(resume_embedding_text)

        print("\n[공고 fullForEmbedding]")
        print(job_embedding_text)

        full_sim, full_score = calculate_full_embedding_similarity(
            resume_embedding_text,
            job_embedding_text
        )

        print("\n[전체 임베딩 유사도]")
        print(f"유사도: {full_sim:.4f}")
        print(f"20점 환산 점수: {full_score:.2f}")

        # 3. ChromaDB 저장
        collection = get_chroma_collection()

        upsert_document(
            collection=collection,
            doc_id=f"resume_{RESUME_DOC_ID}",
            text=resume_embedding_text,
            metadata={
                "type": "resume",
                "docId": RESUME_DOC_ID,
                "name": resume_raw.get("resume", {}).get("resumeData", {}).get("basicInfo", {}).get("name", "")
            }
        )

        upsert_document(
            collection=collection,
            doc_id=f"job_{JOB_DOC_ID}",
            text=job_embedding_text,
            metadata={
                "type": "job_posting",
                "docId": JOB_DOC_ID,
                "title": job_raw.get("jobPosting", {}).get("title", "")
            }
        )

        print("\n[ChromaDB 저장 완료]")

        # 4. 이력서 기준 유사 문서 조회
        chroma_result = query_similar(
            collection=collection,
            query_text=resume_embedding_text,
            n_results=3
        )

        print("\n[ChromaDB 유사도 조회 결과]")
        print(chroma_result)

        # 5. 발표용 최종 요약
        print("\n[최종 요약]")
        print(f"- 룰 기반 점수: {result['rule_total']:.2f}/80")
        print(f"- 의미 기반 점수: {result['semantic_total']:.2f}/20")
        print(f"- 합산 점수: {result['final_score']:.2f}/100")
        print(f"- 전체 임베딩 유사도: {full_sim:.4f}")
        print(f"- 전체 임베딩 20점 환산: {full_score:.2f}")

        print("\n[미충족 조건]")
        if result["unmet_conditions"]:
            for reason in result["unmet_conditions"]:
                print(f"- {reason}")
        else:
            print("- 없음")

        print("\n[최종 결과 dict]")
        print(result)

    except Exception as error:
        print("\n[매칭 실패]")
        print(str(error))


if __name__ == "__main__":
    main()