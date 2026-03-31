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

credentials = service_account.Credentials.from_service_account_file(
    "C:/Users/82109/sbert_prtc/sunlit-plasma-488515-g8-8704e17d4636.json"
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


# Chrome 옵션 설정 (헤드리스로 실행하려면)
chrome_options = Options()
chrome_options.add_argument("--headless")  # 화면을 띄우지 않고 실행
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--ignore-certificate-errors")  # SSL 인증서 오류 무시


# ChromeDriver 경로 설정 (chromedriver가 PATH에 있으면 경로 생략 가능)
#chrome_driver_path = 'C:\\Users\\82109\\crawling\\Crawling\\selenium\\Scripts\\chromedriver.exe' # 크롬 드라이버 경로

#service = Service(executable_path=chrome_driver_path)


service = Service(ChromeDriverManager().install())

# 웹드라이버 실행
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 10)

# 카테고리 페이지로 이동
driver.get('https://www.jobkorea.co.kr/recruit/joblist?menucode=local&localorder=1')

# 페이지 로드 대기
time.sleep(3)


# 등록일순 정렬 적용
order_select = wait.until(EC.presence_of_element_located((By.ID, "orderTab")))

driver.execute_script("""
arguments[0].value = '2';
arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
""", order_select)

wait.until(lambda d: d.find_element(By.ID, "orderTab").get_attribute("value") == "2")

time.sleep(2)

print("현재 정렬값:", driver.find_element(By.ID, "orderTab").get_attribute("value"))


'''
# 정렬 위치까지 스크롤
driver.execute_script("window.scrollTo(0, 500);")
time.sleep(1)

# 드롭다운 열기
sort_dropdown = wait.until(
    EC.presence_of_element_located((By.XPATH, "//*[normalize-space()='추천순']"))
)
driver.execute_script("arguments[0].click();", sort_dropdown)
time.sleep(1)

# 등록일순 선택
sort_option = wait.until(
    EC.presence_of_element_located((By.XPATH, "//*[normalize-space()='등록일순']"))
)
driver.execute_script("arguments[0].click();", sort_option)
time.sleep(3)
'''


target_count = 4 # 가져올 공고 수
links = []
#collected_count = 0  # 수집된 공고 수


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



for link in links:

    driver.get(link)
    time.sleep(2)

    print("\n==============================")

    try:
        company = driver.find_element(By.CSS_SELECTOR, '[data-sentry-component="CompanyName"] h2').text
        print("회사:", company)

    except:
        print("회사: 없음")


    try:
        title = driver.find_element(By.CSS_SELECTOR, '[data-sentry-component="TitleContent"] h1').text
        print("공고 제목:", title)

    except:
        print("제목: 없음")


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

                    print("포지션:", position)
                    print("자격요건:", requirement)
                    print("-----")

            except:
                continue


    else:

        print("이미지 공고")

        imgs = driver.find_elements(By.CSS_SELECTOR, "td.detailTable img")

        if imgs:

            ocr_texts = []

            for img in imgs:

                img_url = img.get_attribute("src")

                if not img_url:
                    continue

                print("공고 이미지:", img_url)

                try:

                    text = ocr_from_image_url(img_url)

                    if text.strip():
                        ocr_texts.append(text)

                except Exception as e:
                    print("OCR 실패:", e)


            full_text = "\n".join(ocr_texts)

            print("\nOCR 결과:")
            print(full_text[:500])  # 너무 길어서 일부만 출력


    driver.switch_to.default_content()



    '''
        items = driver.find_elements(By.CSS_SELECTOR, '[data-sentry-component="QualificationItem"]')



        if items:
            for item in items:
                spans = item.find_elements(By.TAG_NAME, "span")

                if len(spans) >= 2:
                    label = spans[0].text
                    value = " ".join([s.text for s in spans[1:]])

                    print(label, ":", value)
    '''


driver.quit()