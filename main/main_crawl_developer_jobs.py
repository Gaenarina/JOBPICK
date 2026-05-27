import json
import os
import sys
import time
from urllib.parse import quote, urlsplit, urlunsplit

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from selenium.webdriver.common.by import By

from crawler.crawler_jobposting import JobKoreaCrawler
from ocr.ocr_jobposting import extract_text_from_image
from preprocess.preprocess_jobposting import preprocess_text
from structure.structure_image_jobposting import structure_jobposting_from_image
from structure.structure_text_jobposting import structure_jobposting_from_text

from database.firebase_init import init_firebase
from database.firebase_save_jobposting import (
    save_jobposting,
    save_failed_jobposting,
)


DEFAULT_KEYWORDS = [
    "프론트엔드 개발자",
    "백엔드 개발자",
    "웹 개발자",
    "React 개발자",
    "Spring 개발자",
    "Python 개발자",
]

DEFAULT_TARGET_COUNT = 5


def normalize_url_for_compare(url):
    if not url:
        return ""

    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def normalize_jobkorea_link(link):
    if not link:
        return ""

    link = link.strip()

    if link.startswith("/"):
        link = "https://www.jobkorea.co.kr" + link

    if not link.startswith("http"):
        return ""

    return link


def is_job_detail_link(link):
    value = str(link or "").lower()

    return (
        "/recruit/gi_read/" in value
        or "gi_read" in value
    )


def load_existing_links(db):
    existing_links = set()

    for doc in db.collection("job_postings").stream():
        data = doc.to_dict() or {}

        source_url = (
            data.get("jobPosting", {}).get("sourceUrl", "")
            or data.get("meta", {}).get("sourceUrl", "")
            or data.get("sourceUrl", "")
        )

        if source_url:
            existing_links.add(normalize_url_for_compare(source_url))

    return existing_links


def get_anchor_text(anchor):
    try:
        return " ".join(anchor.text.split()).strip()
    except Exception:
        return ""


def find_job_links_on_current_page(crawler):
    selectors = [
        "a[href*='/Recruit/GI_Read/']",
        "a[href*='GI_Read']",
        "#dev-gi-list tr.devloopArea strong a",
        ".list-default a[href*='GI_Read']",
        ".recruit-info a[href*='GI_Read']",
        ".post-list-info a[href*='GI_Read']",
    ]

    found = []

    for selector in selectors:
        try:
            anchors = crawler.driver.find_elements(By.CSS_SELECTOR, selector)

            for anchor in anchors:
                try:
                    href = normalize_jobkorea_link(anchor.get_attribute("href"))
                    title = get_anchor_text(anchor)

                    if not href:
                        continue

                    if not is_job_detail_link(href):
                        continue

                    found.append({
                        "url": href,
                        "title": title,
                    })
                except Exception:
                    continue
        except Exception:
            continue

    result = []
    seen = set()

    for item in found:
        key = normalize_url_for_compare(item["url"])

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result


def open_search_page(crawler, keyword, page=1):
    search_url = f"https://www.jobkorea.co.kr/Search/?stext={quote(keyword)}"

    if page > 1:
        search_url += f"&Page_No={page}"

    crawler.driver.get(search_url)
    time.sleep(3)

    try:
        crawler.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(1)
        crawler.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        crawler.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
    except Exception:
        pass


def collect_developer_job_links(crawler, keywords, target_count, existing_links):
    collected = []
    seen = set(existing_links)

    max_collect_count = max(target_count * 4, target_count)

    for keyword in keywords:
        if len(collected) >= max_collect_count:
            break

        print(f"\n[검색어] {keyword}")

        for page in range(1, 4):
            if len(collected) >= max_collect_count:
                break

            print(f"- 검색 페이지 {page} 수집 중")

            try:
                open_search_page(crawler, keyword, page)
                links = find_job_links_on_current_page(crawler)
            except Exception as error:
                print(f"- 검색 페이지 수집 실패: {error}")
                continue

            print(f"- 발견 링크 수: {len(links)}")

            for item in links:
                url = item["url"]
                key = normalize_url_for_compare(url)

                if not key:
                    continue

                if key in seen:
                    continue

                seen.add(key)
                collected.append(url)

                print(f"  수집: {item.get('title', '')} / {url}")

                if len(collected) >= max_collect_count:
                    break

            time.sleep(1)

    return collected


