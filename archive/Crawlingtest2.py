from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time


def clean_text(text):
    return " ".join(text.split()).strip() if text else ""


def move_to_best_job_content_context(driver):
    """
    우선순위
    1) iframe 안의 신형 상세 본문 (.detailed-summary-contents, #dev-template-v2-part)
    2) iframe 안의 구형 본문 (.artTplDetail, td.detailTable 등)
    3) 현재 페이지(default content)의 신형 상세 본문
    4) 현재 페이지(default content)의 구형/이미지 본문
    """
    driver.switch_to.default_content()

    iframes = driver.find_elements(By.TAG_NAME, "iframe")

    # 1) iframe 안의 신형 상세 본문 최우선
    for iframe in iframes:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)

            if driver.find_elements(
                By.CSS_SELECTOR,
                ".detailed-summary-contents, #dev-template-v2-part"
            ):
                return
        except:
            continue

    # 2) iframe 안의 구형 본문 / 이미지 본문
    for iframe in iframes:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)

            if driver.find_elements(
                By.CSS_SELECTOR,
                ".secDetailWrap, .artTplDetail, td.detailTable, .detailTable"
            ):
                return
        except:
            continue

    # 3) default content의 신형 상세 본문
    driver.switch_to.default_content()
    if driver.find_elements(
        By.CSS_SELECTOR,
        ".detailed-summary-contents, #dev-template-v2-part"
    ):
        return

    # 4) default content의 구형 / 이미지 본문
    if driver.find_elements(
        By.CSS_SELECTOR,
        ".secDetailWrap, .artTplDetail, td.detailTable, .detailTable"
    ):
        return

    driver.switch_to.default_content()


def get_valid_detail_images(driver):
    """
    공고 본문 안의 실제 상세 이미지 후보만 추림
    """
    valid_urls = []

    selectors = [
        "td.detailTable img",
        ".detailTable img",
        ".secDetailWrap td img",
    ]

    excluded_keywords = ["logo", "icon", "btn", "button", "로고", "아이콘", "버튼"]

    for selector in selectors:
        try:
            imgs = driver.find_elements(By.CSS_SELECTOR, selector)

            for img in imgs:
                try:
                    src = img.get_attribute("src")
                    alt = (img.get_attribute("alt") or "").strip().lower()

                    if not src:
                        continue

                    if src.startswith("data:image"):
                        continue

                    if any(keyword in alt for keyword in excluded_keywords):
                        continue

                    try:
                        width = img.size.get("width", 0)
                        height = img.size.get("height", 0)
                        if width < 250 or height < 250:
                            continue
                    except:
                        pass

                    if src not in valid_urls:
                        valid_urls.append(src)

                except:
                    continue
        except:
            continue

    return valid_urls


