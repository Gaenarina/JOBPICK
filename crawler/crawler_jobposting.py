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


def extract_old_template_posting(driver):
    rows = driver.find_elements(By.CSS_SELECTOR, "div.artTplDetail.artRecruit table tbody tr")

    result = {
        "posting_type": "old_text",
        "company_desc": "",
        "positions": [],
        "common_requirements": [],
        "extra_sections": {},
        "hiring_steps": [],
        "apply_link": ""
    }

    try:
        company_desc = driver.find_element(By.CSS_SELECTOR, ".artTopDesc .desc").text
        result["company_desc"] = clean_text(company_desc)
    except:
        pass

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

            result["positions"].append({
                "group": group_name if group_name else "없음",
                "job_name": job_name if job_name else "없음",
                "responsibilities": responsibilities if responsibilities else "없음",
                "qualifications": qualifications if qualifications else "없음",
                "experience_type": exp_type if exp_type else "없음"
            })

        except:
            continue

    try:
        common_section = driver.find_element(By.CSS_SELECTOR, ".artTplDetail.artRequire")
        common_items = common_section.find_elements(By.CSS_SELECTOR, "li")

        for item in common_items:
            txt = clean_text(item.text)
            if txt:
                result["common_requirements"].append(txt)
    except:
        pass

    sections = driver.find_elements(By.CSS_SELECTOR, ".artTplDetail")
    for sec in sections:
        try:
            sec_title = clean_text(sec.find_element(By.CSS_SELECTOR, ".hd_3 .tit").text)

            if sec_title in ["안내사항", "기타사항", "접수방법"]:
                li_list = sec.find_elements(By.CSS_SELECTOR, "li")
                temp_list = []

                if li_list:
                    for li in li_list:
                        txt = clean_text(li.text)
                        if txt:
                            temp_list.append(txt)
                else:
                    full_text = clean_text(sec.text)
                    if full_text:
                        temp_list.append(full_text)

                result["extra_sections"][sec_title] = temp_list
        except:
            continue

    try:
        steps = driver.find_elements(By.CSS_SELECTOR, ".detStep_list .step_name")
        for step in steps:
            txt = clean_text(step.text)
            if txt:
                result["hiring_steps"].append(txt)
    except:
        pass

    try:
        apply_btn = driver.find_element(By.CSS_SELECTOR, "a.detBtnApply")
        apply_link = apply_btn.get_attribute("href")
        result["apply_link"] = apply_link
    except:
        pass

    return result


def extract_new_detail_posting(driver):
    result = {
        "posting_type": "new_text",
        "positions": [],
        "sections": {}
    }

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

                    result["positions"].append({
                        "header": header_text if header_text else "없음",
                        "body": body_text if body_text else "내용 없음"
                    })

                except:
                    continue

    except:
        pass

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

                lines = [clean_text(line) for line in sec.text.split("\n") if clean_text(line)]
                if lines and lines[0] == heading_text:
                    lines = lines[1:]

                result["sections"][heading_text] = lines if lines else ["없음"]

            except:
                continue

    except:
        pass

    return result


def extract_new_summary_posting(driver):
    result = {
        "guidelines": [],
        "qualifications": [],
        "application": "",
        "company_info": "",
    }

    try:
        guideline_box = driver.find_element(By.CSS_SELECTOR, "[data-sentry-component='RecruitmentGuidelines']")

        try:
            field_boxes = guideline_box.find_elements(By.CSS_SELECTOR, "[data-sentry-component='RecruitmentField']")
            for field_box in field_boxes:
                txt = clean_text(field_box.text)
                if txt:
                    result["guidelines"].append(txt)
        except:
            pass

        try:
            items = guideline_box.find_elements(By.CSS_SELECTOR, "[data-sentry-component='RecruitmentItem']")
            for item in items:
                txt = clean_text(item.text)
                if txt:
                    result["guidelines"].append(txt)
        except:
            pass

    except:
        pass

    try:
        qualification_box = driver.find_element(By.CSS_SELECTOR, "[data-sentry-component='Qualification']")
        q_items = qualification_box.find_elements(By.CSS_SELECTOR, "[data-sentry-component='QualificationItem']")
        if q_items:
            for item in q_items:
                txt = clean_text(item.text)
                if txt:
                    result["qualifications"].append(txt)
        else:
            txt = clean_text(qualification_box.text)
            if txt:
                result["qualifications"].append(txt)
    except:
        pass

    try:
        app_box = driver.find_element(By.CSS_SELECTOR, "#application-section")
        app_text = clean_text(app_box.text)
        result["application"] = app_text
    except:
        pass

    try:
        company_box = driver.find_element(By.CSS_SELECTOR, "#company-section")
        company_text = clean_text(company_box.text)
        result["company_info"] = company_text
    except:
        pass

    return result


class JobKoreaCrawler:
    def __init__(self, headless=True):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--ignore-certificate-errors")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

    def close(self):
        self.driver.quit()

    def get_job_links(self, target_count=4):
        driver = self.driver
        wait = self.wait

        driver.get("https://www.jobkorea.co.kr/recruit/joblist?menucode=local&localorder=1")
        time.sleep(3)

        order_select = wait.until(EC.presence_of_element_located((By.ID, "orderTab")))
        driver.execute_script("""
        arguments[0].value = '2';
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        """, order_select)

        wait.until(lambda d: d.find_element(By.ID, "orderTab").get_attribute("value") == "2")
        time.sleep(2)

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

            except:
                continue

        return links

    def crawl_posting(self, link):
        driver = self.driver

        driver.get(link)
        time.sleep(2)

        result = {
            "url": link,
            "company": "",
            "title": "",
            "main": None,
            "summary": None,
            "image_urls": []
        }

        try:
            company = driver.find_element(By.CSS_SELECTOR, '[data-sentry-component="CompanyName"] h2').text
            result["company"] = clean_text(company)
        except:
            pass

        try:
            title = driver.find_element(By.CSS_SELECTOR, '[data-sentry-component="TitleContent"] h1').text
            result["title"] = clean_text(title)
        except:
            pass

        move_to_best_job_content_context(driver)

        old_template_check = driver.find_elements(By.CSS_SELECTOR, "div.artTplDetail.artRecruit")
        old_rows = driver.find_elements(By.CSS_SELECTOR, "div.artTplDetail.artRecruit table tbody tr")

        new_detail_check = driver.find_elements(
            By.CSS_SELECTOR,
            ".detailed-summary-contents, #dev-template-v2-part"
        )

        valid_image_urls = get_valid_detail_images(driver)
        result["image_urls"] = valid_image_urls

        if old_template_check and old_rows:
            result["main"] = extract_old_template_posting(driver)

        elif new_detail_check:
            result["main"] = extract_new_detail_posting(driver)

        elif valid_image_urls:
            result["main"] = {
                "posting_type": "image",
                "image_urls": valid_image_urls
            }

        driver.switch_to.default_content()

        new_summary_check = driver.find_elements(
            By.CSS_SELECTOR,
            "[data-sentry-component='RecruitmentGuidelines'], "
            "[data-sentry-component='Qualification'], "
            "#application-section, "
            "#company-section"
        )

        if new_summary_check:
            result["summary"] = extract_new_summary_posting(driver)

        return result

    def crawl_multiple_postings(self, target_count=4):
        links = self.get_job_links(target_count=target_count)
        results = []

        for link in links:
            try:
                posting = self.crawl_posting(link)
                results.append(posting)
            except Exception as e:
                results.append({
                    "url": link,
                    "error": str(e)
                })

        return results