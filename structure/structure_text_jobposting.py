# structure_text_jobposting.py

import re


def clean_text(text):
    if text is None:
        return ""
    return " ".join(str(text).split()).strip()


def unique_preserve_order(items):
    seen = set()
    result = []

    for item in items:
        value = clean_text(item)
        if not value:
            continue
        if value not in seen:
            seen.add(value)
            result.append(value)

    return result


def split_lines(text):
    if not text:
        return []
    return [clean_text(line) for line in str(text).split("\n") if clean_text(line)]


def flatten_to_list(value):
    result = []

    if value is None:
        return result

    if isinstance(value, list):
        for item in value:
            if isinstance(item, list):
                result.extend(flatten_to_list(item))
            else:
                txt = clean_text(item)
                if txt:
                    result.append(txt)

    elif isinstance(value, dict):
        for v in value.values():
            result.extend(flatten_to_list(v))

    else:
        txt = clean_text(value)
        if txt:
            result.append(txt)

    return result


def extract_recruitment_period(text):
    text = clean_text(text)

    patterns = [
        r"\d{4}\.\d{1,2}\.\d{1,2}\s*[~\-]\s*\d{4}\.\d{1,2}\.\d{1,2}",
        r"\d{4}-\d{1,2}-\d{1,2}\s*[~\-]\s*\d{4}-\d{1,2}-\d{1,2}",
        r"\d{1,2}/\d{1,2}\s*[~\-]\s*\d{1,2}/\d{1,2}",
        r"상시채용",
        r"채용시까지",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return clean_text(match.group())

    return ""


def parse_guidelines(summary_data):
    if not summary_data:
        return []

    guidelines = summary_data.get("guidelines", [])

    if isinstance(guidelines, list):
        return unique_preserve_order(guidelines)

    if isinstance(guidelines, str):
        return unique_preserve_order(split_lines(guidelines))

    return []


def parse_qualifications(summary_data):
    if not summary_data:
        return []

    qualifications = summary_data.get("qualifications", [])

    if isinstance(qualifications, list):
        return unique_preserve_order(qualifications)

    if isinstance(qualifications, str):
        return unique_preserve_order(split_lines(qualifications))

    return []


def parse_application(summary_data):
    if not summary_data:
        return ""

    application = summary_data.get("application", "")
    return clean_text(application)


def parse_company_info(summary_data):
    if not summary_data:
        return ""

    company_info = summary_data.get("company_info", "")
    return clean_text(company_info)


def extract_common_fields_from_texts(texts):
    education = []
    qualifications = []
    skills = []
    certifications = []
    salary = []
    application_method = []
    hiring_count = []
    responsibilities = []

    skill_keywords = [
        "python", "java", "javascript", "typescript", "react", "next.js",
        "node.js", "sql", "aws", "docker", "kubernetes", "firebase",
        "git", "linux", "c", "c++", "ai", "ml", "딥러닝", "머신러닝",
        "데이터 분석", "웹 개발", "백엔드", "프론트엔드", "앱 개발"
    ]

    cert_keywords = [
        "자격증", "정보처리기사", "sqld", "sqld", "adsp", "토익", "toeic",
        "토스", "opic", "오픽", "컴활"
    ]

    education_keywords = [
        "학력", "대졸", "초대졸", "석사", "박사", "고졸", "학사", "전공"
    ]

    qualification_keywords = [
        "자격", "요건", "우대", "필수", "경력", "신입", "가능", "경험"
    ]

    salary_keywords = [
        "연봉", "급여", "월급", "시급", "보수", "처우"
    ]

    application_keywords = [
        "지원", "접수", "제출", "지원방법", "접수방법", "홈페이지", "이메일"
    ]

    hiring_count_keywords = [
        "채용인원", "모집인원", "00명", "0명", "두 자릿수"
    ]

    responsibility_keywords = [
        "담당", "업무", "역할", "직무", "수행"
    ]

    for text in texts:
        t = clean_text(text)
        lower_t = t.lower()

        if any(keyword in t for keyword in education_keywords):
            education.append(t)

        if any(keyword in t for keyword in qualification_keywords):
            qualifications.append(t)

        if any(keyword in lower_t for keyword in skill_keywords):
            skills.append(t)

        if any(keyword.lower() in lower_t for keyword in cert_keywords):
            certifications.append(t)

        if any(keyword in t for keyword in salary_keywords):
            salary.append(t)

        if any(keyword in t for keyword in application_keywords):
            application_method.append(t)

        if any(keyword in t for keyword in hiring_count_keywords):
            hiring_count.append(t)

        if any(keyword in t for keyword in responsibility_keywords):
            responsibilities.append(t)

    return {
        "education": unique_preserve_order(education),
        "qualifications": unique_preserve_order(qualifications),
        "skills": unique_preserve_order(skills),
        "certifications": unique_preserve_order(certifications),
        "salary": unique_preserve_order(salary),
        "applicationMethod": unique_preserve_order(application_method),
        "hiringCount": unique_preserve_order(hiring_count),
        "responsibilities": unique_preserve_order(responsibilities),
    }


def structure_old_text_posting(posting):
    main_data = posting.get("main", {}) or {}
    summary_data = posting.get("summary", {}) or {}

    company_name = clean_text(posting.get("company", ""))
    title = clean_text(posting.get("title", ""))
    image_urls = posting.get("image_urls", []) or []

    company_desc = clean_text(main_data.get("company_desc", ""))
    positions = main_data.get("positions", []) or []
    common_requirements = main_data.get("common_requirements", []) or []
    extra_sections = main_data.get("extra_sections", {}) or {}
    hiring_steps = main_data.get("hiring_steps", []) or []
    apply_link = clean_text(main_data.get("apply_link", ""))

    all_texts = [title, company_desc]

    for pos in positions:
        all_texts.extend([
            pos.get("group", ""),
            pos.get("job_name", ""),
            pos.get("responsibilities", ""),
            pos.get("qualifications", ""),
            pos.get("experience_type", ""),
        ])

    all_texts.extend(common_requirements)
    all_texts.extend(flatten_to_list(extra_sections))
    all_texts.extend(hiring_steps)
    all_texts.extend(parse_guidelines(summary_data))
    all_texts.extend(parse_qualifications(summary_data))
    all_texts.append(parse_application(summary_data))
    all_texts.append(parse_company_info(summary_data))

    extracted = extract_common_fields_from_texts(all_texts)

    responsibilities_list = []
    qualifications_list = []

    for pos in positions:
        job_name = clean_text(pos.get("job_name", ""))
        resp = clean_text(pos.get("responsibilities", ""))
        qual = clean_text(pos.get("qualifications", ""))
        exp = clean_text(pos.get("experience_type", ""))

        if job_name and resp:
            responsibilities_list.append(f"{job_name}: {resp}")
        elif resp:
            responsibilities_list.append(resp)

        if job_name and qual:
            qualifications_list.append(f"{job_name}: {qual}")
        elif qual:
            qualifications_list.append(qual)

        if exp:
            qualifications_list.append(exp)

    qualifications_list.extend(common_requirements)
    qualifications_list.extend(parse_qualifications(summary_data))
    responsibilities_list.extend(extracted["responsibilities"])

    application_method = []
    if apply_link:
        application_method.append(apply_link)
    application_method.extend(flatten_to_list(extra_sections.get("접수방법", [])))
    application_method.extend(extracted["applicationMethod"])

    recruitment_period = ""
    for text in all_texts:
        recruitment_period = extract_recruitment_period(text)
        if recruitment_period:
            break

    return {
        "jobPosting": {
            "companyName": company_name,
            "title": title,
            "recruitmentPeriod": recruitment_period,
            "imageUrl": image_urls[0] if image_urls else "",
            "education": "\n".join(extracted["education"]),
            "qualifications": "\n".join(unique_preserve_order(qualifications_list)),
            "skills": "\n".join(extracted["skills"]),
            "certifications": "\n".join(extracted["certifications"]),
            "salary": "\n".join(extracted["salary"]),
            "applicationMethod": "\n".join(unique_preserve_order(application_method)),
            "hiringCount": "\n".join(extracted["hiringCount"]),
            "responsibilities": "\n".join(unique_preserve_order(responsibilities_list)),
            "companyDescription": company_desc,
            "hiringSteps": unique_preserve_order(hiring_steps),
            "extraSections": extra_sections,
            "sourceUrl": clean_text(posting.get("url", "")),
            "postingType": "old_text",
        }
    }


def structure_new_text_posting(posting):
    main_data = posting.get("main", {}) or {}
    summary_data = posting.get("summary", {}) or {}

    company_name = clean_text(posting.get("company", ""))
    title = clean_text(posting.get("title", ""))
    image_urls = posting.get("image_urls", []) or []

    positions = main_data.get("positions", []) or []
    sections = main_data.get("sections", {}) or {}

    guideline_parsed = parse_guidelines(summary_data)
    qualification_parsed = parse_qualifications(summary_data)
    application_text = parse_application(summary_data)
    company_info_text = parse_company_info(summary_data)

    all_texts = [title, company_info_text, application_text]
    all_texts.extend(guideline_parsed)
    all_texts.extend(qualification_parsed)

    position_lines = []
    for pos in positions:
        header = clean_text(pos.get("header", ""))
        body = clean_text(pos.get("body", ""))
        line = f"{header}: {body}" if header and body else (header or body)
        if line:
            position_lines.append(line)
            all_texts.append(line)

    for sec_title, sec_lines in sections.items():
        all_texts.append(sec_title)
        all_texts.extend(flatten_to_list(sec_lines))

    extracted = extract_common_fields_from_texts(all_texts)

    qualifications_list = []
    qualifications_list.extend(guideline_parsed)
    qualifications_list.extend(qualification_parsed)

    responsibilities_list = []
    responsibilities_list.extend(position_lines)

    if "주요업무" in sections:
        responsibilities_list.extend(flatten_to_list(sections.get("주요업무", [])))
    if "담당업무" in sections:
        responsibilities_list.extend(flatten_to_list(sections.get("담당업무", [])))
    if "직무소개" in sections:
        responsibilities_list.extend(flatten_to_list(sections.get("직무소개", [])))

    if "자격요건" in sections:
        qualifications_list.extend(flatten_to_list(sections.get("자격요건", [])))
    if "우대사항" in sections:
        qualifications_list.extend(flatten_to_list(sections.get("우대사항", [])))
    if "지원자격" in sections:
        qualifications_list.extend(flatten_to_list(sections.get("지원자격", [])))

    recruitment_period = ""
    for text in all_texts:
        recruitment_period = extract_recruitment_period(text)
        if recruitment_period:
            break

    application_method = []
    if application_text:
        application_method.append(application_text)

    return {
        "jobPosting": {
            "companyName": company_name,
            "title": title,
            "recruitmentPeriod": recruitment_period,
            "imageUrl": image_urls[0] if image_urls else "",
            "education": "\n".join(extracted["education"]),
            "qualifications": "\n".join(unique_preserve_order(qualifications_list)),
            "skills": "\n".join(extracted["skills"]),
            "certifications": "\n".join(extracted["certifications"]),
            "salary": "\n".join(extracted["salary"]),
            "applicationMethod": "\n".join(unique_preserve_order(application_method)),
            "hiringCount": "\n".join(extracted["hiringCount"]),
            "responsibilities": "\n".join(unique_preserve_order(responsibilities_list)),
            "companyDescription": company_info_text,
            "hiringSteps": [],
            "extraSections": sections,
            "sourceUrl": clean_text(posting.get("url", "")),
            "postingType": "new_text",
        }
    }


def structure_jobposting_from_text(posting):
    main_data = posting.get("main", {}) or {}
    posting_type = clean_text(main_data.get("posting_type", ""))

    if posting_type == "old_text":
        return structure_old_text_posting(posting)

    if posting_type == "new_text":
        return structure_new_text_posting(posting)

    return {
        "jobPosting": {
            "companyName": clean_text(posting.get("company", "")),
            "title": clean_text(posting.get("title", "")),
            "recruitmentPeriod": "",
            "imageUrl": "",
            "education": "",
            "qualifications": "",
            "skills": "",
            "certifications": "",
            "salary": "",
            "applicationMethod": "",
            "hiringCount": "",
            "responsibilities": "",
            "companyDescription": "",
            "hiringSteps": [],
            "extraSections": {},
            "sourceUrl": clean_text(posting.get("url", "")),
            "postingType": posting_type if posting_type else "unknown",
        }
    }


# 예전 함수명 호환용
def build_job_posting_from_text_crawl(posting):
    return structure_jobposting_from_text(posting)