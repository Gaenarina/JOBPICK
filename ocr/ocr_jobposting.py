# ocr_jobposting

import os
import requests
from google.cloud import vision
from google.oauth2 import service_account

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

VISION_KEY_PATH = os.path.join(PROJECT_ROOT, "config", "vision_key.json")

# -----------------------------
# 1. Google Vision 인증
# -----------------------------
credentials = service_account.Credentials.from_service_account_file(
    VISION_KEY_PATH
)

vision_client = vision.ImageAnnotatorClient(credentials=credentials)


# -----------------------------
# 2. 이미지에서 텍스트 추출
# -----------------------------
def extract_text_from_image(image_url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.jobkorea.co.kr/"
    }

    response = requests.get(image_url, headers=headers, timeout=15)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    print("status:", response.status_code)
    print("content-type:", content_type)
    print("content-length:", len(response.content))

    # 디버깅용 저장
    with open("debug_jobkorea_image.bin", "wb") as file:
        file.write(response.content)

    if not content_type.startswith("image/"):
        raise Exception(f"이미지 응답이 아닙니다. Content-Type: {content_type}")

    image = vision.Image(content=response.content)
    result = vision_client.document_text_detection(image=image)

    if result.error.message:
        raise Exception(result.error.message)

    if result.full_text_annotation:
        return result.full_text_annotation.text.strip()

    return ""