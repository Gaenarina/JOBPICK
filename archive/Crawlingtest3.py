from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# -------------------------
# 유틸 함수
# -------------------------
def clean_text(text):
    return " ".join(text.split()).strip() if text else ""

def move_to_best_job_content_context(driver):
    driver.switch_to.default_content()
    iframes = driver.find_elements(By.TAG_NAME, "iframe")

    # 1) iframe 안 신형 상세 본문
    for iframe in iframes:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)
            if driver.find_elements(By.CSS_SELECTOR, ".detailed-summary-contents, #dev-template-v2-part"):
                return
        except:
            continue

    # 2) iframe 안 구형/이미지
    for iframe in iframes:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)
            if driver.find_elements(By.CSS_SELECTOR, ".secDetailWrap, .artTplDetail, td.detailTable, .detailTable"):
                return
        except:
            continue

    # 3) default content 신형
    driver.switch_to.default_content()
    if driver.find_elements(By.CSS_SELECTOR, ".detailed-summary-contents, #dev-template-v2-part"):
        return

    # 4) default content 구형/이미지
    if driver.find_elements(By.CSS_SELECTOR, ".secDetailWrap, .artTplDetail, td.detailTable, .detailTable"):
        return

    driver.switch_to.default_content()

def get_valid_detail_images(driver):
    valid_urls = []
    selectors = ["td.detailTable img", ".detailTable img", ".secDetailWrap td img"]
    excluded_keywords = ["logo", "icon", "btn", "button", "로고", "아이콘", "버튼"]

    for selector in selectors:
        try:
            imgs = driver.find_elements(By.CSS_SELECTOR, selector)
            for img in imgs:
                src = img.get_attribute("src")
                alt = (img.get_attribute("alt") or "").lower()
                if not src or src.startswith("data:image") or any(k in alt for k in excluded_keywords):
                    continue
                if src not in valid_urls:
                    valid_urls.append(src)
        except:
            continue
    return valid_urls

# -------------------------
# 구형 텍스트 공고
# -------------------------
def print_old_template_posting(driver):
    print("공고 유형: 구형 텍스트 공고")
    rows = driver.find_elements(By.CSS_SELECTOR, "div.artTplDetail.artRecruit table tbody tr")
    try:
        company_desc = driver.find_element(By.CSS_SELECTOR, ".artTopDesc .desc").text
        print("\n[기업소개]")
        print(clean_text(company_desc))
    except:
        print("\n[기업소개] 없음")

    current_group = ""
    current_exp = ""
    print("\n[모집분야 및 자격요건]")
    for row in rows:
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue
            if len(cells) == 5:
                current_group = clean_text(cells[0].text)
                group_name = current_group
                job_name = clean_text(cells[1].text)
                responsibilities = clean_text(cells[2].text)
                qualifications = clean_text(cells[3].text)
                current_exp = clean_text(cells[4].text)
                exp_type = current_exp
            elif len(cells) == 4:
                group_name = current_group
                job_name = clean_text(cells[0].text)
                responsibilities = clean_text(cells[1].text)
                qualifications = clean_text(cells[2].text)
                exp_text = clean_text(cells[3].text)
                if exp_text:
                    current_exp = exp_text
                exp_type = current_exp
            else:
                continue
            print("-" * 40)
            print("구분:", group_name)
            print("직무:", job_name)
            print("담당업무:", responsibilities)
            print("자격요건/우대사항:", qualifications)
            print("신입/경력:", exp_type)
        except:
            continue

    # 공통자격 요건
    try:
        common_section = driver.find_element(By.CSS_SELECTOR, ".artTplDetail.artRequire")
        common_items = common_section.find_elements(By.CSS_SELECTOR, "li")
        print("\n[공통자격 요건]")
        for item in common_items:
            txt = clean_text(item.text)
            if txt:
                print("-", txt)
    except:
        print("\n[공통자격 요건] 없음")

