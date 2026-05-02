from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
from google.cloud import vision
from google.oauth2 import service_account
from selenium.webdriver.support.ui import Select

# ChromaDB
import chromadb
from chromadb.utils import embedding_functions

# ============================
# Google Vision API 설정
# ============================
credentials = service_account.Credentials.from_service_account_file(
    r"C:\Users\user\job-pick\crawler\trusty-monument-490208-k4-723b7a54493a.json"
)

vision_client = vision.ImageAnnotatorClient(credentials=credentials)

def ocr_from_image_url(img_url):
    response = requests.get(img_url, timeout=15)
    response.raise_for_status()
    image = vision.Image(content=response.content)
    result = vision_client.document_text_detection(image=image)
    if result.error.message:
        raise Exception(result.error.message)
    if result.full_text_annotation:
        return result.full_text_annotation.text.strip()
    return ""

# ============================
# Chrome 드라이버 설정
# ============================
chrome_options = Options()
chrome_options.add_argument("--headless")  # 화면 띄우지 않음
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--ignore-certificate-errors")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 10)

# ============================
# ChromaDB 설정
# ============================
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="job_postings")

# ============================
# 잡코리아 카테고리 페이지
# ============================
driver.get('https://www.jobkorea.co.kr/recruit/joblist?menucode=local&localorder=1')
time.sleep(3)

# 등록일순 정렬
order_select = wait.until(EC.presence_of_element_located((By.ID, "orderTab")))
driver.execute_script("""
arguments[0].value = '2';
arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
""", order_select)
wait.until(lambda d: d.find_element(By.ID, "orderTab").get_attribute("value") == "2")
time.sleep(2)

print("현재 정렬값:", driver.find_element(By.ID, "orderTab").get_attribute("value"))

# ============================
# 공고 링크 수집
# ============================
target_count = 50  # 가져올 공고 수
links = []

items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.titBx")))

for item in items:
    if len(links) >= target_count:
        break
    try:
        link = item.find_element(By.CSS_SELECTOR, "strong a").get_attribute("href")
        if link.startswith("/"):
            link = "https://www.jobkorea.co.kr" + link
        links.append(link)
    except Exception as e:
        print("링크 추출 실패:", e)
        continue

# ============================
# 공고 상세 크롤링 & ChromaDB 저장
# ============================
for link in links:
    driver.get(link)
    time.sleep(2)
    print("\n==============================")

    # 회사명
    try:
        company = driver.find_element(By.CSS_SELECTOR, '[data-sentry-component="CompanyName"] h2').text
    except:
        company = "없음"

    # 제목
    try:
        title = driver.find_element(By.CSS_SELECTOR, '[data-sentry-component="TitleContent"] h1').text
    except:
        title = "없음"

    # 공고 내용
    full_text = ""
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if iframes:
        driver.switch_to.frame(iframes[0])

    rows = driver.find_elements(By.CSS_SELECTOR, "div.artTplDetail table tbody tr")
    if rows:
        print("텍스트 공고")
        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 3:
                    position = cells[0].text
                    requirement = cells[2].text
                    full_text += f"{position} {requirement}\n"
            except:
                continue
    else:
        print("이미지 공고")
        imgs = driver.find_elements(By.CSS_SELECTOR, "td.detailTable img")
        if imgs:
            for img in imgs:
                img_url = img.get_attribute("src")
                if not img_url:
                    continue
                try:
                    text = ocr_from_image_url(img_url)
                    if text.strip():
                        full_text += text + "\n"
                except Exception as e:
                    print("OCR 실패:", e)

    driver.switch_to.default_content()

    # ============================
    # ChromaDB 저장
    # ============================
    job_text = company + " " + title + "\n" + full_text
    collection.add(
        documents=[job_text],
        ids=[link],
        metadatas=[{"company": company, "title": title, "url": link}]
    )

    print(f"저장 완료: {company} - {title}")

driver.quit()
print("크롤링 및 ChromaDB 저장 완료 ✅")