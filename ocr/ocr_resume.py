# ocr_resume.py

import io
import os
from google.cloud import vision
from google.oauth2 import service_account


# -----------------------------
# 1. Google Vision 인증
# -----------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_PATH = os.path.join(BASE_DIR, "config", "vision_key.json")

if not os.path.exists(KEY_PATH):
    raise FileNotFoundError(f"Google Vision 키 파일을 찾을 수 없습니다: {KEY_PATH}")

credentials = service_account.Credentials.from_service_account_file(KEY_PATH)
vision_client = vision.ImageAnnotatorClient(credentials=credentials)


# -----------------------------
# 2. Vision 응답 → 텍스트 추출
# -----------------------------
def extract_text_from_vision_response(vision_result) -> str:
    extracted_texts = []

    for file_response in vision_result.responses:
        for page_response in file_response.responses:
            if page_response.error.message:
                raise Exception(page_response.error.message)

            if page_response.full_text_annotation.text:
                extracted_texts.append(page_response.full_text_annotation.text)

    return "\n".join(extracted_texts).strip()


# -----------------------------
# 3. PDF에서 텍스트 추출 (OCR)
# -----------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    with io.open(pdf_path, "rb") as pdf_file:
        pdf_content = pdf_file.read()

    input_config = vision.InputConfig(
        content=pdf_content,
        mime_type="application/pdf"
    )

    feature = vision.Feature(
        type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION
    )

    request = vision.AnnotateFileRequest(
        input_config=input_config,
        features=[feature]
    )

    vision_result = vision_client.batch_annotate_files(requests=[request])

    return extract_text_from_vision_response(vision_result)