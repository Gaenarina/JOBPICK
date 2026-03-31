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


def clean_text(text):
    return " ".join(text.split()).strip() if text else ""


def move_to_best_job_content_context(driver):
    driver.switch_to.default_content()
    iframes = driver.find_elements(By.TAG_NAME, "iframe")

    for iframe in iframes:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)
            if driver.find_elements(By.CSS_SELECTOR, ".detailed-summary-contents, #dev-template-v2-part"):
                return
        except:
            continue

    for iframe in iframes:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)
            if driver.find_elements(By.CSS_SELECTOR, ".secDetailWrap, .artTplDetail, td.detailTable, .detailTable"):
                return
        except:
            continue

    driver.switch_to.default_content()
    if driver.find_elements(By.CSS_SELECTOR, ".detailed-summary-contents, #dev-template-v2-part"):
        return

    if driver.find_elements(By.CSS_SELECTOR, ".secDetailWrap, .artTplDetail, td.detailTable, .detailTable"):
        return

    driver.switch_to.default_content()


def get_valid_detail_images(driver):
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
        print(app_text if app_text else "없음")
    except:
        print("없음")

    print("\n[기업 정보]")
    try:
        company_box = driver.find_element(By.CSS_SELECTOR, "#company-section")
        company_text = clean_text(company_box.text)
        print(company_text if company_text else "없음")
    except:
        print("없음")


def collect_links_from_current_page(driver, seen_links, all_links, max_count=200):
    job_rows = driver.find_elements(By.CSS_SELECTOR, "#dev-gi-list tr.devloopArea")

    for row in job_rows:
        if len(all_links) >= max_count:
            return

        try:
            a_tag = row.find_element(By.CSS_SELECTOR, "strong a")
            link = a_tag.get_attribute("href")

            if link.startswith("/"):
                link = "https://www.jobkorea.co.kr" + link

            if link and link not in seen_links:
                seen_links.add(link)
                all_links.append(link)
        except:
            continue


def capture_print_output(func, driver):
    buffer = io.StringIO()
    try:
        with redirect_stdout(buffer):
            func(driver)
    except Exception as e:
        return "", str(e)
    return buffer.getvalue().strip(), None


def go_to_job_list_latest(driver, wait):
    driver.get("https://www.jobkorea.co.kr/recruit/joblist?menucode=local&localorder=1")
    time.sleep(3)

    order_select = wait.until(EC.presence_of_element_located((By.ID, "orderTab")))
    driver.execute_script("""
    arguments[0].value = '2';
    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
    """, order_select)

    wait.until(lambda d: d.find_element(By.ID, "orderTab").get_attribute("value") == "2")
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "#dev-gi-list tr.devloopArea")) > 0)
    time.sleep(2)


def move_to_page(driver, wait, page):
    old_first_title = ""
    old_rows = driver.find_elements(By.CSS_SELECTOR, "#dev-gi-list tr.devloopArea")
    if old_rows:
        old_first_title = old_rows[0].find_element(By.CSS_SELECTOR, "strong a").text.strip()

    page_btn = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, f"a[data-page='{page}']"))
    )
    driver.execute_script("arguments[0].click();", page_btn)

    wait.until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "#dev-gi-list tr.devloopArea")) > 0
        and d.find_elements(By.CSS_SELECTOR, "#dev-gi-list tr.devloopArea")[0]
        .find_element(By.CSS_SELECTOR, "strong a").text.strip() != old_first_title
    )
    time.sleep(2)


def collect_initial_links(driver, wait, max_count=200, max_pages=100):
    links = []
    seen_links = set()

    go_to_job_list_latest(driver, wait)

    for page in range(1, max_pages + 1):
        if page > 1:
            try:
                move_to_page(driver, wait, page)
            except Exception as e:
                print(f"{page}페이지 이동 실패: {e}")
                break

        collect_links_from_current_page(driver, seen_links, links, max_count=max_count)

        if len(links) >= max_count:
            break

    return links[:max_count]


def collect_new_links_until_duplicate(driver, wait, existing_links, max_pages=100):
    new_links = []
    seen_this_run = set()

    go_to_job_list_latest(driver, wait)

    for page in range(1, max_pages + 1):
        if page > 1:
            try:
                move_to_page(driver, wait, page)
            except Exception as e:
                print(f"{page}페이지 이동 실패: {e}")
                break

        job_rows = driver.find_elements(By.CSS_SELECTOR, "#dev-gi-list tr.devloopArea")

        for row in job_rows:
            try:
                a_tag = row.find_element(By.CSS_SELECTOR, "strong a")
                link = a_tag.get_attribute("href")

                if link.startswith("/"):
                    link = "https://www.jobkorea.co.kr" + link

                if not link:
                    continue

                if link in existing_links:
                    print(f"기존 공고 발견 → 수집 중단: {link}")
                    return new_links

                if link not in seen_this_run:
                    seen_this_run.add(link)
                    new_links.append(link)

            except:
                continue

    return new_links