def safe_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, set):
        return list(value)

    if isinstance(value, dict):
        result = []
        for item in value.values():
            result.extend(safe_list(item))
        return result

    return [str(value)]


def get_structured_text_for_filter(structured_data, posting):
    job_posting = structured_data.get("jobPosting", {}) or {}
    requirements = job_posting.get("requirements", {}) or {}
    job = job_posting.get("job", {}) or {}
    embedding_text = job_posting.get("embeddingText", {}) or {}

    parts = [
        posting.get("title", ""),
        posting.get("company", ""),
        job_posting.get("title", ""),
        job_posting.get("companyName", ""),
        job_posting.get("category", ""),
        job.get("department", ""),
        embedding_text.get("fullForEmbedding", ""),
    ]

    parts.extend(safe_list(job_posting.get("responsibilities", [])))
    parts.extend(safe_list(requirements.get("requiredSkills", [])))
    parts.extend(safe_list(requirements.get("preferredSkills", [])))
    parts.extend(safe_list(requirements.get("requiredQualifications", [])))
    parts.extend(safe_list(requirements.get("preferredQualifications", [])))
    parts.extend(safe_list(requirements.get("coreCompetencies", [])))

    return " ".join(str(part) for part in parts if str(part).strip())


def is_developer_job_text(text):
    value = str(text or "").lower()

    if not value.strip():
        return False

    hard_exclude_keywords = [
        "하드웨어",
        "설치as",
        "설치 a/s",
        "a/s",
        "as 담당",
        "장비 설치",
        "장비 점검",
        "장비 유지보수",
        "키오스크",
        "빔프로젝터",
        "센서",
        "전기",
        "전자",
        "통신 장비",
        "현장 설치",
        "방문 설치",
        "운전 가능",
        "차량 소지",
        "납품",
    ]

    direct_developer_keywords = [
        "프론트엔드",
        "프론트 개발",
        "백엔드",
        "서버 개발",
        "웹 개발",
        "웹개발",
        "풀스택",
        "개발자",
        "프로그래머",
        "소프트웨어 개발",
        "sw 개발",
        "응용sw",
        "응용 sw",
        "응용소프트웨어",
        "응용 소프트웨어",
        "프로그램 개발",
        "애플리케이션 개발",
        "어플리케이션 개발",
        "api 개발",
        "서비스 개발",
    ]

    if any(keyword in value for keyword in hard_exclude_keywords):
        if not any(keyword in value for keyword in direct_developer_keywords):
            return False

    if any(keyword in value for keyword in direct_developer_keywords):
        return True

    tech_keywords = [
        "python",
        "java",
        "javascript",
        "typescript",
        "react",
        "next.js",
        "nextjs",
        "node.js",
        "nodejs",
        "spring",
        "spring boot",
        "django",
        "flask",
        "fastapi",
        "sql",
        "mysql",
        "postgresql",
        "oracle",
        "firebase",
        "git",
        "github",
        "docker",
        "aws",
        "rest api",
        "api",
        "프로그래밍",
        "코딩",
        "데이터베이스",
    ]

    hit_count = sum(1 for keyword in tech_keywords if keyword in value)

    return hit_count >= 2


def is_structured_developer_job(structured_data, posting):
    filter_text = get_structured_text_for_filter(structured_data, posting)
    return is_developer_job_text(filter_text)


