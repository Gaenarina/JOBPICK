import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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

TARGET_COUNT = 5


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
            existing_links.add(source_url)

    return existing_links


def main():
    db, _ = init_firebase("config/firebase_key.json")
    crawler = JobKoreaCrawler(headless=True)

    try:
        existing_links = load_existing_links(db)
        print(f"[기존 공고 링크 수] {len(existing_links)}")

        postings = crawler.crawl_multiple_postings(
            target_count=TARGET_COUNT,
            existing_links=existing_links
        )

        for index, posting in enumerate(postings, start=1):
            print("\n" + "=" * 100)
            print(f"[공고 {index}]")
            print("회사명:", posting.get("company", ""))
            print("공고 제목:", posting.get("title", ""))
            print("공고 링크:", posting.get("url", ""))

            main_data = posting.get("main") or {}
            summary_data = posting.get("summary") or {}

            if not main_data:
                print("\n[처리 실패] 메인 공고 내용이 없습니다.")

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
                continue

            posting_type = main_data.get("posting_type", "")

            if posting_type in ["old_text", "new_text"]:
                print("\n[텍스트 공고]")

                structured_data = structure_jobposting_from_text(posting)

                print("\n[구조화 결과]")
                print(json.dumps(structured_data, ensure_ascii=False, indent=2))

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
                print(f"\n[Firestore 저장 완료] {saved_id}")

            elif posting_type == "image":
                print("\n[이미지 공고]")

                image_urls = main_data.get("image_urls", []) or []
                if not image_urls:
                    print("\n[처리 실패] 이미지가 없습니다.")

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
                    continue

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
                    print("\n[처리 실패] OCR 결과가 없습니다.")

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
                    continue

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
                print(f"\n[Firestore 저장 완료] {saved_id}")

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

    finally:
        crawler.close()


if __name__ == "__main__":
    main()