def is_closed_posting(driver):
    try:
        page_text = driver.page_source.lower()
    except:
        return False

    closed_keywords = [
        "접수마감",
        "채용마감",
        "마감된 공고",
        "모집마감",
        "공고마감",
        "expired",
        "closed"
    ]

    return any(keyword.lower() in page_text for keyword in closed_keywords)


def find_expired_links(driver, saved_links):
    expired_links = []

    for idx, link in enumerate(saved_links, 1):
        try:
            driver.get(link)
            time.sleep(2)

            if is_closed_posting(driver):
                expired_links.append(link)
                print(f"[만료 공고] {idx}. {link}")
            else:
                print(f"[유효 공고] {idx}. {link}")

        except Exception as e:
            print(f"만료 확인 실패: {link} / {e}")

    return expired_links


def crawl_and_collect_postings(driver, links, limit=None):
    target_links = links if limit is None else links[:limit]
    collected_postings = []

    for idx, link in enumerate(target_links, 1):
        driver.get(link)
        time.sleep(2)

        try:
            company = driver.find_element(By.CSS_SELECTOR, '[data-sentry-component="CompanyName"] h2').text
            company = clean_text(company)
        except:
            company = "없음"

        try:
            title = driver.find_element(By.CSS_SELECTOR, '[data-sentry-component="TitleContent"] h1').text
            title = clean_text(title)
        except:
            title = "없음"

        print("\n" + "=" * 80)
        print(f"{idx}. {link}")
        print("회사:", company)
        print("공고 제목:", title)

        move_to_best_job_content_context(driver)

        old_template_check = driver.find_elements(By.CSS_SELECTOR, "div.artTplDetail.artRecruit")
        old_rows = driver.find_elements(By.CSS_SELECTOR, "div.artTplDetail.artRecruit table tbody tr")

        new_detail_check = driver.find_elements(
            By.CSS_SELECTOR,
            ".detailed-summary-contents, #dev-template-v2-part"
        )

        valid_image_urls = get_valid_detail_images(driver)

        posting_type = "unknown"
        detail_text = ""
        summary_text = ""
        image_urls = []

        if old_template_check and old_rows:
            posting_type = "old_text"
            detail_text, error = capture_print_output(print_old_template_posting, driver)
            if error:
                print("상세 본문 캡처 실패:", error)

        elif new_detail_check:
            posting_type = "new_text"
            detail_text, error = capture_print_output(print_new_detail_posting, driver)
            if error:
                print("상세 본문 캡처 실패:", error)

        elif valid_image_urls:
            posting_type = "image"
            image_urls = valid_image_urls

        driver.switch_to.default_content()

        new_summary_check = driver.find_elements(
            By.CSS_SELECTOR,
            "[data-sentry-component='RecruitmentGuidelines'], "
            "[data-sentry-component='Qualification'], "
            "#application-section, "
            "#company-section"
        )

        if new_summary_check:
            summary_text, error = capture_print_output(print_new_summary_posting, driver)
            if error:
                print("요약 영역 캡처 실패:", error)

        posting_data = {
            "url": link,
            "company": company,
            "title": title,
            "posting_type": posting_type,
            "detail_text": detail_text,
            "summary_text": summary_text,
            "image_urls": image_urls
        }

        collected_postings.append(posting_data)

    return collected_postings


# =========================
# 실행 모드 설정
# "initial" : 최초 200개 수집
# "incremental" : 기존 링크와 비교해서 신규만 수집, 중복 나오면 중단
# "expired" : 저장된 링크들 중 만료 공고 찾기
# =========================
MODE = "initial"


chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--ignore-certificate-errors")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 15)

try:
    if MODE == "initial":
        initial_links = collect_initial_links(driver, wait, max_count=200, max_pages=100)
        print(f"초기 수집 링크 수: {len(initial_links)}")
        collected_postings = crawl_and_collect_postings(driver, initial_links)
        print(f"\n최종 수집 공고 수: {len(collected_postings)}")

    elif MODE == "incremental":
        existing_links = set([
            # 여기에 친구 JSON에서 읽어온 기존 링크 넣기
            # 예시:
            # "https://www.jobkorea.co.kr/Recruit/GI_Read/12345678"
        ])

        new_links = collect_new_links_until_duplicate(driver, wait, existing_links, max_pages=100)
        print(f"신규 수집 링크 수: {len(new_links)}")
        collected_postings = crawl_and_collect_postings(driver, new_links)
        print(f"\n최종 수집 공고 수: {len(collected_postings)}")

    elif MODE == "expired":
        saved_links = [
            # 여기에 현재 저장된 전체 링크 넣기
            # 예시:
            # "https://www.jobkorea.co.kr/Recruit/GI_Read/12345678"
        ]

        expired_links = find_expired_links(driver, saved_links)
        print(f"만료 공고 수: {len(expired_links)}")
        for link in expired_links:
            print(link)

    else:
        print("MODE 값을 확인하세요. initial / incremental / expired 중 하나여야 합니다.")

finally:
    driver.quit()