# -------------------------
# 신형 상세 본문
# -------------------------
def print_new_detail_posting(driver):
    print("공고 유형: 신형 텍스트 공고")
    print("\n[상세 본문]")
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, "#dev-template-v2-part .dev-list-type tbody tr")
        for row in rows:
            tds = row.find_elements(By.TAG_NAME, "td")
            if len(tds) < 2:
                continue
            header_text = clean_text(tds[0].text)
            body_text = clean_text(tds[1].text)
            print("-" * 40)
            print("모집영역:", header_text)
            print(body_text)
    except:
        print("상세 본문 없음")

# -------------------------
# 신형 요약 영역
# -------------------------
def print_new_summary_posting(driver):
    print("\n[요약 영역]")
    try:
        guideline_box = driver.find_element(By.CSS_SELECTOR, "[data-sentry-component='RecruitmentGuidelines']")
        items = guideline_box.find_elements(By.CSS_SELECTOR, "[data-sentry-component='RecruitmentItem']")
        print("\n[모집요강]")
        for item in items:
            txt = clean_text(item.text)
            if txt:
                print("-", txt)
    except:
        print("모집요강 없음")

    try:
        qualification_box = driver.find_element(By.CSS_SELECTOR, "[data-sentry-component='Qualification']")
        q_items = qualification_box.find_elements(By.CSS_SELECTOR, "[data-sentry-component='QualificationItem']")
        print("\n[지원자격]")
        for item in q_items:
            txt = clean_text(item.text)
            if txt:
                print("-", txt)
    except:
        print("지원자격 없음")

    try:
        app_box = driver.find_element(By.CSS_SELECTOR, "#application-section")
        print("\n[접수기간 · 방법]")
        print(clean_text(app_box.text))
    except:
        print("접수기간 · 방법 없음")

# -------------------------
# 드라이버 세팅
# -------------------------
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--ignore-certificate-errors")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 10)

# -------------------------
# 리스트 페이지 순회
# -------------------------
base_url = "https://www.jobkorea.co.kr/recruit/joblist?menucode=local&localorder=1"
driver.get(base_url)
time.sleep(2)

# 등록일순
order_select = wait.until(EC.presence_of_element_located((By.ID, "orderTab")))
driver.execute_script("""
arguments[0].value = '2';
arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
""", order_select)
time.sleep(2)

# 총 페이지 수 확인
last_page_link = driver.find_elements(By.CSS_SELECTOR, "div#dvGIPaging ul li a")[-1]
total_pages = int(last_page_link.get_attribute("data-page"))

print("총 페이지 수:", total_pages)

for page_num in range(1, total_pages + 1):
    print("\n############################## 페이지", page_num, "##############################\n")
    driver.get(f"https://www.jobkorea.co.kr/recruit/_GI_List?Page={page_num}")
    time.sleep(2)

    items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.titBx")))

    links = []
    for item in items:
        try:
            link = item.find_element(By.CSS_SELECTOR, "strong a").get_attribute("href")
            if link.startswith("/"):
                link = "https://www.jobkorea.co.kr" + link
            links.append(link)
        except:
            continue

    for link in links:
        driver.get(link)
        time.sleep(2)
        print("\n" + "="*80)

        # 회사명 / 공고제목
        try:
            company = driver.find_element(By.CSS_SELECTOR, '[data-sentry-component="CompanyName"] h2').text
            print("회사:", clean_text(company))
        except:
            print("회사: 없음")

        try:
            title = driver.find_element(By.CSS_SELECTOR, '[data-sentry-component="TitleContent"] h1').text
            print("공고 제목:", clean_text(title))
        except:
            print("제목: 없음")

        # 상세/구형/이미지 문맥 이동
        move_to_best_job_content_context(driver)

        # 구형 텍스트
        old_check = driver.find_elements(By.CSS_SELECTOR, "div.artTplDetail.artRecruit")
        if old_check:
            print_old_template_posting(driver)

        # 신형 상세
        new_check = driver.find_elements(By.CSS_SELECTOR, ".detailed-summary-contents, #dev-template-v2-part")
        if new_check:
            print_new_detail_posting(driver)

        # 이미지 공고
        images = get_valid_detail_images(driver)
        if images:
            print("공고 유형: 이미지 공고")
            for img in images:
                print(img)

        # 요약 영역 항상 출력
        driver.switch_to.default_content()
        print_new_summary_posting(driver)

driver.quit()