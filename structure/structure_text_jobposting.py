# structure_text_jobposting.py

import re


# =========================
# 기본 정리
# =========================
def clean_text(text):
    if text is None:
        return ""

    text = str(text)
    text = text.replace("\r", "\n").replace("\t", " ")
    text = re.sub(r"[•·●◦▪▫▸▹►▶※◆■□☞★☆]", "ㆍ", text)
    text = re.sub(r"[—–―]+", "-", text)
    text = re.sub(r"[→⇒➜➝➞]+", ">", text)
    text = re.sub(r"\((월|화|수|목|금|토|일)\)", "", text)
    text = re.sub(r"[^0-9a-zA-Z가-힣\s\.,:/~>\-\(\)ㆍ&\[\]]", " ", text)
    text = re.sub(r"\s*ㆍ\s*", " ㆍ ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_name(text):
    if text is None:
        return ""
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def clean_url(text):
    if text is None:
        return ""
    return str(text).strip()


def clean_text_for_embedding(text):
    if text is None:
        return ""

    text = str(text)
    text = re.sub(r"[•·●◦▪▫▸▹►▶※◆■□☞★☆]", " ", text)
    text = re.sub(r"\((월|화|수|목|금|토|일)\)", " ", text)
    text = re.sub(r"[^0-9a-zA-Z가-힣\s\.:/\-~]", " ", text)
    text = re.sub(r"\b[\.\-/:~]+\b", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_for_dedup(text):
    text = clean_text(text)
    text = re.sub(
        r"^(학력|경력|스킬|핵심역량|자격요건|지원자격|우대사항|우대조건|모집인원|급여|근무시간|근무지주소|접수방법|지원양식)\s*[:：]?\s*",
        "",
        text,
    )
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def unique_preserve_order(items):
    seen = set()
    result = []

    for item in items:
        value = clean_text(item)
        norm = normalize_for_dedup(value)

        if not norm:
            continue

        if norm not in seen:
            seen.add(norm)
            result.append(value)

    return result


def split_lines(text):
    if not text:
        return []
    return [clean_text(line) for line in str(text).split("\n") if clean_text(line)]


def split_bullets(text):
    if not text:
        return []

    text = clean_text(text)
    parts = re.split(r"\s*ㆍ\s*", text)

    result = []
    for part in parts:
        part = clean_text(part)
        if part:
            result.append(part)

    return result


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


def normalize_posting_type(raw_type):
    raw_type = clean_text(raw_type).lower().replace(" ", "_")
    if raw_type in {"new_text", "newtext"}:
        return "new_text"
    if raw_type in {"old_text", "oldtext"}:
        return "old_text"
    if raw_type == "image":
        return "image"
    return raw_type if raw_type else "unknown"


def get_meta_company(posting):
    return (
        clean_name(posting.get("company", ""))
        or clean_name((posting.get("meta") or {}).get("companyName", ""))
    )


def get_meta_title(posting):
    return (
        clean_name(posting.get("title", ""))
        or clean_name((posting.get("meta") or {}).get("title", ""))
    )


def get_meta_url(posting):
    return (
        clean_url(posting.get("url", ""))
        or clean_url((posting.get("meta") or {}).get("sourceUrl", ""))
    )


def get_meta_image_url(posting):
    image_urls = posting.get("image_urls", []) or []
    if image_urls:
        return clean_url(image_urls[0])
    return clean_url((posting.get("meta") or {}).get("imageUrl", ""))


# =========================
# 날짜 / 채용기간
# =========================
def normalize_date(date_text):
    date_text = clean_text(date_text)
    if not date_text:
        return ""

    date_text = re.sub(r"\((월|화|수|목|금|토|일)\)", "", date_text)
    date_text = date_text.replace(".", "-")
    date_text = re.sub(r"-+", "-", date_text).strip("-")
    return date_text


def extract_recruitment_period(text):
    text = clean_text(text)

    patterns = [
        r"\d{4}\.\d{1,2}\.\d{1,2}\s*[~\-]\s*\d{4}\.\d{1,2}\.\d{1,2}",
        r"\d{4}-\d{1,2}-\d{1,2}\s*[~\-]\s*\d{4}-\d{1,2}-\d{1,2}",
        r"시작일\s*\d{4}\.\d{1,2}\.\d{1,2}(?:\([^)]+\))?\s*마감일\s*\d{4}\.\d{1,2}\.\d{1,2}(?:\([^)]+\))?",
        r"\d{1,2}/\d{1,2}\s*[~\-]\s*\d{1,2}/\d{1,2}",
        r"상시채용",
        r"채용시까지",
        r"채용 시 마감",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return clean_text(match.group())

    return ""


def extract_recruitment_info(text):
    text = clean_text(text)

    start_match = re.search(r"시작일\s*(\d{4}\.\d{1,2}\.\d{1,2}(?:\([^)]+\))?)", text)
    end_match = re.search(r"마감일\s*(\d{4}\.\d{1,2}\.\d{1,2}(?:\([^)]+\))?)", text)

    start_date = normalize_date(start_match.group(1)) if start_match else ""
    end_date = normalize_date(end_match.group(1)) if end_match else ""

    is_rolling = any(x in text for x in ["상시채용", "채용시까지", "채용 시 마감"])
    raw = text if (start_date or end_date or is_rolling) else extract_recruitment_period(text)

    return {
        "raw": raw,
        "startDate": start_date,
        "endDate": end_date,
        "isRolling": is_rolling,
    }


# =========================
# summary 파싱
# =========================
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
    return clean_text(summary_data.get("application", ""))


def parse_company_info_text(summary_data):
    if not summary_data:
        return ""
    return clean_text(summary_data.get("company_info", ""))


def parse_company_info(summary_data):
    company_info_text = parse_company_info_text(summary_data)

    employee_match = re.search(r"사원수\s*([^\n]+?)(?:기업구분|산업\(업종\)|위치|$)", company_info_text)
    type_match = re.search(r"기업구분\s*([^\n]+?)(?:산업\(업종\)|위치|$)", company_info_text)
    industry_match = re.search(r"산업\(업종\)\s*([^\n]+?)(?:지도보기|위치|$)", company_info_text)
    location_match = re.search(r"위치\s*(.+)$", company_info_text)

    return {
        "employeeCount": clean_text(employee_match.group(1)) if employee_match else "",
        "companyType": clean_text(type_match.group(1)) if type_match else "",
        "industry": clean_text(industry_match.group(1)) if industry_match else "",
        "location": clean_text(location_match.group(1)) if location_match else "",
        "raw": company_info_text,
    }


# =========================
# 라벨 추출
# =========================
def extract_tagged_value(text, label, stop_labels=None):
    text = clean_text(text)
    if not text or not label:
        return ""

    if stop_labels is None:
        stop_labels = []

    if stop_labels:
        stop_pattern = "|".join(re.escape(x) for x in stop_labels)
        pattern = rf"{re.escape(label)}\s*[:：]?\s*(.*?)(?=(?:{stop_pattern})|$)"
    else:
        pattern = rf"{re.escape(label)}\s*[:：]?\s*(.*)$"

    match = re.search(pattern, text)
    if match:
        return clean_text(match.group(1))
    return ""


def extract_list_after_label(text, label, stop_labels=None):
    value = extract_tagged_value(text, label, stop_labels)
    if not value:
        return []

    return unique_preserve_order(
        [clean_text(x) for x in re.split(r",|/|\|", value) if clean_text(x)]
    )


def clean_short_field(value, prefixes=None):
    value = clean_text(value)
    if not value:
        return ""

    prefixes = prefixes or []
    for prefix in prefixes:
        value = re.sub(rf"^{re.escape(prefix)}\s*[:：]?\s*", "", value)

    return clean_text(value)


def sanitize_fragment(text):
    value = clean_text(text)

    if not value:
        return ""

    value = re.sub(r"^[ㆍ\-\.\:\>\s]+", "", value)
    value = re.sub(r"[ㆍ\-\.\:\>\s]+$", "", value)
    value = clean_text(value)

    if value in {"", ".", "-", ":", "ㆍ", ">"}:
        return ""

    return value

# =========================
# placeholder / 노이즈 필터
# =========================
PLACEHOLDER_PATTERNS = [
    "상세내용을 입력하세요",
    "상세 내용을 입력하세요",
    "내용을 입력하세요",
    "상세내용 입력",
    "상세 내용 입력",
]

def is_placeholder_text(text):
    value = clean_text(text)
    if not value:
        return True
    normalized = re.sub(r"\s+", "", value)
    return any(re.sub(r"\s+", "", pattern) in normalized for pattern in PLACEHOLDER_PATTERNS)

def filter_placeholder_items(items):
    return [
        item for item in items
        if clean_text(item) and not is_placeholder_text(item)
    ]

def clean_repeated_bullet_prefix(text):
    value = clean_text(text)
    value = re.sub(r"^ㆍ\\s*", "", value)
    return clean_text(value)



# =========================
# 공고 원문 보조 추출
# =========================
def get_full_source_text(posting):
    parts = []

    for key in ["rawText", "preprocessedText", "text", "body"]:
        value = posting.get(key, "")
        if value:
            parts.append(str(value))

    meta = posting.get("meta", {}) or {}
    for key in ["rawText", "preprocessedText", "text"]:
        value = meta.get(key, "")
        if value:
            parts.append(str(value))

    main_data = posting.get("main", {}) or {}
    for pos in main_data.get("positions", []) or []:
        parts.append(pos.get("header", ""))
        parts.append(pos.get("body", ""))

    for value in (main_data.get("sections", {}) or {}).values():
        parts.extend(flatten_to_list(value))

    summary_data = posting.get("summary", {}) or {}
    parts.extend(flatten_to_list(summary_data.get("guidelines", [])))
    parts.extend(flatten_to_list(summary_data.get("qualifications", [])))
    parts.append(summary_data.get("application", ""))
    parts.append(summary_data.get("company_info", ""))

    return clean_text("\n".join([str(x) for x in parts if clean_text(x)]))


def extract_tagged_value_any(text, labels, stop_labels=None):
    for label in labels:
        value = extract_tagged_value(text, label, stop_labels)
        if value:
            return value
    return ""


def is_real_responsibility_item(text):
    item = clean_text(text)
    if not item:
        return False

    blocked = [
        "자격요건", "지원자격", "우대사항", "우대조건", "근무환경", "근무조건",
        "급여", "복리후생", "전형절차", "접수방법", "지원방법", "기업 정보",
        "요약 영역", "모집요강", "지원자격", "접수기간", "유의사항", "회사소개",
        "허위사실", "면접", "최종합격", "마감일", "인사담당자",
    ]
    if any(bad in item for bad in blocked):
        return False

    if len(item) < 3 or len(item) > 160:
        return False

    return True


def split_numbered_responsibility_block(block):
    block = clean_text(block)
    if not block:
        return []

    results = []

    # 1. 앱설치 - ... 2. 검수 - ... 형태
    pattern = re.compile(
        r"(?:^|\s)(\d+)\.\s*([^\d\.\-]{1,25}?)\s*-\s*(.*?)(?=(?:\s\d+\.\s*[^\d\.\-]{1,25}?\s*-)|(?:\s*자격요건)|(?:\s*우대사항)|(?:\s*모집영역)|$)"
    )
    for match in pattern.finditer(block):
        title = clean_text(match.group(2))
        desc = clean_text(match.group(3))
        desc_parts = [x for x in re.split(r"\s*-\s*", desc) if clean_text(x)]
        if desc_parts:
            for part in desc_parts:
                item = f"{title}: {clean_text(part)}" if title else clean_text(part)
                if is_real_responsibility_item(item):
                    results.append(item)
        else:
            item = f"{title}: {desc}" if title else desc
            if is_real_responsibility_item(item):
                results.append(item)

    if results:
        return unique_preserve_order(results)

    # bullet 또는 문장형 fallback
    for item in split_bullets(block):
        if is_real_responsibility_item(item):
            results.append(item)

    return unique_preserve_order(results)



def split_task_phrases_from_free_text(block):
    block = clean_text(block)
    if not block:
        return []

    block = re.sub(r"\([^)]*수준[^)]*\)", " ", block)
    block = re.sub(r"\([^)]*\)", " ", block)
    block = clean_text(block)

    results = []
    patterns = [
        r"([A-Za-z가-힣0-9/\-]+(?:\s+[A-Za-z가-힣0-9/\-]+){0,3}\s+(?:운영관리|운영 관리|유지관리|유지 관리|유지보수|유지 보수))",
        r"([A-Za-z가-힣0-9/\-]+(?:\s+[A-Za-z가-힣0-9/\-]+){0,3}\s+(?:개발|개선|관리|구축|운영|상담|응대|검수|처리))",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, block):
            item = sanitize_fragment(match.group(1))
            if is_real_responsibility_item(item):
                results.append(item)
        if results:
            return unique_preserve_order(results)

    if is_real_responsibility_item(block):
        results.append(block)

    return unique_preserve_order(results)

def extract_responsibilities_from_raw_text(text):
    text = clean_text(text)
    if not text:
        return []

    labels = [
        "담당 업무", "담당업무", "담당 업무 (파트)", "주요업무", "업무내용", "직무소개",
        "수행 업무", "수행업무", "수행 내용", "수행내용", "수행할 업무",
        "합류하면 하게 될 일", "하게 될 일", "담당할 업무",
    ]
    stops = [
        "자격요건", "지원자격", "우대사항", "우대조건", "모집영역: 근무 환경",
        "근무 환경", "근무조건", "전형절차", "유의사항", "요약 영역", "모집요강",
        "접수기간", "기업 정보", "회사소개",
        "요구 기술", "요구기술", "필요 기술", "기술 환경", "기술환경", "단 가", "단가", "기타",
    ]

    # 담당 업무 (파트) 라벨부터 자격요건 전까지 직접 캡처
    label_pattern = "|".join(re.escape(x) for x in labels)
    stop_pattern = "|".join(re.escape(x) for x in stops)
    match = re.search(rf"(?:{label_pattern})\s*(.*?)(?=(?:{stop_pattern})|$)", text, flags=re.IGNORECASE)
    if match:
        captured_block = match.group(1)
        items = split_numbered_responsibility_block(captured_block)
        if not items:
            items = split_task_phrases_from_free_text(captured_block)
        if items:
            return items

    # 라벨 없이 원문에 번호형 업무가 바로 있는 경우
    numbered_hint = re.search(r"1\.\s*[^\d\.\-]{1,25}\s*-\s*.*?(?=\s*자격요건|\s*우대사항|$)", text)
    if numbered_hint:
        items = split_numbered_responsibility_block(numbered_hint.group(0))
        if items:
            return items

    return []


def filter_required_qualification_items(items):
    cleaned = []
    for item in items:
        value = clean_text(item)
        if not value:
            continue

        # 학력/경력은 별도 필드에서 점수화하므로 requiredQualifications에서는 제외
        if re.match(r"^(학력|경력)\s*[:：]", value):
            continue
        if value in {"학력", "경력", "고졸이상", "경력무관", "무관"}:
            continue
        if re.fullmatch(r"(학력\s*)?(고졸|초대졸|대졸|학사|석사|박사)\s*이상", value):
            continue
        if re.fullmatch(r"(경력\s*)?(무관|신입|경력무관)", value):
            continue

        cleaned.append(value)

    return unique_preserve_order(cleaned)


# =========================
# 의미 필터
# =========================
def is_meaningful_skill_item(text):
    t = clean_text(text).lower()
    if not t:
        return False

    blocked_keywords = [
        "근무", "급여", "휴게", "휴무", "포트폴리오", "고객", "매장", "행사",
        "지원", "희망연봉", "사대보험", "퇴직금", "요일", "시간", "스케줄"
    ]

    if any(keyword in t for keyword in blocked_keywords):
        return False

    return True


def is_meaningful_cert_item(text):
    t = clean_text(text)
    return "자격증" in t or "보유자" in t


# =========================
# summary 요약 파싱
# =========================
def parse_application_info(application_text):
    application_text = clean_text(application_text)

    method = extract_tagged_value(
        application_text,
        "접수방법",
        ["지원양식", "첨부서류", "마감일", "기업의 사정", "시작일"]
    )

    resume_form = extract_tagged_value(
        application_text,
        "지원양식",
        ["첨부서류", "마감일", "기업의 사정", "시작일"]
    )

    attachments = extract_list_after_label(
        application_text,
        "첨부서류",
        ["마감일", "기업의 사정", "시작일"]
    )

    return {
        "raw": application_text,
        "method": method,
        "resumeForm": resume_form,
        "attachments": attachments,
    }


def normalize_employment_type(text):
    text = clean_text(text)

    if "정규직" in text:
        return "정규직"
    if "계약직" in text:
        return "계약직"
    if "인턴" in text:
        return "인턴"
    if "프리랜서" in text:
        return "프리랜서"

    return ""


def extract_position_levels(text):
    text = clean_text(text)

    keywords = [
        "인턴", "사원급", "주임", "대리", "과장", "차장", "부장",
        "팀원", "팀장", "매니저", "리더", "연구원", "선임", "책임"
    ]

    return unique_preserve_order([k for k in keywords if k in text])


def parse_summary_requirements(summary_data):
    guideline_lines = parse_guidelines(summary_data)
    qualification_lines = parse_qualifications(summary_data)

    guideline_text = " ".join(guideline_lines)
    qualification_text = " ".join(qualification_lines)

    department = extract_tagged_value(
        guideline_text,
        "모집분야",
        ["모집인원", "고용형태", "직급/직책", "급여", "근무시간", "근무지주소"]
    )
    hiring_count = extract_tagged_value(
        guideline_text,
        "모집인원",
        ["고용형태", "직급/직책", "급여", "근무시간", "근무지주소"]
    )
    employment_type = extract_tagged_value(
        guideline_text,
        "고용형태",
        ["직급/직책", "급여", "근무시간", "근무지주소"]
    )
    position_text = extract_tagged_value(
        guideline_text,
        "직급/직책",
        ["급여", "근무시간", "근무지주소"]
    )
    salary = extract_tagged_value(
        guideline_text,
        "급여",
        ["근무시간", "근무지주소"]
    )
    work_time = extract_tagged_value(
        guideline_text,
        "근무시간",
        ["근무지주소"]
    )
    work_location = extract_tagged_value(
        guideline_text,
        "근무지주소",
        []
    )

    education = extract_tagged_value(
        qualification_text,
        "학력",
        ["경력", "스킬", "핵심역량", "자격요건", "지원자격", "우대사항", "우대조건"]
    )
    experience = extract_tagged_value(
        qualification_text,
        "경력",
        ["학력", "스킬", "핵심역량", "자격요건", "지원자격", "우대사항", "우대조건"]
    )
    required_skills = extract_list_after_label(
        qualification_text,
        "스킬",
        ["핵심역량", "자격요건", "지원자격", "우대사항", "우대조건", "경력", "학력"]
    )
    core_competencies = extract_list_after_label(
        qualification_text,
        "핵심역량",
        ["자격요건", "지원자격", "우대사항", "우대조건", "경력", "학력", "스킬"]
    )

    return {
        "department": department,
        "hiringCount": hiring_count,
        "employmentType": employment_type,
        "positionText": position_text,
        "salary": salary,
        "workTime": work_time,
        "workLocation": work_location,
        "education": education,
        "experience": experience,
        "requiredSkills": unique_preserve_order([x for x in required_skills if is_meaningful_skill_item(x)]),
        "coreCompetencies": unique_preserve_order(core_competencies),
        "guidelineLines": guideline_lines,
        "qualificationLines": qualification_lines,
    }


# =========================
# position 파싱
# =========================
def parse_position_body_text(body_text):
    body_text = clean_text(body_text)

    responsibilities_text = extract_tagged_value_any(
        body_text,
        [
            "담당업무", "담당 업무", "담당 업무 (파트)", "주요업무", "업무내용", "직무소개",
            "수행 업무", "수행업무", "수행 내용", "수행내용", "수행할 업무",
            "합류하면 하게 될 일", "하게 될 일", "담당할 업무",
        ],
        [
            "급여", "복리후생", "근무시간", "근무 시간", "근무요일", "근무 요일",
            "자격요건", "지원자격", "우대사항", "우대조건", "스킬", "핵심역량", "지원방법",
            "근무환경", "근무 환경", "모집영역", "요구 기술", "요구기술", "필요 기술", "기술 환경", "기술환경", "단가", "단 가", "기타"
        ]
    )

    required_text = extract_tagged_value(
        body_text,
        "자격요건",
        ["지원자격", "우대사항", "우대조건", "근무시간", "근무 시간", "급여", "복리후생"]
    )
    support_text = extract_tagged_value(
        body_text,
        "지원자격",
        ["우대사항", "우대조건", "근무시간", "근무 시간", "급여", "복리후생"]
    )
    preferred_text = extract_tagged_value(
        body_text,
        "우대사항",
        ["우대조건", "근무시간", "근무 시간", "급여", "복리후생", "지원방법"]
    )
    preferred_cond_text = extract_tagged_value(
        body_text,
        "우대조건",
        ["근무시간", "근무 시간", "급여", "복리후생", "지원방법"]
    )

    skill_text = extract_tagged_value(
        body_text,
        "스킬",
        ["핵심역량", "자격요건", "지원자격", "우대사항", "우대조건", "근무시간", "근무 시간", "급여"]
    )

    competency_text = extract_tagged_value(
        body_text,
        "핵심역량",
        ["자격요건", "지원자격", "우대사항", "우대조건", "근무시간", "근무 시간", "급여"]
    )

    work_time_block = extract_tagged_value(
        body_text,
        "근무 시간",
        ["급여", "복리후생", "자격요건", "지원자격", "우대사항", "우대조건"]
    ) or extract_tagged_value(
        body_text,
        "근무시간",
        ["급여", "복리후생", "자격요건", "지원자격", "우대사항", "우대조건"]
    )

    salary_text = extract_tagged_value(
        body_text,
        "급여",
        ["복리후생", "근무시간", "근무 시간", "자격요건", "지원자격", "우대사항", "우대조건", "지원방법"]
    )

    hiring_count_match = re.search(r"\(\s*([0-9○O]+)\s*명\s*\)", body_text)
    hiring_count = f"{hiring_count_match.group(1).replace('O', '○')}명" if hiring_count_match else ""

    work_hours = re.findall(r"\d{2}:\d{2}\s*~\s*\d{2}:\d{2}", work_time_block)

    responsibilities = []
    parsed_resp_items = split_numbered_responsibility_block(responsibilities_text)
    if not parsed_resp_items:
        parsed_resp_items = split_bullets(responsibilities_text)
    if not parsed_resp_items:
        parsed_resp_items = split_task_phrases_from_free_text(responsibilities_text)

    for item in parsed_resp_items:
        if any(bad in item for bad in ["급여", "퇴직금", "사대보험", "휴무", "휴게", "희망연봉"]):
            continue
        if is_real_responsibility_item(item):
            responsibilities.append(clean_repeated_bullet_prefix(item))

    required_qualifications = unique_preserve_order(
        split_bullets(required_text) + split_bullets(support_text)
    )
    preferred_qualifications = unique_preserve_order(
        split_bullets(preferred_text) + split_bullets(preferred_cond_text)
    )
    skills = unique_preserve_order([clean_text(x) for x in re.split(r",|/|\|", skill_text) if clean_text(x) and is_meaningful_skill_item(x)])
    core_competencies = unique_preserve_order([clean_text(x) for x in re.split(r",|/|\|", competency_text) if clean_text(x)])

    return {
        "responsibilities": unique_preserve_order(responsibilities),
        "requiredQualifications": required_qualifications,
        "preferredQualifications": preferred_qualifications,
        "skills": skills,
        "coreCompetencies": core_competencies,
        "workHours": unique_preserve_order(work_hours),
        "salary": clean_text(salary_text),
        "hiringCount": hiring_count,
    }


# =========================
# 임베딩 텍스트
# =========================
def build_embedding_text(job_posting):
    job = job_posting.get("job", {})
    requirements = job_posting.get("requirements", {})
    work_conditions = job_posting.get("workConditions", {})

    summary_parts = [
        job_posting.get("title", ""),
        job.get("department", ""),
        job.get("employmentType", ""),
        requirements.get("education", {}).get("minimum", ""),
        requirements.get("experience", {}).get("type", ""),
    ]

    responsibilities_text = ", ".join(job_posting.get("responsibilities", []))
    requirements_text = ", ".join(
        requirements.get("requiredSkills", [])
        + requirements.get("requiredQualifications", [])
        + requirements.get("coreCompetencies", [])
    )
    preferred_text = ", ".join(
        requirements.get("preferredSkills", [])
        + requirements.get("preferredQualifications", [])
    )
    conditions_text = ", ".join(
        unique_preserve_order(
            [work_conditions.get("salary", "")]
            + work_conditions.get("workHours", [])
            + [work_conditions.get("location", "")]
        )
    )

    summary = clean_text_for_embedding(" / ".join([x for x in summary_parts if clean_text(x)]))
    responsibilities_text = clean_text_for_embedding(responsibilities_text)
    requirements_text = clean_text_for_embedding(requirements_text)
    preferred_text = clean_text_for_embedding(preferred_text)
    conditions_text = clean_text_for_embedding(conditions_text)

    full_for_embedding = clean_text_for_embedding(
        " / ".join(
            [
                summary,
                responsibilities_text,
                requirements_text,
                preferred_text,
                conditions_text,
            ]
        )
    )

    return {
        "summary": summary,
        "responsibilities": responsibilities_text,
        "requirements": requirements_text,
        "preferred": preferred_text,
        "conditions": conditions_text,
        "fullForEmbedding": full_for_embedding,
    }




# =========================
# 최종 출력 직전 정리
# =========================
def compact_text_for_filter(text):
    return re.sub(r"\s+", "", clean_text(text))


def is_bad_output_item(text):
    value = clean_text(text)
    if not value:
        return True

    compact = compact_text_for_filter(value)

    bad_compact_keywords = [
        "상세내용을입력하세요",
        "상세내용입력",
        "내용을입력하세요",
        "상세내용을작성해주세요",
        "내용을작성해주세요",
    ]
    if any(keyword in compact for keyword in bad_compact_keywords):
        return True

    if re.fullmatch(r"[0-9○O]+명", value):
        return True

    if value in {"공통", "필수", "필수요건", "우대사항", "[필수요건]", "[우대사항]", "지원서 접수"}:
        return True

    return False


def is_bad_responsibility_output(text):
    value = clean_text(text)
    if is_bad_output_item(value):
        return True

    blocked_keywords = [
        "자격요건",
        "지원자격",
        "우대사항",
        "우대조건",
        "장애인 복지법",
        "국가유공자",
        "필수",
        "접수 안내",
        "접수기간",
        "접수방법",
        "지원방법",
        "온라인접수",
        "채용홈페이지",
        "채용 홈페이지",
        "전형절차",
        "유의사항",
        "문의사항",
        "지원서 접수",
        "홈페이지 를 통해 확인 가능",
        "홈페이지를 통해 확인 가능",
    ]
    if any(keyword in value for keyword in blocked_keywords):
        return True

    # 지역/위치만 잘못 들어온 경우 제거
    if value in {"서울", "분당", "수원", "평택", "원주", "부산", "대구", "대전", "광주"}:
        return True

    return False


def normalize_education_output(value):
    value = clean_text(value)
    if not value:
        return ""

    patterns = [
        "학력무관",
        "고졸 이상", "고졸이상",
        "초대졸 이상", "초대졸이상",
        "대졸 이상", "대졸이상",
        "4년제 대학 졸업", "대학교 졸업", "학사 이상", "학사이상",
        "석사 이상", "석사이상",
        "박사 이상", "박사이상",
        "무관",
    ]
    for pattern in patterns:
        if pattern in value:
            if pattern in {"고졸 이상", "고졸이상"}:
                return "고졸이상"
            if pattern in {"초대졸 이상", "초대졸이상"}:
                return "초대졸이상"
            if pattern in {"대졸 이상", "대졸이상", "4년제 대학 졸업", "대학교 졸업", "학사 이상", "학사이상"}:
                return "대졸이상"
            if pattern in {"석사 이상", "석사이상"}:
                return "석사이상"
            if pattern in {"박사 이상", "박사이상"}:
                return "박사이상"
            if pattern in {"학력무관", "무관"}:
                return "무관"

    return value


def clean_output_list(items, responsibility=False, max_len=None):
    cleaned = []
    for item in items or []:
        value = clean_text(item)
        if not value:
            continue

        if responsibility:
            if is_bad_responsibility_output(value):
                continue
        else:
            if is_bad_output_item(value):
                continue

        if max_len and len(value) > max_len:
            continue

        cleaned.append(value)

    return unique_preserve_order(cleaned)


def final_sanitize_job_posting(job_posting):
    requirements = job_posting.get("requirements", {}) or {}

    # 담당업무 최종 정리
    job_posting["responsibilities"] = clean_output_list(
        job_posting.get("responsibilities", []),
        responsibility=True,
    )

    # 학력 필드는 점수 계산용이므로 짧게 표준화
    education = requirements.get("education", {}) or {}
    education["minimum"] = normalize_education_output(education.get("minimum", ""))
    requirements["education"] = education

    # 자격요건/우대사항/스킬/자격증 최종 정리
    requirements["requiredQualifications"] = clean_output_list(
        requirements.get("requiredQualifications", []),
        responsibility=False,
        max_len=160,
    )
    requirements["preferredQualifications"] = clean_output_list(
        requirements.get("preferredQualifications", []),
        responsibility=False,
        max_len=180,
    )
    requirements["requiredSkills"] = clean_output_list(
        requirements.get("requiredSkills", []),
        responsibility=False,
        max_len=60,
    )
    requirements["preferredSkills"] = clean_output_list(
        requirements.get("preferredSkills", []),
        responsibility=False,
        max_len=80,
    )
    requirements["coreCompetencies"] = clean_output_list(
        requirements.get("coreCompetencies", []),
        responsibility=False,
        max_len=60,
    )

    # certifications는 자격증성 문구만 남기고, 긴 문단은 제거
    certs = []
    for item in requirements.get("certifications", []) or []:
        value = clean_text(item)
        if not value or is_bad_output_item(value):
            continue
        if len(value) > 90:
            continue
        if any(keyword in value for keyword in ["자격증", "지도사", "인명구조", "운전면허", "면허", "기사", "기능사"]):
            certs.append(value)
    requirements["certifications"] = unique_preserve_order(certs)

    job_posting["requirements"] = requirements
    return job_posting


# =========================
# legacy 변환
# =========================
def build_legacy_fields(job_posting):
    requirements = job_posting.get("requirements", {})
    work_conditions = job_posting.get("workConditions", {})
    application = job_posting.get("application", {})
    recruitment = job_posting.get("recruitment", {})
    company_info = job_posting.get("companyInfo", {})

    recruitment_period = ""
    if recruitment.get("startDate") and recruitment.get("endDate"):
        recruitment_period = f"{recruitment['startDate']} ~ {recruitment['endDate']}"
    elif recruitment.get("isRolling"):
        recruitment_period = "상시채용"
    else:
        recruitment_period = recruitment.get("raw", "")

    return {
        "companyName": job_posting.get("companyName", ""),
        "title": job_posting.get("title", ""),
        "recruitmentPeriod": recruitment_period,
        "imageUrl": job_posting.get("imageUrl", ""),
        "education": requirements.get("education", {}).get("minimum", ""),
        "qualifications": "\n".join(unique_preserve_order(
            requirements.get("requiredQualifications", []) + requirements.get("preferredQualifications", [])
        )),
        "skills": "\n".join(requirements.get("requiredSkills", [])),
        "certifications": "\n".join(requirements.get("certifications", [])),
        "salary": work_conditions.get("salary", ""),
        "applicationMethod": "\n".join(unique_preserve_order(
            [application.get("method", ""), application.get("resumeForm", "")] + application.get("attachments", [])
        )),
        "hiringCount": job_posting.get("job", {}).get("hiringCount", ""),
        "responsibilities": "\n".join(job_posting.get("responsibilities", [])),
        "companyDescription": company_info.get("raw", ""),
        "hiringSteps": job_posting.get("hiringProcess", []),
        "extraSections": job_posting.get("extraSections", {}),
        "sourceUrl": job_posting.get("sourceUrl", ""),
        "postingType": job_posting.get("postingType", ""),
    }


# =========================
# new_text 핵심
# =========================
def structure_new_text_posting(posting):
    main_data = posting.get("main", {}) or {}
    summary_data = posting.get("summary", {}) or {}

    company_name = get_meta_company(posting)
    title = get_meta_title(posting)
    source_url = get_meta_url(posting)
    image_url = get_meta_image_url(posting)

    positions = main_data.get("positions", []) or []
    sections = main_data.get("sections", {}) or {}
    source_text = get_full_source_text(posting)

    summary_requirements = parse_summary_requirements(summary_data)
    application_text = parse_application(summary_data)
    company_info = parse_company_info(summary_data)
    application_info = parse_application_info(application_text)
    recruitment = extract_recruitment_info(application_text)

    responsibilities = []
    required_qualifications = []
    preferred_qualifications = []
    required_skills = list(summary_requirements["requiredSkills"])
    preferred_skills = []
    core_competencies = list(summary_requirements["coreCompetencies"])
    work_hours = []
    position_salary_candidates = []
    position_hiring_count_candidates = []
    certifications = []

    for pos in positions:
        header = clean_text(pos.get("header", ""))
        body = clean_text(pos.get("body", ""))
        parsed = parse_position_body_text(body)

        for item in parsed["responsibilities"]:
            responsibilities.append(f"{header}: {item}" if header else item)

        required_qualifications.extend(parsed["requiredQualifications"])
        preferred_qualifications.extend(parsed["preferredQualifications"])
        required_skills.extend(parsed["skills"])
        core_competencies.extend(parsed["coreCompetencies"])
        work_hours.extend(parsed["workHours"])

        if parsed["salary"]:
            position_salary_candidates.append(parsed["salary"])
        if parsed["hiringCount"]:
            position_hiring_count_candidates.append(parsed["hiringCount"])

    if "주요업무" in sections:
        responsibilities.extend(flatten_to_list(sections.get("주요업무", [])))
    if "담당업무" in sections:
        responsibilities.extend(flatten_to_list(sections.get("담당업무", [])))
    if "직무소개" in sections:
        responsibilities.extend(flatten_to_list(sections.get("직무소개", [])))
    for responsibility_key in ["수행 업무", "수행업무", "수행 내용", "수행내용", "합류하면 하게 될 일", "하게 될 일", "담당할 업무"]:
        if responsibility_key in sections:
            responsibilities.extend(flatten_to_list(sections.get(responsibility_key, [])))

    if not responsibilities:
        responsibilities.extend(extract_responsibilities_from_raw_text(source_text))

    if "자격요건" in sections:
        required_qualifications.extend(flatten_to_list(sections.get("자격요건", [])))
    if "지원자격" in sections:
        required_qualifications.extend(flatten_to_list(sections.get("지원자격", [])))
    if "우대사항" in sections:
        preferred_qualifications.extend(flatten_to_list(sections.get("우대사항", [])))
    if "우대조건" in sections:
        preferred_qualifications.extend(flatten_to_list(sections.get("우대조건", [])))

    for item in preferred_qualifications:
        low = item.lower()
        if "포토샵" in item or "photoshop" in low or "figma" in low or "illustrator" in low:
            preferred_skills.append(item)
        if is_meaningful_cert_item(item):
            certifications.append(item)

    salary = clean_short_field(summary_requirements["salary"], ["급여"])
    if not salary and position_salary_candidates:
        salary = clean_short_field(position_salary_candidates[0], ["급여"])

    hiring_count = clean_short_field(summary_requirements["hiringCount"], ["모집인원"])
    if not hiring_count and position_hiring_count_candidates:
        hiring_count = clean_short_field(position_hiring_count_candidates[0], ["모집인원"])

    education = clean_short_field(summary_requirements["education"], ["학력"])
    experience = clean_short_field(summary_requirements["experience"], ["경력"])
    work_type = clean_short_field(summary_requirements["workTime"], ["근무시간"])
    work_location = clean_short_field(summary_requirements["workLocation"], ["근무지주소"])

    required_qualifications = filter_required_qualification_items(required_qualifications)
    preferred_qualifications = unique_preserve_order(filter_placeholder_items(preferred_qualifications))
    required_skills = unique_preserve_order([clean_repeated_bullet_prefix(x) for x in filter_placeholder_items(required_skills) if is_meaningful_skill_item(x)])
    core_competencies = unique_preserve_order(filter_placeholder_items(core_competencies))
    responsibilities = unique_preserve_order([clean_repeated_bullet_prefix(x) for x in responsibilities if is_real_responsibility_item(x)])

    hiring_steps = unique_preserve_order(flatten_to_list(sections.get("전형절차", [])))
    notices = unique_preserve_order(flatten_to_list(sections.get("유의사항", [])))

    job_posting = {
        "companyName": company_name,
        "title": title,
        "postingType": "new_text",
        "sourceUrl": source_url,
        "imageUrl": image_url,
        "recruitment": recruitment,
        "job": {
            "department": clean_short_field(summary_requirements["department"], ["모집분야"]),
            "hiringCount": hiring_count,
            "employmentType": normalize_employment_type(summary_requirements["employmentType"] or " ".join(summary_requirements["guidelineLines"])),
            "positionLevel": unique_preserve_order(
                extract_position_levels(summary_requirements["positionText"] or " ".join(summary_requirements["guidelineLines"]))
            ),
        },
        "requirements": {
            "education": {
                "minimum": education,
            },
            "experience": {
                "type": experience,
            },
            "requiredSkills": unique_preserve_order(required_skills),
            "preferredSkills": unique_preserve_order(preferred_skills),
            "requiredQualifications": unique_preserve_order(required_qualifications),
            "preferredQualifications": unique_preserve_order(preferred_qualifications),
            "coreCompetencies": unique_preserve_order(core_competencies),
            "certifications": unique_preserve_order(certifications),
        },
        "responsibilities": unique_preserve_order(responsibilities),
        "workConditions": {
            "salary": salary,
            "workHours": unique_preserve_order(work_hours),
            "location": work_location or company_info.get("location", ""),
            "workType": work_type,
        },
        "application": application_info,
        "hiringProcess": hiring_steps,
        "notices": notices,
        "companyInfo": {
            "companyType": company_info.get("companyType", ""),
            "industry": company_info.get("industry", ""),
            "employeeCount": company_info.get("employeeCount", ""),
            "raw": company_info.get("raw", ""),
        },
        "extraSections": sections,
    }

    job_posting = final_sanitize_job_posting(job_posting)
    job_posting["embeddingText"] = build_embedding_text(job_posting)

    return {
        "jobPosting": job_posting,
        "legacyJobPosting": build_legacy_fields(job_posting),
    }


# =========================
# old_text
# =========================
def structure_old_text_posting(posting):
    main_data = posting.get("main", {}) or {}
    summary_data = posting.get("summary", {}) or {}

    company_name = get_meta_company(posting)
    title = get_meta_title(posting)
    source_url = get_meta_url(posting)
    image_url = get_meta_image_url(posting)

    company_desc = clean_text(main_data.get("company_desc", ""))
    positions = main_data.get("positions", []) or []
    common_requirements = main_data.get("common_requirements", []) or []
    extra_sections = main_data.get("extra_sections", {}) or {}
    hiring_steps = main_data.get("hiring_steps", []) or []
    apply_link = clean_url(main_data.get("apply_link", ""))

    summary_requirements = parse_summary_requirements(summary_data)
    application_text = parse_application(summary_data)
    application_info = parse_application_info(application_text)
    company_info = parse_company_info(summary_data)
    recruitment = extract_recruitment_info(application_text)

    responsibilities = []
    required_qualifications = list(common_requirements)
    preferred_qualifications = []
    required_skills = list(summary_requirements["requiredSkills"])
    core_competencies = list(summary_requirements["coreCompetencies"])
    work_hours = []

    for pos in positions:
        job_name = clean_text(pos.get("job_name", ""))
        resp = clean_text(pos.get("responsibilities", ""))
        qual = clean_text(pos.get("qualifications", ""))
        exp = clean_text(pos.get("experience_type", ""))

        for item in split_bullets(resp):
            if is_real_responsibility_item(item):
                responsibilities.append(f"{job_name}: {item}" if job_name else item)

        required_qualifications.extend(split_bullets(qual))
        if exp:
            required_qualifications.append(exp)

    required_qualifications = filter_required_qualification_items(required_qualifications)
    preferred_qualifications = unique_preserve_order(filter_placeholder_items(preferred_qualifications))
    required_skills = unique_preserve_order([clean_repeated_bullet_prefix(x) for x in filter_placeholder_items(required_skills) if is_meaningful_skill_item(x)])
    core_competencies = unique_preserve_order(filter_placeholder_items(core_competencies))
    responsibilities = unique_preserve_order([clean_repeated_bullet_prefix(x) for x in responsibilities if is_real_responsibility_item(x)])

    job_posting = {
        "companyName": company_name,
        "title": title,
        "postingType": "old_text",
        "sourceUrl": source_url,
        "imageUrl": image_url,
        "recruitment": recruitment,
        "job": {
            "department": clean_short_field(summary_requirements["department"], ["모집분야"]),
            "hiringCount": clean_short_field(summary_requirements["hiringCount"], ["모집인원"]),
            "employmentType": normalize_employment_type(" ".join(summary_requirements["guidelineLines"])),
            "positionLevel": extract_position_levels(" ".join(summary_requirements["guidelineLines"])),
        },
        "requirements": {
            "education": {"minimum": clean_short_field(summary_requirements["education"], ["학력"])},
            "experience": {"type": clean_short_field(summary_requirements["experience"], ["경력"])},
            "requiredSkills": unique_preserve_order(required_skills),
            "preferredSkills": [],
            "requiredQualifications": unique_preserve_order(required_qualifications),
            "preferredQualifications": unique_preserve_order(preferred_qualifications),
            "coreCompetencies": unique_preserve_order(core_competencies),
            "certifications": [],
        },
        "responsibilities": unique_preserve_order(responsibilities),
        "workConditions": {
            "salary": clean_short_field(summary_requirements["salary"], ["급여"]),
            "workHours": unique_preserve_order(work_hours),
            "location": company_info.get("location", ""),
            "workType": clean_short_field(summary_requirements["workTime"], ["근무시간"]),
        },
        "application": {
            "raw": application_text,
            "method": application_info.get("method", "") or apply_link,
            "resumeForm": application_info.get("resumeForm", ""),
            "attachments": application_info.get("attachments", []),
            "applyLink": apply_link,
        },
        "hiringProcess": unique_preserve_order(hiring_steps),
        "notices": unique_preserve_order(flatten_to_list(extra_sections.get("유의사항", []))),
        "companyInfo": {
            "companyType": company_info.get("companyType", ""),
            "industry": company_info.get("industry", ""),
            "employeeCount": company_info.get("employeeCount", ""),
            "raw": company_desc or company_info.get("raw", ""),
        },
        "extraSections": extra_sections,
    }

    job_posting = final_sanitize_job_posting(job_posting)
    job_posting["embeddingText"] = build_embedding_text(job_posting)

    return {
        "jobPosting": job_posting,
        "legacyJobPosting": build_legacy_fields(job_posting),
    }


# =========================
# unknown fallback
# =========================
def structure_unknown_text_posting(posting):
    company_name = get_meta_company(posting)
    title = get_meta_title(posting)
    source_url = get_meta_url(posting)
    image_url = get_meta_image_url(posting)

    job_posting = {
        "companyName": company_name,
        "title": title,
        "postingType": "unknown",
        "sourceUrl": source_url,
        "imageUrl": image_url,
        "recruitment": {"raw": "", "startDate": "", "endDate": "", "isRolling": False},
        "job": {"department": "", "hiringCount": "", "employmentType": "", "positionLevel": []},
        "requirements": {
            "education": {"minimum": ""},
            "experience": {"type": ""},
            "requiredSkills": [],
            "preferredSkills": [],
            "requiredQualifications": [],
            "preferredQualifications": [],
            "coreCompetencies": [],
            "certifications": [],
        },
        "responsibilities": [],
        "workConditions": {"salary": "", "workHours": [], "location": "", "workType": ""},
        "application": {"raw": "", "method": "", "resumeForm": "", "attachments": []},
        "hiringProcess": [],
        "notices": [],
        "companyInfo": {"companyType": "", "industry": "", "employeeCount": "", "raw": ""},
        "extraSections": {},
    }

    job_posting = final_sanitize_job_posting(job_posting)
    job_posting["embeddingText"] = build_embedding_text(job_posting)

    return {
        "jobPosting": job_posting,
        "legacyJobPosting": build_legacy_fields(job_posting),
    }


# =========================
# 메인 엔트리
# =========================
def structure_jobposting_from_text(posting):
    main_data = posting.get("main", {}) or {}

    raw_posting_type = main_data.get("posting_type", "") or main_data.get("postingType", "")
    posting_type = normalize_posting_type(raw_posting_type)

    if posting_type == "old_text":
        return structure_old_text_posting(posting)

    if posting_type == "new_text":
        return structure_new_text_posting(posting)

    return structure_unknown_text_posting(posting)


# 예전 함수명 호환용
def build_job_posting_from_text_crawl(posting):
    return structure_jobposting_from_text(posting)
