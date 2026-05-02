# structure_image_jobposting

import re


# -----------------------------
# 1. 추출 대상 섹션 키워드
# -----------------------------
TARGET_SECTION_KEYWORDS = {
    "responsibilities": ["담당업무", "주요업무", "업무내용"],
    "qualifications": ["자격요건", "지원자격", "필수조건", "자격사항"],
    "applicationMethod": ["지원방법", "접수방법", "접수기한"]
}


# -----------------------------
# 2. 섹션 경계 인식용 키워드
# -----------------------------
BOUNDARY_HEADERS = [
    "담당업무", "주요업무", "업무내용",
    "자격요건", "지원자격", "필수조건", "자격사항",
    "우대사항", "우대조건",
    "근무조건", "근무시간", "근무장소",
    "전형절차", "채용절차",
    "지원방법", "접수방법", "접수기한",
    "복리후생", "복지사항",
    "제출서류", "기타사항",
    "채용분야", "모집분야",
    "급여", "연봉", "월급",
    "접수기간", "모집기간", "채용기간",
    "채용 시 마감", "채용시 마감", "조기 마감",
    "채용 완료시까지", "채용 완료 시까지", "상시채용"
]


# -----------------------------
# 3. 기본 정리
# -----------------------------
def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# -----------------------------
# 4. 구조화 전 노이즈 제거
# -----------------------------
def remove_text_noise(text: str) -> str:
    text = normalize_text(text)

    noise_patterns = [
        r"홈페이지\s*바로가기",
        r"바로가기",
        r"SMC\s*홈페이지\s*바로가기",
        r"\*\s*면접일정은\s*추후\s*통보됩니다\.?",
    ]

    for pattern in noise_patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    text = re.sub(r"\s+", " ", text).strip()
    return text


# -----------------------------
# 5. 특정 섹션 추출
# -----------------------------
def extract_section(text: str, start_keywords: list[str], boundary_headers: list[str]) -> str:
    text = remove_text_noise(text)

    start_match = None
    start_keyword = None

    for keyword in start_keywords:
        match = re.search(re.escape(keyword), text)
        if match:
            if start_match is None or match.start() < start_match.start():
                start_match = match
                start_keyword = keyword

    if not start_match:
        return ""

    start_idx = start_match.end()
    sub_text = text[start_idx:]
    end_idx = len(sub_text)

    for header in boundary_headers:
        if header == start_keyword:
            continue

        match = re.search(re.escape(header), sub_text)
        if match and match.start() < end_idx:
            end_idx = match.start()

    return normalize_text(sub_text[:end_idx])


# -----------------------------
# 6. 업체명 추출
# -----------------------------
def extract_company_name(text: str) -> str:
    text = remove_text_noise(text)

    explicit_patterns = [
        r"회사명\s*[:：]?\s*([가-힣A-Za-z0-9\(\)\[\]\.&,\- ]{1,30})",
        r"기업명\s*[:：]?\s*([가-힣A-Za-z0-9\(\)\[\]\.&,\- ]{1,30})",
        r"상호\s*[:：]?\s*([가-힣A-Za-z0-9\(\)\[\]\.&,\- ]{1,30})"
    ]

    for pattern in explicit_patterns:
        match = re.search(pattern, text)
        if match:
            company = normalize_text(match.group(1))
            for header in BOUNDARY_HEADERS:
                if header in company:
                    company = normalize_text(company.split(header)[0])
            if 0 < len(company) <= 20:
                return company

    split_keywords = [
        "담당업무", "주요업무", "업무내용",
        "자격요건", "지원자격", "필수조건", "자격사항",
        "모집분야", "채용분야"
    ]

    first_chunk = text
    for keyword in split_keywords:
        if keyword in text:
            first_chunk = text.split(keyword)[0]
            break

    first_chunk = normalize_text(first_chunk)

    if 0 < len(first_chunk) <= 20:
        return first_chunk

    return ""


# -----------------------------
# 7. 모집 기간 추출
# -----------------------------
def extract_recruitment_period(text: str) -> str:
    text = remove_text_noise(text)

    if "채용 시 마감" in text or "채용시 마감" in text:
        return "채용 시 마감"
    if "조기 마감" in text:
        return "조기 마감 가능"
    if "채용 완료시까지" in text or "채용 완료 시까지" in text:
        return "채용 완료시까지"
    if "상시채용" in text:
        return "상시채용"

    patterns = [
        r"접수기한\s*[:：]?\s*([^\s]+(?:\s*~\s*[^\s]+)?)",
        r"접수기간\s*[:：]?\s*([^\s]+(?:\s*~\s*[^\s]+)?)",
        r"모집기간\s*[:：]?\s*([^\s]+(?:\s*~\s*[^\s]+)?)",
        r"채용기간\s*[:：]?\s*([^\s]+(?:\s*~\s*[^\s]+)?)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_text(match.group(1))

    return ""


# -----------------------------
# 8. 메인 구조화 함수
# -----------------------------
def structure_jobposting_from_image(text: str, image_url: str = "", company_name_hint: str = "") -> dict:
    text = remove_text_noise(text)

    company_name = extract_company_name(text)
    if not company_name and company_name_hint:
        company_name = normalize_text(company_name_hint)

    application_method = extract_section(
        text,
        TARGET_SECTION_KEYWORDS["applicationMethod"],
        BOUNDARY_HEADERS
    )

    return {
        "jobPosting": {
            "companyName": company_name,
            "recruitmentPeriod": extract_recruitment_period(text),
            "imageUrl": image_url,
            "education": "",
            "qualifications": extract_section(
                text,
                TARGET_SECTION_KEYWORDS["qualifications"],
                BOUNDARY_HEADERS
            ),
            "skills": "",
            "certifications": "",
            "salary": "",
            "applicationMethod": application_method,
            "hiringCount": "",
            "responsibilities": extract_section(
                text,
                TARGET_SECTION_KEYWORDS["responsibilities"],
                BOUNDARY_HEADERS
            )
        }
    }