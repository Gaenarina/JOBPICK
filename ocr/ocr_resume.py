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

# 로컬에서는 기존 JSON 파일 사용
if os.path.exists(KEY_PATH):
    credentials = service_account.Credentials.from_service_account_file(KEY_PATH)

# Render 등 배포 환경에서는 환경변수 사용
else:
    project_id = os.getenv("VISION_PROJECT_ID")
    client_email = os.getenv("VISION_CLIENT_EMAIL")
    private_key = os.getenv("VISION_PRIVATE_KEY")

    if not project_id or not client_email or not private_key:
        raise RuntimeError(
            "Google Vision 인증 정보가 없습니다. "
            "vision_key.json 또는 Vision 환경변수를 확인하세요."
        )

    service_account_info = {
        "type": "service_account",
        "project_id": project_id,
        "client_email": client_email,
        "private_key": private_key.replace("\\n", "\n"),
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info
    )

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