def print_old_template_posting(driver):
    rows = driver.find_elements(By.CSS_SELECTOR, "div.artTplDetail.artRecruit table tbody tr")

    print("공고 유형: 구형 텍스트 공고")

    try:
        company_desc = driver.find_element(By.CSS_SELECTOR, ".artTopDesc .desc").text
        print("\n[기업소개]")
        print(clean_text(company_desc))
    except:
        print("\n[기업소개] 없음")

    print("\n[모집분야 및 자격요건]")

    current_group = ""
    current_exp = ""

    for row in rows:
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue

            group_name = ""
            job_name = ""
            responsibilities = ""
            qualifications = ""
            exp_type = ""

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

            elif len(cells) == 3:
                group_name = current_group
                job_name = clean_text(cells[0].text)
                responsibilities = clean_text(cells[1].text)
                qualifications = clean_text(cells[2].text)
                exp_type = current_exp

            else:
                continue

            print("-" * 40)
            print("구분:", group_name if group_name else "없음")
            print("직무:", job_name if job_name else "없음")
            print("담당업무:", responsibilities if responsibilities else "없음")
            print("자격요건/우대사항:", qualifications if qualifications else "없음")
            print("신입/경력:", exp_type if exp_type else "없음")

        except Exception as e:
            print("행 파싱 실패:", e)

    try:
        common_section = driver.find_element(By.CSS_SELECTOR, ".artTplDetail.artRequire")
        common_items = common_section.find_elements(By.CSS_SELECTOR, "li")

        print("\n[공통자격 요건]")
        if common_items:
            for item in common_items:
                txt = clean_text(item.text)
                if txt:
                    print("-", txt)
        else:
            print("없음")
    except:
        print("\n[공통자격 요건] 없음")

    sections = driver.find_elements(By.CSS_SELECTOR, ".artTplDetail")
    for sec in sections:
        try:
            sec_title = clean_text(sec.find_element(By.CSS_SELECTOR, ".hd_3 .tit").text)

            if sec_title in ["안내사항", "기타사항", "접수방법"]:
                print(f"\n[{sec_title}]")
                li_list = sec.find_elements(By.CSS_SELECTOR, "li")

                if li_list:
                    for li in li_list:
                        txt = clean_text(li.text)
                        if txt:
                            print("-", txt)
                else:
                    print(clean_text(sec.text))
        except:
            continue

    try:
        steps = driver.find_elements(By.CSS_SELECTOR, ".detStep_list .step_name")
        print("\n[전형절차]")
        if steps:
            for idx, step in enumerate(steps, 1):
                txt = clean_text(step.text)
                if txt:
                    print(f"{idx}. {txt}")
        else:
            print("없음")
    except:
        print("\n[전형절차] 없음")

    try:
        apply_btn = driver.find_element(By.CSS_SELECTOR, "a.detBtnApply")
        apply_link = apply_btn.get_attribute("href")
        print("\n[지원 링크]")
        print(apply_link)
    except:
        print("\n[지원 링크] 없음")


def print_new_detail_posting(driver):
    print("공고 유형: 신형 텍스트 공고")
    print("\n[상세 본문]")

    print("\n[포지션 및 자격요건]")
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, "#dev-template-v2-part .dev-list-type tbody tr")

        if rows:
            for row in rows:
                try:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if len(tds) < 2:
                        continue

                    header_text = clean_text(tds[0].text)
                    body_text = clean_text(tds[1].text)

                    print("-" * 40)
                    print("모집영역:", header_text if header_text else "없음")
                    print(body_text if body_text else "내용 없음")

                except Exception as e:
                    print("상세 모집행 파싱 실패:", e)
        else:
            print("없음")

    except Exception as e:
        print("포지션 및 자격요건 파싱 실패:", e)

    try:
        sections = driver.find_elements(By.CSS_SELECTOR, ".detailed-summary-contents > .detailed-summary-content")

        for sec in sections:
            try:
                sec_id = sec.get_attribute("id") or ""
                if sec_id == "dev-template-v2-part":
                    continue

                heading_el = sec.find_element(By.CSS_SELECTOR, ".heading")
                heading_text = clean_text(heading_el.text)
                if not heading_text:
                    continue

                print(f"\n[{heading_text}]")

                lines = [clean_text(line) for line in sec.text.split("\n") if clean_text(line)]
                if lines and lines[0] == heading_text:
                    lines = lines[1:]

                if lines:
                    for line in lines:
                        print("-", line)
                else:
                    print("없음")

            except:
                continue

    except Exception as e:
        print("추가 상세 섹션 파싱 실패:", e)


