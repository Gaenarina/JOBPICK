from google.cloud import vision
from google.oauth2 import service_account
import io

credentials = service_account.Credentials.from_service_account_file(
    "C:/Users/82109/sbert_prtc/sunlit-plasma-488515-g8-8704e17d4636.json"
)

client = vision.ImageAnnotatorClient(credentials=credentials)

# 이미지 파일 열기
with io.open("test.png", "rb") as image_file:
    content = image_file.read()

image = vision.Image(content=content)

# 텍스트 감지 요청
response = client.text_detection(image=image)
texts = response.text_annotations

if texts:
    print("전체 인식 텍스트:")
    print(texts[0].description)
else:
    print("텍스트 감지 실패")

if response.error.message:
    raise Exception(response.error.message)