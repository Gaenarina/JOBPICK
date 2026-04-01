# preprocess_jobposting.py

import re
from typing import Any, Dict


def preprocess_text(text: str) -> str:
    if not text:
        return ""

    # 줄바꿈/공백 정리
    text = text.replace("\r", "\n")
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    # 특수문자 정리
    text = text.replace("•", "")
    text = text.replace("·", " ")
    text = text.replace("\xa0", " ")

    # 양끝 공백 제거
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]

    return "\n".join(lines)


def normalize_text_value(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\r", "\n")
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.replace("•", "")
    text = text.replace("·", " ")
    text = text.replace("\xa0", " ")

    return text.strip()


def preprocess_jobposting_data(posting: Dict) -> Dict:
    """
    텍스트 공고용 공통 전처리
    - crawler가 반환한 posting 객체를 정리해서 다시 반환
    """
    cleaned_posting = {
        "url": normalize_text_value(posting.get("url", "")),
        "company": normalize_text_value(posting.get("company", "")),
        "title": normalize_text_value(posting.get("title", "")),
        "main": {},
        "summary": {}
    }

    main_data = posting.get("main", {}) or {}
    summary_data = posting.get("summary", {}) or {}

    cleaned_main = {
        "posting_type": normalize_text_value(main_data.get("posting_type", ""))
    }

    posting_type = cleaned_main["posting_type"]

    if posting_type == "new_text":
        cleaned_positions = []
        for position in main_data.get("positions", []) or []:
            cleaned_positions.append({
                "header": normalize_text_value(position.get("header", "")),
                "body": normalize_text_value(position.get("body", ""))
            })

        cleaned_sections = {}
        for key, values in (main_data.get("sections", {}) or {}).items():
            cleaned_key = normalize_text_value(key)
            cleaned_values = [
                normalize_text_value(value)
                for value in (values or [])
                if normalize_text_value(value)
            ]
            cleaned_sections[cleaned_key] = cleaned_values

        cleaned_main["positions"] = cleaned_positions
        cleaned_main["sections"] = cleaned_sections

    elif posting_type == "old_text":
        cleaned_positions = []
        for position in main_data.get("positions", []) or []:
            cleaned_positions.append({
                "group": normalize_text_value(position.get("group", "")),
                "job_name": normalize_text_value(position.get("job_name", "")),
                "responsibilities": normalize_text_value(position.get("responsibilities", "")),
                "qualifications": normalize_text_value(position.get("qualifications", "")),
                "experience_type": normalize_text_value(position.get("experience_type", ""))
            })

        cleaned_main["positions"] = cleaned_positions
        cleaned_main["company_desc"] = normalize_text_value(main_data.get("company_desc", ""))
        cleaned_main["common_requirements"] = [
            normalize_text_value(value)
            for value in (main_data.get("common_requirements", []) or [])
            if normalize_text_value(value)
        ]

        cleaned_extra_sections = {}
        for key, values in (main_data.get("extra_sections", {}) or {}).items():
            cleaned_key = normalize_text_value(key)

            if isinstance(values, list):
                cleaned_extra_sections[cleaned_key] = [
                    normalize_text_value(value)
                    for value in values
                    if normalize_text_value(value)
                ]
            else:
                cleaned_extra_sections[cleaned_key] = normalize_text_value(values)

        cleaned_main["extra_sections"] = cleaned_extra_sections
        cleaned_main["hiring_steps"] = [
            normalize_text_value(value)
            for value in (main_data.get("hiring_steps", []) or [])
            if normalize_text_value(value)
        ]
        cleaned_main["apply_link"] = normalize_text_value(main_data.get("apply_link", ""))

    cleaned_summary = {
        "guidelines": [
            normalize_text_value(value)
            for value in (summary_data.get("guidelines", []) or [])
            if normalize_text_value(value)
        ],
        "qualifications": [
            normalize_text_value(value)
            for value in (summary_data.get("qualifications", []) or [])
            if normalize_text_value(value)
        ],
        "application": normalize_text_value(summary_data.get("application", "")),
        "company_info": normalize_text_value(summary_data.get("company_info", ""))
    }

    cleaned_posting["main"] = cleaned_main
    cleaned_posting["summary"] = cleaned_summary

    return cleaned_posting