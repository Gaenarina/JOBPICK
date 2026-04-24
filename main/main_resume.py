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


#PDF_PATH = "data/resume_sample/예시이력서_강하린_많은경력.pdf"
#PDF_PATH = "data/resume_sample/예시이력서_최지훈_고졸.pdf"
#PDF_PATH = "data/resume_sample/예시이력서_박서연_문과.pdf"
PDF_PATH = "data/resume_sample/예시이력서_김도현_이과.pdf"

def main():
    db = init_firebase("config/firebase_key.json")

    try:
        # -----------------------------
        # 1. OCR
        # -----------------------------
        raw_text = extract_text_from_pdf(PDF_PATH)

        # -----------------------------
        # 2. 전처리
        # -----------------------------
        preprocessed_text = preprocess_text(raw_text)

        # -----------------------------
        # 3. 구조화
        # -----------------------------
        structured_data = structure_resume(preprocessed_text)

        # -----------------------------
        # 4. 결과 출력
        # -----------------------------
        print("\n[OCR 원문]")
        print(raw_text)

        print("\n[전처리 결과]")
        print(preprocessed_text)

        print("\n[구조화 결과]")
        print(json.dumps(structured_data, ensure_ascii=False, indent=2))

        # -----------------------------
        # 5. Firestore 저장
        # -----------------------------
        saved_id = save_resume(
            db=db,
            structured_data=structured_data,
            source_file_path=PDF_PATH,
            raw_text=raw_text,
            preprocessed_text=preprocessed_text
        )

        print(f"\n[Firestore 저장 완료] {saved_id}")

    except Exception as error:
        print("\n[처리 실패]")
        print(str(error))

        failed_id = save_failed_resume(
            db=db,
            source_file_path=PDF_PATH,
            error_message=str(error)
        )

        print(f"\n[Firestore 실패 저장] {failed_id}")


if __name__ == "__main__":
    main()