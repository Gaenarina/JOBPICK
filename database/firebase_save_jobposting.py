from datetime import datetime


def save_jobposting(
    db,
    structured_data,
    source_url="",
    company_name="",
    title="",
    posting_type="",
    image_url="",
    raw_text="",
    preprocessed_text=""
):
    """
    구조화된 채용공고 데이터를 Firestore에 저장한다.
    """

    doc_ref = db.collection("job_postings").document()

    save_data = {
        "jobPosting": structured_data.get("jobPosting", {}),
        "meta": {
            "sourceUrl": source_url,
            "companyName": company_name,
            "title": title,
            "postingType": posting_type,
            "imageUrl": image_url,
        },
        "rawText": raw_text,
        "preprocessedText": preprocessed_text,
        "createdAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat(),
    }

    doc_ref.set(save_data)
    return doc_ref.id


def save_failed_jobposting(
    db,
    source_url="",
    company_name="",
    title="",
    posting_type="",
    image_url="",
    error_message=""
):
    """
    처리 실패한 채용공고 데이터를 Firestore에 저장한다.
    """

    doc_ref = db.collection("job_postings_failed").document()

    save_data = {
        "meta": {
            "sourceUrl": source_url,
            "companyName": company_name,
            "title": title,
            "postingType": posting_type,
            "imageUrl": image_url,
        },
        "errorMessage": str(error_message),
        "createdAt": datetime.utcnow().isoformat(),
    }

    doc_ref.set(save_data)
    return doc_ref.id