def save_text_posting(db, posting, posting_type):
    structured_data = structure_jobposting_from_text(posting)

    if not is_structured_developer_job(structured_data, posting):
        print("[건너뜀] 개발자 공고로 판단되지 않음")
        return None

    print("\n[구조화 결과]")
    print(json.dumps(structured_data, ensure_ascii=False, indent=2))

    main_data = posting.get("main") or {}
    summary_data = posting.get("summary") or {}

    raw_crawled_text = main_data.get("raw_crawled_text", "")
    raw_summary_text = summary_data.get("raw_summary_text", "")

    merged_raw_text = "\n\n".join([
        text for text in [raw_crawled_text, raw_summary_text] if text
    ])

    saved_id = save_jobposting(
        db=db,
        structured_data=structured_data,
        source_url=posting.get("url", ""),
        company_name=posting.get("company", ""),
        title=posting.get("title", ""),
        posting_type=posting_type,
        image_url="",
        raw_text=merged_raw_text,
        preprocessed_text=""
    )

    return saved_id


def save_image_posting(db, posting, posting_type):
    main_data = posting.get("main") or {}
    image_urls = main_data.get("image_urls", []) or []

    if not image_urls:
        failed_id = save_failed_jobposting(
            db=db,
            source_url=posting.get("url", ""),
            company_name=posting.get("company", ""),
            title=posting.get("title", ""),
            posting_type=posting_type,
            image_url="",
            error_message="이미지가 없습니다."
        )
        print(f"[Firestore 실패 저장] {failed_id}")
        return None

    raw_text_list = []
    preprocessed_text_list = []

    for image_url in image_urls:
        try:
            raw_text = extract_text_from_image(image_url)
            preprocessed_text = preprocess_text(raw_text)

            if raw_text:
                raw_text_list.append(raw_text)

            if preprocessed_text:
                preprocessed_text_list.append(preprocessed_text)

        except Exception as error:
            print(f"[OCR 실패] {error}")

    merged_raw_text = "\n\n".join(raw_text_list)
    merged_preprocessed_text = "\n\n".join(preprocessed_text_list)

    if not merged_preprocessed_text:
        failed_id = save_failed_jobposting(
            db=db,
            source_url=posting.get("url", ""),
            company_name=posting.get("company", ""),
            title=posting.get("title", ""),
            posting_type=posting_type,
            image_url=image_urls[0] if image_urls else "",
            error_message="OCR 결과가 없습니다."
        )
        print(f"[Firestore 실패 저장] {failed_id}")
        return None

    structured_data = structure_jobposting_from_image(
        merged_preprocessed_text,
        image_url=image_urls[0],
        company_name_hint=posting.get("company", ""),
        title_hint=posting.get("title", ""),
        source_url=posting.get("url", ""),
        meta={
            "companyName": posting.get("company", ""),
            "title": posting.get("title", ""),
            "sourceUrl": posting.get("url", ""),
            "imageUrl": image_urls[0],
        }
    )

    if not is_structured_developer_job(structured_data, posting):
        print("[건너뜀] 개발자 공고로 판단되지 않음")
        return None

    print("\n[구조화 결과]")
    print(json.dumps(structured_data, ensure_ascii=False, indent=2))

    saved_id = save_jobposting(
        db=db,
        structured_data=structured_data,
        source_url=posting.get("url", ""),
        company_name=posting.get("company", ""),
        title=posting.get("title", ""),
        posting_type=posting_type,
        image_url=image_urls[0],
        raw_text=merged_raw_text,
        preprocessed_text=merged_preprocessed_text
    )

    return saved_id


