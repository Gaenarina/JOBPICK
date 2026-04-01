from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import io
from contextlib import redirect_stdout


class JobKoreaCrawler:
    def __init__(self, headless=True):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--ignore-certificate-errors")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)

    def close(self):
        self.driver.quit()

    def clean_text(self, text):
        return " ".join(text.split()).strip() if text else ""

    def capture_print_output(self, func):
        buffer = io.StringIO()
        try:
            with redirect_stdout(buffer):
                func()
        except Exception as e:
            return "", str(e)
        return buffer.getvalue().strip(), None

    def build_raw_crawled_text(self, company, title, url, posting_type, detail_text="", summary_text="", image_urls=None):
        if image_urls is None:
            image_urls = []

        lines = []
        lines.append(f"회사: {company}")
        lines.append(f"공고 제목: {title}")
        lines.append(f"공고 링크: {url}")

        if posting_type == "old_text":
            lines.append("공고 유형: 구형 텍스트 공고")
        elif posting_type == "new_text":
            lines.append("공고 유형: 신형 텍스트 공고")
        elif posting_type == "image":
            lines.append("공고 유형: 이미지 공고")
        else:
            lines.append(f"공고 유형: {posting_type}")

        if detail_text:
            lines.append("")
            lines.append(detail_text)

        if image_urls:
            lines.append("")
            lines.append("[공고 이미지 URL]")
            for image_url in image_urls:
                lines.append(image_url)

        if summary_text:
            lines.append("")
            lines.append(summary_text)

        return "\n".join(lines).strip()

    def move_to_best_job_content_context(self):
        self.driver.switch_to.default_content()
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")

        for iframe in iframes:
            try:
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame(iframe)
                if self.driver.find_elements(By.CSS_SELECTOR, ".detailed-summary-contents, #dev-template-v2-part"):
                    return
            except:
                continue

        for iframe in iframes:
            try:
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame(iframe)
                if self.driver.find_elements(By.CSS_SELECTOR, ".secDetailWrap, .artTplDetail, td.detailTable, .detailTable"):
                    return
            except:
                continue

        self.driver.switch_to.default_content()
        if self.driver.find_elements(By.CSS_SELECTOR, ".detailed-summary-contents, #dev-template-v2-part"):
            return

        if self.driver.find_elements(By.CSS_SELECTOR, ".secDetailWrap, .artTplDetail, td.detailTable, .detailTable"):
            return

        self.driver.switch_to.default_content()

    def get_valid_detail_images(self):
        valid_urls = []
        selectors = [
            "td.detailTable img",
            ".detailTable img",
            ".secDetailWrap td img",
        ]
        excluded_keywords = ["logo", "icon", "btn", "button", "로고", "아이콘", "버튼"]

        for selector in selectors:
            try:
                imgs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for img in imgs:
                    try:
                        src = img.get_attribute("src")
                        alt = (img.get_attribute("alt") or "").strip().lower()

                        if not src or src.startswith("data:image"):
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

    # -----------------------------
    # 구형 텍스트 공고 파싱
    # -----------------------------
    def extract_old_template_posting(self):
        rows = self.driver.find_elements(By.CSS_SELECTOR, "div.artTplDetail.artRecruit table tbody tr")

        company_desc = ""
        try:
            company_desc = self.clean_text(
                self.driver.find_element(By.CSS_SELECTOR, ".artTopDesc .desc").text
            )
        except:
            company_desc = ""

        positions = []
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
                    current_group = self.clean_text(cells[0].text)
                    group_name = current_group
                    job_name = self.clean_text(cells[1].text)
                    responsibilities = self.clean_text(cells[2].text)
                    qualifications = self.clean_text(cells[3].text)
                    current_exp = self.clean_text(cells[4].text)
                    exp_type = current_exp

                elif len(cells) == 4:
                    group_name = current_group
                    job_name = self.clean_text(cells[0].text)
                    responsibilities = self.clean_text(cells[1].text)
                    qualifications = self.clean_text(cells[2].text)
                    exp_text = self.clean_text(cells[3].text)
                    if exp_text:
                        current_exp = exp_text
                    exp_type = current_exp

                elif len(cells) == 3:
                    group_name = current_group
                    job_name = self.clean_text(cells[0].text)
                    responsibilities = self.clean_text(cells[1].text)
                    qualifications = self.clean_text(cells[2].text)
                    exp_type = current_exp

                else:
                    continue

                positions.append({
                    "group": group_name,
                    "job_name": job_name,
                    "responsibilities": responsibilities,
                    "qualifications": qualifications,
                    "experience_type": exp_type,
                })

            except:
                continue

        common_requirements = []
        try:
            common_section = self.driver.find_element(By.CSS_SELECTOR, ".artTplDetail.artRequire")
            common_items = common_section.find_elements(By.CSS_SELECTOR, "li")
            for item in common_items:
                txt = self.clean_text(item.text)
                if txt:
                    common_requirements.append(txt)
        except:
            pass

        extra_sections = {}
        sections = self.driver.find_elements(By.CSS_SELECTOR, ".artTplDetail")
        for sec in sections:
            try:
                sec_title = self.clean_text(sec.find_element(By.CSS_SELECTOR, ".hd_3 .tit").text)
                if sec_title in ["안내사항", "기타사항", "접수방법"]:
                    li_list = sec.find_elements(By.CSS_SELECTOR, "li")
                    section_lines = []
                    if li_list:
                        for li in li_list:
                            txt = self.clean_text(li.text)
                            if txt:
                                section_lines.append(txt)
                    else:
                        txt = self.clean_text(sec.text)
                        if txt:
                            section_lines.append(txt)

                    extra_sections[sec_title] = section_lines
            except:
                continue

        hiring_steps = []
        try:
            steps = self.driver.find_elements(By.CSS_SELECTOR, ".detStep_list .step_name")
            for step in steps:
                txt = self.clean_text(step.text)
                if txt:
                    hiring_steps.append(txt)
        except:
            pass

        apply_link = ""
        try:
            apply_btn = self.driver.find_element(By.CSS_SELECTOR, "a.detBtnApply")
            apply_link = apply_btn.get_attribute("href") or ""
        except:
            apply_link = ""

        detail_text, _ = self.capture_print_output(self.print_old_template_posting)

        return {
            "posting_type": "old_text",
            "company_desc": company_desc,
            "positions": positions,
            "common_requirements": common_requirements,
            "extra_sections": extra_sections,
            "hiring_steps": hiring_steps,
            "apply_link": apply_link,
            "detail_text": detail_text,
        }

    def print_old_template_posting(self):
        rows = self.driver.find_elements(By.CSS_SELECTOR, "div.artTplDetail.artRecruit table tbody tr")

        print("공고 유형: 구형 텍스트 공고")

        try:
            company_desc = self.driver.find_element(By.CSS_SELECTOR, ".artTopDesc .desc").text
            print("\n[기업소개]")
            print(self.clean_text(company_desc))
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
                    current_group = self.clean_text(cells[0].text)
                    group_name = current_group
                    job_name = self.clean_text(cells[1].text)
                    responsibilities = self.clean_text(cells[2].text)
                    qualifications = self.clean_text(cells[3].text)
                    current_exp = self.clean_text(cells[4].text)
                    exp_type = current_exp

                elif len(cells) == 4:
                    group_name = current_group
                    job_name = self.clean_text(cells[0].text)
                    responsibilities = self.clean_text(cells[1].text)
                    qualifications = self.clean_text(cells[2].text)
                    exp_text = self.clean_text(cells[3].text)
                    if exp_text:
                        current_exp = exp_text
                    exp_type = current_exp

                elif len(cells) == 3:
                    group_name = current_group
                    job_name = self.clean_text(cells[0].text)
                    responsibilities = self.clean_text(cells[1].text)
                    qualifications = self.clean_text(cells[2].text)
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
            common_section = self.driver.find_element(By.CSS_SELECTOR, ".artTplDetail.artRequire")
            common_items = common_section.find_elements(By.CSS_SELECTOR, "li")

            print("\n[공통자격 요건]")
            if common_items:
                for item in common_items:
                    txt = self.clean_text(item.text)
                    if txt:
                        print("-", txt)
            else:
                print("없음")
        except:
            print("\n[공통자격 요건] 없음")

        sections = self.driver.find_elements(By.CSS_SELECTOR, ".artTplDetail")
        for sec in sections:
            try:
                sec_title = self.clean_text(sec.find_element(By.CSS_SELECTOR, ".hd_3 .tit").text)
                if sec_title in ["안내사항", "기타사항", "접수방법"]:
                    print(f"\n[{sec_title}]")
                    li_list = sec.find_elements(By.CSS_SELECTOR, "li")
                    if li_list:
                        for li in li_list:
                            txt = self.clean_text(li.text)
                            if txt:
                                print("-", txt)
                    else:
                        print(self.clean_text(sec.text))
            except:
                continue

        try:
            steps = self.driver.find_elements(By.CSS_SELECTOR, ".detStep_list .step_name")
            print("\n[전형절차]")
            if steps:
                for idx, step in enumerate(steps, 1):
                    txt = self.clean_text(step.text)
                    if txt:
                        print(f"{idx}. {txt}")
            else:
                print("없음")
        except:
            print("\n[전형절차] 없음")

        try:
            apply_btn = self.driver.find_element(By.CSS_SELECTOR, "a.detBtnApply")
            apply_link = apply_btn.get_attribute("href")
            print("\n[지원 링크]")
            print(apply_link)
        except:
            print("\n[지원 링크] 없음")

    # -----------------------------
    # 신형 텍스트 공고 파싱
    # -----------------------------
    def extract_new_text_posting(self):
        positions = []
        try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, "#dev-template-v2-part .dev-list-type tbody tr")
            for row in rows:
                try:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if len(tds) < 2:
                        continue

                    header_text = self.clean_text(tds[0].text)
                    body_text = self.clean_text(tds[1].text)

                    positions.append({
                        "header": header_text,
                        "body": body_text,
                    })
                except:
                    continue
        except:
            pass

        sections = {}
        try:
            sec_elements = self.driver.find_elements(By.CSS_SELECTOR, ".detailed-summary-contents > .detailed-summary-content")
            for sec in sec_elements:
                try:
                    sec_id = sec.get_attribute("id") or ""
                    if sec_id == "dev-template-v2-part":
                        continue

                    heading_el = sec.find_element(By.CSS_SELECTOR, ".heading")
                    heading_text = self.clean_text(heading_el.text)
                    if not heading_text:
                        continue

                    lines = [self.clean_text(line) for line in sec.text.split("\n") if self.clean_text(line)]
                    if lines and lines[0] == heading_text:
                        lines = lines[1:]

                    sections[heading_text] = lines
                except:
                    continue
        except:
            pass

        detail_text, _ = self.capture_print_output(self.print_new_detail_posting)

        return {
            "posting_type": "new_text",
            "positions": positions,
            "sections": sections,
            "detail_text": detail_text,
        }

    def print_new_detail_posting(self):
        print("공고 유형: 신형 텍스트 공고")
        print("\n[상세 본문]")

        print("\n[포지션 및 자격요건]")
        try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, "#dev-template-v2-part .dev-list-type tbody tr")
            if rows:
                for row in rows:
                    try:
                        tds = row.find_elements(By.TAG_NAME, "td")
                        if len(tds) < 2:
                            continue

                        header_text = self.clean_text(tds[0].text)
                        body_text = self.clean_text(tds[1].text)

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
            sections = self.driver.find_elements(By.CSS_SELECTOR, ".detailed-summary-contents > .detailed-summary-content")
            for sec in sections:
                try:
                    sec_id = sec.get_attribute("id") or ""
                    if sec_id == "dev-template-v2-part":
                        continue

                    heading_el = sec.find_element(By.CSS_SELECTOR, ".heading")
                    heading_text = self.clean_text(heading_el.text)
                    if not heading_text:
                        continue

                    print(f"\n[{heading_text}]")

                    lines = [self.clean_text(line) for line in sec.text.split("\n") if self.clean_text(line)]
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

    # -----------------------------
    # 요약 영역 파싱
    # -----------------------------
    def extract_summary_posting(self):
        guidelines = []
        qualifications = []
        application = ""
        company_info = ""

        try:
            guideline_box = self.driver.find_element(By.CSS_SELECTOR, "[data-sentry-component='RecruitmentGuidelines']")
            field_boxes = guideline_box.find_elements(By.CSS_SELECTOR, "[data-sentry-component='RecruitmentField']")
            for field_box in field_boxes:
                txt = self.clean_text(field_box.text)
                if txt:
                    guidelines.append(txt)

            items = guideline_box.find_elements(By.CSS_SELECTOR, "[data-sentry-component='RecruitmentItem']")
            for item in items:
                txt = self.clean_text(item.text)
                if txt:
                    guidelines.append(txt)
        except:
            pass

        try:
            qualification_box = self.driver.find_element(By.CSS_SELECTOR, "[data-sentry-component='Qualification']")
            q_items = qualification_box.find_elements(By.CSS_SELECTOR, "[data-sentry-component='QualificationItem']")
            if q_items:
                for item in q_items:
                    txt = self.clean_text(item.text)
                    if txt:
                        qualifications.append(txt)
            else:
                txt = self.clean_text(qualification_box.text)
                if txt:
                    qualifications.append(txt)
        except:
            pass

        try:
            app_box = self.driver.find_element(By.CSS_SELECTOR, "#application-section")
            application = self.clean_text(app_box.text)
        except:
            application = ""

        try:
            company_box = self.driver.find_element(By.CSS_SELECTOR, "#company-section")
            company_info = self.clean_text(company_box.text)
        except:
            company_info = ""

        summary_text, _ = self.capture_print_output(self.print_new_summary_posting)

        return {
            "guidelines": guidelines,
            "qualifications": qualifications,
            "application": application,
            "company_info": company_info,
            "raw_summary_text": summary_text,
        }

    def print_new_summary_posting(self):
        print("[요약 영역]")

        print("\n[모집요강]")
        try:
            guideline_box = self.driver.find_element(By.CSS_SELECTOR, "[data-sentry-component='RecruitmentGuidelines']")
            try:
                field_boxes = guideline_box.find_elements(By.CSS_SELECTOR, "[data-sentry-component='RecruitmentField']")
                for field_box in field_boxes:
                    txt = self.clean_text(field_box.text)
                    if txt:
                        print(txt)
            except:
                pass

            try:
                items = guideline_box.find_elements(By.CSS_SELECTOR, "[data-sentry-component='RecruitmentItem']")
                for item in items:
                    txt = self.clean_text(item.text)
                    if txt:
                        print("-", txt)
            except:
                pass
        except:
            print("없음")

        print("\n[지원자격]")
        try:
            qualification_box = self.driver.find_element(By.CSS_SELECTOR, "[data-sentry-component='Qualification']")
            q_items = qualification_box.find_elements(By.CSS_SELECTOR, "[data-sentry-component='QualificationItem']")
            if q_items:
                for item in q_items:
                    txt = self.clean_text(item.text)
                    if txt:
                        print("-", txt)
            else:
                print(self.clean_text(qualification_box.text))
        except:
            print("없음")

        print("\n[접수기간 · 방법]")
        try:
            app_box = self.driver.find_element(By.CSS_SELECTOR, "#application-section")
            app_text = self.clean_text(app_box.text)
            print(app_text if app_text else "없음")
        except:
            print("없음")

        print("\n[기업 정보]")
        try:
            company_box = self.driver.find_element(By.CSS_SELECTOR, "#company-section")
            company_text = self.clean_text(company_box.text)
            print(company_text if company_text else "없음")
        except:
            print("없음")

    # -----------------------------
    # 목록 수집
    # -----------------------------
    def go_to_job_list_latest(self):
        self.driver.get("https://www.jobkorea.co.kr/recruit/joblist?menucode=local&localorder=1")
        time.sleep(3)

        order_select = self.wait.until(EC.presence_of_element_located((By.ID, "orderTab")))
        self.driver.execute_script("""
        arguments[0].value = '2';
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        """, order_select)

        self.wait.until(lambda d: d.find_element(By.ID, "orderTab").get_attribute("value") == "2")
        self.wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "#dev-gi-list tr.devloopArea")) > 0)
        time.sleep(2)

    def collect_one_page_links_skip_duplicates(self, existing_links=None, max_count=40):
        if existing_links is None:
            existing_links = set()

        links = []
        seen_links = set()

        self.go_to_job_list_latest()

        job_rows = self.driver.find_elements(By.CSS_SELECTOR, "#dev-gi-list tr.devloopArea")

        for row in job_rows:
            if len(links) >= max_count:
                break

            try:
                a_tag = row.find_element(By.CSS_SELECTOR, "strong a")
                link = a_tag.get_attribute("href")

                if link.startswith("/"):
                    link = "https://www.jobkorea.co.kr" + link

                if not link:
                    continue

                if link in existing_links:
                    print(f"중복 링크 건너뜀: {link}")
                    continue

                if link not in seen_links:
                    seen_links.add(link)
                    links.append(link)

            except:
                continue

        return links

    # -----------------------------
    # 공고 1개 크롤링
    # -----------------------------
    def crawl_single_posting(self, link):
        self.driver.get(link)
        time.sleep(2)

        try:
            company = self.driver.find_element(By.CSS_SELECTOR, '[data-sentry-component="CompanyName"] h2').text
            company = self.clean_text(company)
        except:
            company = ""

        try:
            title = self.driver.find_element(By.CSS_SELECTOR, '[data-sentry-component="TitleContent"] h1').text
            title = self.clean_text(title)
        except:
            title = ""

        print("\n" + "=" * 80)
        print("회사:", company)
        print("공고 제목:", title)
        print("공고 링크:", link)

        self.move_to_best_job_content_context()

        old_template_check = self.driver.find_elements(By.CSS_SELECTOR, "div.artTplDetail.artRecruit")
        old_rows = self.driver.find_elements(By.CSS_SELECTOR, "div.artTplDetail.artRecruit table tbody tr")
        new_detail_check = self.driver.find_elements(By.CSS_SELECTOR, ".detailed-summary-contents, #dev-template-v2-part")
        valid_image_urls = self.get_valid_detail_images()

        main_data = {}
        if old_template_check and old_rows:
            main_data = self.extract_old_template_posting()
            image_urls = []
        elif new_detail_check:
            main_data = self.extract_new_text_posting()
            image_urls = []
        elif valid_image_urls:
            main_data = {
                "posting_type": "image",
                "image_urls": valid_image_urls,
                "detail_text": "",
            }
            image_urls = valid_image_urls
        else:
            main_data = {
                "posting_type": "unknown",
                "detail_text": "",
            }
            image_urls = []

        self.driver.switch_to.default_content()

        summary_data = self.extract_summary_posting()

        raw_crawled_text = self.build_raw_crawled_text(
            company=company,
            title=title,
            url=link,
            posting_type=main_data.get("posting_type", "unknown"),
            detail_text=main_data.get("detail_text", ""),
            summary_text=summary_data.get("raw_summary_text", ""),
            image_urls=image_urls
        )

        main_data["raw_crawled_text"] = raw_crawled_text
        if image_urls:
            main_data["image_urls"] = image_urls

        return {
            "url": link,
            "company": company,
            "title": title,
            "main": main_data,
            "summary": summary_data,
        }

    # -----------------------------
    # 여러 공고 크롤링
    # -----------------------------
    def crawl_multiple_postings(self, target_count=4, existing_links=None):
        links = self.collect_one_page_links_skip_duplicates(
            existing_links=existing_links,
            max_count=target_count
        )

        postings = []
        for link in links:
            posting = self.crawl_single_posting(link)
            postings.append(posting)

        return postings