def print_new_summary_posting(driver):
    print("[요약 영역]")

    print("\n[모집요강]")
    try:
        guideline_box = driver.find_element(By.CSS_SELECTOR, "[data-sentry-component='RecruitmentGuidelines']")

        try:
            field_boxes = guideline_box.find_elements(By.CSS_SELECTOR, "[data-sentry-component='RecruitmentField']")
            for field_box in field_boxes:
                txt = clean_text(field_box.text)
                if txt:
                    print(txt)
        except:
            pass

        try:
            items = guideline_box.find_elements(By.CSS_SELECTOR, "[data-sentry-component='RecruitmentItem']")
            for item in items:
                txt = clean_text(item.text)
                if txt:
                    print("-", txt)
        except:
            pass

    except:
        print("없음")

    print("\n[지원자격]")
    try:
        qualification_box = driver.find_element(By.CSS_SELECTOR, "[data-sentry-component='Qualification']")
        q_items = qualification_box.find_elements(By.CSS_SELECTOR, "[data-sentry-component='QualificationItem']")
        if q_items:
            for item in q_items:
                txt = clean_text(item.text)
                if txt:
                    print("-", txt)
        else:
            print(clean_text(qualification_box.text))
    except:
        print("없음")

    print("\n[접수기간 · 방법]")
    try:
        app_box = driver.find_element(By.CSS_SELECTOR, "#application-section")
        app_text = clean_text(app_box.text)
        if app_text:
            print(app_text)
        else:
            print("없음")
    except:
        print("없음")

    print("\n[기업 정보]")
    try:
        company_box = driver.find_element(By.CSS_SELECTOR, "#company-section")
        company_text = clean_text(company_box.text)
        if company_text:
            print(company_text)
        else:
            print("없음")
    except:
        print("없음")


# Chrome 옵션 설정
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--ignore-certificate-errors")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 10)

driver.get("https://www.jobkorea.co.kr/recruit/joblist?menucode=local&localorder=1")
time.sleep(3)

order_select = wait.until(EC.presence_of_element_located((By.ID, "orderTab")))
driver.execute_script("""
arguments[0].value = '2';
arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
""", order_select)

wait.until(lambda d: d.find_element(By.ID, "orderTab").get_attribute("value") == "2")
time.sleep(2)

print("현재 정렬값:", driver.find_element(By.ID, "orderTab").get_attribute("value"))

target_count = 4
links = []

items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.titBx")))

for item in items:
    if len(links) >= target_count:
        break

    try:
        link = item.find_element(By.CSS_SELECTOR, "strong a").get_attribute("href")

        if link.startswith("/"):
            link = "https://www.jobkorea.co.kr" + link

        if link not in links:
            links.append(link)

    except Exception as e:
        print("링크 추출 실패:", e)
        continue


for link in links:
    driver.get(link)
    time.sleep(2)

    print("\n" + "=" * 80)

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

    # 1) 상세/구형/이미지 쪽 문맥으로 이동
    move_to_best_job_content_context(driver)

    # 현재 문맥 기준 체크
    old_template_check = driver.find_elements(By.CSS_SELECTOR, "div.artTplDetail.artRecruit")
    old_rows = driver.find_elements(By.CSS_SELECTOR, "div.artTplDetail.artRecruit table tbody tr")

    new_detail_check = driver.find_elements(
        By.CSS_SELECTOR,
        ".detailed-summary-contents, #dev-template-v2-part"
    )

    valid_image_urls = get_valid_detail_images(driver)

    printed_main = False

    # 2) 구형 텍스트 공고
    if old_template_check and old_rows:
        print_old_template_posting(driver)
        printed_main = True

    # 3) 신형 상세 본문
    elif new_detail_check:
        print_new_detail_posting(driver)
        printed_main = True

    # 4) 이미지 공고
    elif valid_image_urls:
        print("공고 유형: 이미지 공고")
        print("\n[공고 이미지 URL]")
        for img_url in valid_image_urls:
            print(img_url)
        printed_main = True

    # 5) 요약 영역은 반드시 default content에서 따로 검사
    driver.switch_to.default_content()

    new_summary_check = driver.find_elements(
        By.CSS_SELECTOR,
        "[data-sentry-component='RecruitmentGuidelines'], "
        "[data-sentry-component='Qualification'], "
        "#application-section, "
        "#company-section"
    )

    if new_summary_check:
        print()
        print("=" * 20 + " 요약 영역 " + "=" * 20)
        print_new_summary_posting(driver)

    # 6) 메인도 없고 요약도 없으면 패스
    if not printed_main and not new_summary_check:
        continue

driver.quit()