def process_single_posting(db, crawler, link, index):
    print("\n" + "=" * 100)
    print(f"[개발자 공고 후보 {index}]")
    print("공고 링크:", link)

    try:
        posting = crawler.crawl_single_posting(link)
    except Exception as error:
        print(f"[크롤링 실패] {error}")
        failed_id = save_failed_jobposting(
            db=db,
            source_url=link,
            company_name="",
            title="",
            posting_type="unknown",
            image_url="",
            error_message=f"크롤링 실패: {error}"
        )
        print(f"[Firestore 실패 저장] {failed_id}")
        return None

    print("회사명:", posting.get("company", ""))
    print("공고 제목:", posting.get("title", ""))

    if not is_developer_job_text(posting.get("title", "")):
        print("[제목 기준 확인] 제목만으로는 개발자 공고 여부가 약함. 상세 구조화 후 다시 판단함.")

    main_data = posting.get("main") or {}

    if not main_data:
        failed_id = save_failed_jobposting(
            db=db,
            source_url=posting.get("url", ""),
            company_name=posting.get("company", ""),
            title=posting.get("title", ""),
            posting_type="unknown",
            image_url="",
            error_message="메인 공고 내용이 없습니다."
        )
        print(f"[Firestore 실패 저장] {failed_id}")
        return None

    posting_type = main_data.get("posting_type", "")

    try:
        if posting_type in ["old_text", "new_text"]:
            print("\n[텍스트 공고]")
            saved_id = save_text_posting(db, posting, posting_type)

        elif posting_type == "image":
            print("\n[이미지 공고]")
            saved_id = save_image_posting(db, posting, posting_type)

        else:
            print(f"\n[처리 실패] 알 수 없는 공고 유형: {posting_type}")

            failed_id = save_failed_jobposting(
                db=db,
                source_url=posting.get("url", ""),
                company_name=posting.get("company", ""),
                title=posting.get("title", ""),
                posting_type=posting_type,
                image_url="",
                error_message=f"알 수 없는 공고 유형: {posting_type}"
            )
            print(f"[Firestore 실패 저장] {failed_id}")
            return None

        if saved_id:
            print(f"\n[Firestore 저장 완료] {saved_id}")
            return saved_id

        return None

    except Exception as error:
        print(f"[구조화 또는 저장 실패] {error}")

        failed_id = save_failed_jobposting(
            db=db,
            source_url=posting.get("url", ""),
            company_name=posting.get("company", ""),
            title=posting.get("title", ""),
            posting_type=posting_type,
            image_url="",
            error_message=f"구조화 또는 저장 실패: {error}"
        )
        print(f"[Firestore 실패 저장] {failed_id}")
        return None


def parse_args():
    target_count = DEFAULT_TARGET_COUNT
    keywords = DEFAULT_KEYWORDS

    if len(sys.argv) >= 2:
        try:
            target_count = int(sys.argv[1])
        except Exception:
            target_count = DEFAULT_TARGET_COUNT

    if len(sys.argv) >= 3:
        raw_keywords = sys.argv[2]
        parsed_keywords = [
            keyword.strip()
            for keyword in raw_keywords.split(",")
            if keyword.strip()
        ]

        if parsed_keywords:
            keywords = parsed_keywords

    return target_count, keywords


def main():
    target_count, keywords = parse_args()

    print(f"[목표 저장 개수] {target_count}")
    print(f"[검색어] {keywords}")

    db, _ = init_firebase("config/firebase_key.json")
    crawler = JobKoreaCrawler(headless=True)

    saved_count = 0

    try:
        existing_links = load_existing_links(db)
        print(f"[기존 공고 링크 수] {len(existing_links)}")

        links = collect_developer_job_links(
            crawler=crawler,
            keywords=keywords,
            target_count=target_count,
            existing_links=existing_links,
        )

        print(f"\n[개발자 공고 후보 링크 수] {len(links)}")

        for index, link in enumerate(links, start=1):
            if saved_count >= target_count:
                break

            saved_id = process_single_posting(
                db=db,
                crawler=crawler,
                link=link,
                index=index,
            )

            if saved_id:
                saved_count += 1
                print(f"[현재 저장 개수] {saved_count}/{target_count}")

            time.sleep(1)

        print("\n" + "=" * 100)
        print(f"[완료] 개발자 공고 저장 개수: {saved_count}/{target_count}")

        if saved_count < target_count:
            print("[안내] 검색 결과가 부족하거나 개발자 공고로 판단되지 않아 목표 개수보다 적게 저장됐습니다.")
            print("[안내] 검색어를 더 구체적으로 바꿔 다시 실행해보세요.")

    finally:
        crawler.close()


if __name__ == "__main__":
    main()