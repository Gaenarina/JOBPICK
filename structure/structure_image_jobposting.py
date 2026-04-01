# structure_image_jobposting.py

import re


# -----------------------------
# 1. 추출 대상 섹션 키워드
# -----------------------------
TARGET_SECTION_KEYWORDS = {
    "responsibilities": ["담당업무", "주요업무", "업무내용", "상세내용"],
    "qualifications": ["자격요건", "지원자격", "필수조건", "자격사항"],
    "preferredQualifications": ["우대사항", "우대조건"],
    "applicationMethod": ["지원방법", "접수방법", "접수기한", "지원기간", "접수기간"],
    "hiringProcess": ["전형절차", "채용절차"]
}


# -----------------------------
# 2. 섹션 경계 인식용 키워드
# -----------------------------
BOUNDARY_HEADERS = [
    "담당업무", "주요업무", "업무내용", "상세내용",
    "자격요건", "지원자격", "필수조건", "자격사항",
    "우대사항", "우대조건",
    "근무조건", "근무시간", "근무장소", "근무지", "근무형태",
    "전형절차", "채용절차",
    "지원방법", "접수방법", "접수기한", "지원기간", "접수기간",
    "복리후생", "복지사항",
    "제출서류", "기타사항",
    "채용분야", "모집분야", "모집인원", "채용인원",
    "급여", "연봉", "월급", "시급",
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
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"[•·●◦▪▫▸▹►▶※◆■□☞★☆]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def clean_name(text: str) -> str:
    if not text:
        return ""
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def clean_text_for_embedding(text: str) -> str:
    if not text:
        return ""

    text = str(text)
    text = re.sub(r"[•·●◦▪▫▸▹►▶※◆■□☞★☆]", " ", text)
    text = re.sub(r"\((월|화|수|목|금|토|일)\)", " ", text)
    text = re.sub(r"[^0-9a-zA-Z가-힣\s\.:/\-~]", " ", text)
    text = re.sub(r"\b[\.\-/:~]+\b", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def unique_preserve_order(items):
    seen = set()
    result = []

    for item in items:
        value = normalize_text(item)
        if not value:
            continue
        if value not in seen:
            seen.add(value)
            result.append(value)

    return result


def split_bullets(text: str) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []

    parts = re.split(r"\s*[ㆍ•·●◦▪▫▸▹►▶※◆■□☞★☆]\s*|\s{2,}", text)
    result = []

    for part in parts:
        part = normalize_text(part)
        if part:
            result.append(part)

    return unique_preserve_order(result)


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
def extract_company_name(text: str, company_name_hint: str = "") -> str:
    """
    이미지 OCR에서는 회사명을 OCR 본문에서 새로 추정하기보다
    크롤링 단계에서 확보한 company_name_hint를 우선 사용한다.
    """
    company_name_hint = normalize_text(company_name_hint)
    if company_name_hint:
        return company_name_hint

    text = remove_text_noise(text)

    explicit_patterns = [
        r"회사명\s*[:：]?\s*([가-힣A-Za-z0-9\(\)\[\]\.&,\- ]{1,40})",
        r"기업명\s*[:：]?\s*([가-힣A-Za-z0-9\(\)\[\]\.&,\- ]{1,40})",
        r"상호\s*[:：]?\s*([가-힣A-Za-z0-9\(\)\[\]\.&,\- ]{1,40})"
    ]

    for pattern in explicit_patterns:
        match = re.search(pattern, text)
        if match:
            company = normalize_text(match.group(1))

            for header in BOUNDARY_HEADERS:
                if header in company:
                    company = normalize_text(company.split(header)[0])

            if 1 <= len(company) <= 30:
                return company

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
        r"채용기간\s*[:：]?\s*([^\s]+(?:\s*~\s*[^\s]+)?)",
        r"지원기간\s*[:：]?\s*([^\s]+(?:\s*~\s*[^\s]+)?)",
        r"(\d{4}\.\d{1,2}\.\d{1,2}\s*[~\-]\s*\d{4}\.\d{1,2}\.\d{1,2})",
        r"(\d{2,4}\.\d{1,2}\.\d{1,2}\s*[~\-]\s*\d{2,4}\.\d{1,2}\.\d{1,2})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_text(match.group(1))

    return ""


# -----------------------------
# 8. 모집 인원 추출
# -----------------------------
def extract_hiring_count(text: str) -> str:
    text = remove_text_noise(text)

    patterns = [
        r"모집인원\s*[:：]?\s*([0-9○O]+명)",
        r"채용인원\s*[:：]?\s*([0-9○O]+명)",
        r"\(\s*([0-9○O]+명)\s*\)",
        r"\b([0-9○O]+명)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_text(match.group(1)).replace("O", "○")

    return ""


# -----------------------------
# 9. 급여 추출
# -----------------------------
def extract_salary(text: str) -> str:
    text = remove_text_noise(text)

    patterns = [
        r"급여\s*[:：]?\s*(.*?)(?=(연봉|월급|시급|복리후생|지원방법|전형절차|자격요건|우대사항|$))",
        r"연봉\s*[:：]?\s*(.*?)(?=(급여|월급|시급|복리후생|지원방법|전형절차|자격요건|우대사항|$))",
        r"월급\s*[:：]?\s*(.*?)(?=(급여|연봉|시급|복리후생|지원방법|전형절차|자격요건|우대사항|$))",
        r"시급\s*[:：]?\s*(.*?)(?=(급여|연봉|월급|복리후생|지원방법|전형절차|자격요건|우대사항|$))",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = normalize_text(match.group(1))
            if value:
                return value

    return ""


# -----------------------------
# 10. 학력 추출
# -----------------------------
def extract_education(text: str) -> str:
    text = remove_text_noise(text)

    patterns = [
        r"(학력무관)",
        r"학력\s*[:：]?\s*(.*?)(?=(경력|자격요건|우대사항|지원방법|전형절차|$))",
        r"(고졸이상|초대졸이상|대졸이상|학사이상|석사이상|박사이상)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_text(match.group(1))

    return ""


# -----------------------------
# 11. 전형절차 추출
# -----------------------------
def extract_hiring_steps(text: str) -> list[str]:
    sec = extract_section(text, TARGET_SECTION_KEYWORDS["hiringProcess"], BOUNDARY_HEADERS)
    if not sec:
        return []

    if ">" in sec:
        return unique_preserve_order([normalize_text(x) for x in sec.split(">") if normalize_text(x)])

    return split_bullets(sec)


# -----------------------------
# 12. 임베딩용 텍스트 생성
# -----------------------------
def build_image_embedding_text(job_posting: dict) -> dict:
    summary = " / ".join(filter(None, [
        job_posting.get("companyName", ""),
        job_posting.get("title", ""),
        job_posting.get("recruitmentPeriod", ""),
        job_posting.get("education", ""),
        job_posting.get("hiringCount", "")
    ]))

    full_text = " / ".join(filter(None, [
        summary,
        job_posting.get("responsibilities", ""),
        job_posting.get("qualifications", ""),
        job_posting.get("preferredQualifications", ""),
        job_posting.get("skills", ""),
        job_posting.get("salary", ""),
        job_posting.get("applicationMethod", "")
    ]))

    return {
        "summary": clean_text_for_embedding(summary),
        "fullForEmbedding": clean_text_for_embedding(full_text)
    }


# -----------------------------
# 13. 메인 구조화 함수
# -----------------------------
def structure_jobposting_from_image(
    text: str,
    image_url: str = "",
    company_name_hint: str = "",
    title_hint: str = "",
    source_url: str = ""
) -> dict:
    text = remove_text_noise(text)

    company_name = extract_company_name(text, company_name_hint=company_name_hint)

    responsibilities = extract_section(
        text,
        TARGET_SECTION_KEYWORDS["responsibilities"],
        BOUNDARY_HEADERS
    )

    qualifications = extract_section(
        text,
        TARGET_SECTION_KEYWORDS["qualifications"],
        BOUNDARY_HEADERS
    )

    preferred_qualifications = extract_section(
        text,
        TARGET_SECTION_KEYWORDS["preferredQualifications"],
        BOUNDARY_HEADERS
    )

    application_method = extract_section(
        text,
        TARGET_SECTION_KEYWORDS["applicationMethod"],
        BOUNDARY_HEADERS
    )

    hiring_steps = extract_hiring_steps(text)
    recruitment_period = extract_recruitment_period(text)
    hiring_count = extract_hiring_count(text)
    salary = extract_salary(text)
    education = extract_education(text)

    job_posting = {
        "companyName": company_name,
        "title": clean_name(title_hint),
        "recruitmentPeriod": recruitment_period,
        "imageUrl": image_url,
        "education": education,
        "qualifications": qualifications,
        "preferredQualifications": preferred_qualifications,
        "skills": "",
        "certifications": "",
        "salary": salary,
        "applicationMethod": application_method,
        "hiringCount": hiring_count,
        "responsibilities": responsibilities,
        "hiringSteps": hiring_steps,
        "sourceUrl": source_url,
        "postingType": "image"
    }

    job_posting["embeddingText"] = build_image_embedding_text(job_posting)

    return {
        "jobPosting": job_posting
    }