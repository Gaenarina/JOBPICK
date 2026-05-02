import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ocr.ocr_resume import extract_text_from_pdf
from preprocess.preprocess_resume import preprocess_text
from structure.structure_resume import structure_resume

from database.firebase_init import init_firebase
from database.firebase_save_resume import (
    save_resume,
    save_failed_resume,
)
from database.firebase_storage_resume import download_resume_from_storage


def main(doc_id):
    db, bucket = init_firebase("config/firebase_key.json")
    local_pdf_path = ""

    try:
        # -----------------------------
        # 0. Firestore에서 storagePath 조회
        # -----------------------------
        doc_ref = db.collection("resumes").document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise Exception("문서 없음")

        doc_ref.update({
            "status": "PROCESSING"
        })

        data = doc.to_dict()
        storage_path = data["storagePath"]

        # -----------------------------
        # 1. Storage에서 PDF 다운로드
        # -----------------------------
        local_pdf_path = download_resume_from_storage(bucket, storage_path)

        # -----------------------------
        # 2. OCR
        # -----------------------------
        raw_text = extract_text_from_pdf(local_pdf_path)

        # -----------------------------
        # 3. 전처리
        # -----------------------------
        preprocessed_text = preprocess_text(raw_text)

        # -----------------------------
        # 4. 구조화
        # -----------------------------
        structured_data = structure_resume(preprocessed_text)

        # -----------------------------
        # 5. 결과 출력
        # -----------------------------
        print("\n[OCR 원문]")
        print(raw_text)

        print("\n[전처리 결과]")
        print(preprocessed_text)

        print("\n[구조화 결과]")
        print(json.dumps(structured_data, ensure_ascii=False, indent=2))

        # -----------------------------
        # 6. Firestore 저장
        # -----------------------------
        print("[main_resume] 전달할 doc_id:", doc_id)

        saved_id = save_resume(
            db=db,
            doc_id=doc_id,
            structured_data=structured_data,
            source_file_path=storage_path,
            raw_text=raw_text,
            preprocessed_text=preprocessed_text
        )

        print(f"\n[Firestore 저장 완료] {saved_id}")

        doc_ref.update({
            "status": "DONE"
        })

    except Exception as error:
        print("\n[처리 실패]")
        print(str(error))

        failed_id = save_failed_resume(
            db=db,
            source_file_path=storage_path if 'storage_path' in locals() else "",
            error_message=str(error)
        )

        print(f"\n[Firestore 실패 저장] {failed_id}")

        doc_ref.update({
            "status": "FAILED"
        })

    finally:
        if local_pdf_path and os.path.exists(local_pdf_path):
            os.remove(local_pdf_path)

def process_resume_by_doc_id(doc_id):
    main(doc_id)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: py main/main_resume.py <doc_id>")
    else:
        main(sys.argv[1])
