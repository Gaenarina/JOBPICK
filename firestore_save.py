import uuid
import firebase_admin
from firebase_admin import credentials, firestore

# -----------------------------
# Firebase 초기화
# -----------------------------
def init_firebase(firebase_key_path="firebase_key.json"):
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_key_path)
        firebase_admin.initialize_app(cred)

    return firestore.client()


# -----------------------------
# Firestore 저장 함수
# 문서 1개 = 채용공고 1개
# 핵심은 jobPosting 저장
# -----------------------------
def save_job_posting_to_firestore(db, posting, structured_data):
    doc_id = str(uuid.uuid4())

    main_data = posting.get("main") or {}
    posting_type = main_data.get("posting_type", "unknown")
    job_posting = structured_data.get("jobPosting", {})

    doc_data = {
        "docId": doc_id,
        "sourceSite": "jobkorea",
        "sourceUrl": posting.get("url", ""),
        "company": posting.get("company", ""),
        "title": posting.get("title", ""),
        "postingType": posting_type,
        "jobPosting": job_posting,
        "status": "DONE",
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }

    db.collection("documents").document(doc_id).set(doc_data)
    print(f"[Firestore 저장 완료] {doc_id} | {posting.get('title', '')}")


# -----------------------------
# 실패 저장 함수 (선택)
# -----------------------------
def save_failed_posting_to_firestore(db, posting, error_message):
    doc_id = str(uuid.uuid4())

    doc_data = {
        "docId": doc_id,
        "sourceSite": "jobkorea",
        "sourceUrl": posting.get("url", ""),
        "company": posting.get("company", ""),
        "title": posting.get("title", ""),
        "postingType": "unknown",
        "status": "FAILED",
        "errorMessage": str(error_message),
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }

    db.collection("documents").document(doc_id).set(doc_data)
    print(f"[Firestore 실패 저장] {doc_id} | {posting.get('url', '')}")