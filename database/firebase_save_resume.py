from datetime import datetime


def save_resume(
    db,
    doc_id,  
    structured_data,
    source_file_path="",
    raw_text="",
    preprocessed_text=""
):
    """
    기존 resumes/{doc_id} 문서에 구조화된 이력서 데이터를 업데이트한다.
    """
    print("[save_resume] 업데이트할 doc_id:", doc_id)
    doc_ref = db.collection("resumes").document(doc_id)
    print("[save_resume] doc_ref.id:", doc_ref.id)
    
    save_data = {
        "resume": structured_data,
        "meta": {
            "sourceFilePath": source_file_path,
        },
        "rawText": raw_text,
        "preprocessedText": preprocessed_text,
        "status": "DONE",  # ⭐ 상태 변경
        "updatedAt": datetime.utcnow().isoformat(),
    }

    doc_ref.update(save_data)
    return doc_id


def save_failed_resume(
    db,
    source_file_path="",
    error_message=""
):
    """
    처리 실패한 이력서 데이터를 Firestore에 저장한다.
    """

    doc_ref = db.collection("resumes_failed").document()

    save_data = {
        "meta": {
            "sourceFilePath": source_file_path,
        },
        "errorMessage": str(error_message),
        "createdAt": datetime.utcnow().isoformat(),
    }

    doc_ref.set(save_data)
    return doc_ref.id