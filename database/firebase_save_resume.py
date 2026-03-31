from datetime import datetime


def save_resume(
    db,
    structured_data,
    source_file_path="",
    raw_text="",
    preprocessed_text=""
):
    """
    구조화된 이력서 데이터를 Firestore에 저장한다.
    """

    doc_ref = db.collection("resumes").document()

    save_data = {
        "resume": structured_data,
        "meta": {
            "sourceFilePath": source_file_path,
        },
        "rawText": raw_text,
        "preprocessedText": preprocessed_text,
        "createdAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat(),
    }

    doc_ref.set(save_data)
    return doc_ref.id


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