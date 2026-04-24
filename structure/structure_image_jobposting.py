import re
from typing import Any


# =========================
# 1. 기본 정리
# =========================
SECTION_ALIASES = {
    "responsibilities": ["담당업무", "주요업무", "업무내용", "상세내용", "직무소개"],
    "qualifications": ["자격요건", "지원자격", "필수조건", "자격사항"],
    "preferredQualifications": ["우대사항", "우대조건"],
    "applicationMethod": ["지원방법", "접수방법", "접수 방법"],
    "recruitmentPeriod": ["접수기한", "접수기간", "지원기간", "모집기간", "채용기간", "채용 일정"],
    "hiringProcess": ["전형절차", "채용절차", "전형절차는요", "전형 절차"],
    "workConditions": ["근무조건"],
    "salary": ["급여", "연봉", "월급", "시급"],
    "education": ["학력"],
    "experience": ["경력"],
    "hiringCount": ["모집인원", "채용인원"],
    "employmentType": ["근무형태", "고용형태"],
    "workTime": ["근무일시", "근무시간", "근무 시간", "운영시간"],
    "workLocation": ["근무지역", "근무지", "근무장소", "근무 지역"],
    "skills": ["스킬", "사용 가능 프로그램", "활용툴"],
    "companyInfo": ["회사소개", "About us", "우리 회사는요", "회사전경", "Office Environment", "Company Welfare", "병원소개", "ABOUT COMPANY"],
}

ALL_BOUNDARY_HEADERS = [
    "담당업무", "주요업무", "업무내용", "상세내용", "직무소개",
    "자격요건", "지원자격", "필수조건", "자격사항",
    "우대사항", "우대조건", "우대 사항",
    "지원방법", "접수방법", "접수 방법", "접수기한", "접수기간", "지원기간", "모집기간", "채용기간", "채용 일정",
    "전형절차", "채용절차", "전형절차는요", "전형 절차",
    "근무조건", "근무시간", "근무 시간", "근무일시", "근무형태", "고용형태", "근무지", "근무장소", "근무지역", "근무 지역", "운영시간",
    "학력", "경력", "급여", "연봉", "월급", "시급",
    "복리후생", "복지사항", "Welfare", "Company Welfare",
    "채용분야", "모집분야", "모집 분야", "모집인원", "채용인원",
    "회사소개", "About us", "우리 회사는요", "Office Environment", "병원소개", "ABOUT COMPANY",
    "제출서류", "접수 서류", "기타사항", "기타 사항",
]

NOISE_PATTERNS = [
    r"홈페이지\s*바로가기",
    r"SMC\s*홈페이지\s*바로가기",
    r"\*\s*면접일정은\s*추후\s*통보됩니다\.?",
]

MEANINGLESS_VALUES = {
    "",
    ".",
    ":",
    "-",
    "/",
    "및",
    "는요",
    "는요?",
    "참고",
    "하단 공고내용참고",
}

PLACEHOLDER_PATTERNS = [
    "상세내용을 입력하세요",
    "상세 내용을 입력하세요",
    "내용을 입력하세요",
    "상세내용 입력",
    "상세 내용 입력",
]

def is_placeholder_text(text: Any) -> bool:
    value = clean_text(text)
    if not value:
        return True
    normalized = re.sub(r"\s+", "", value)
    return any(re.sub(r"\s+", "", pattern) in normalized for pattern in PLACEHOLDER_PATTERNS)

def filter_placeholder_items(items: list[Any]) -> list[str]:
    return [sanitize_fragment(item) for item in items if sanitize_fragment(item) and not is_placeholder_text(item)]



# =========================
# 2. 클린 함수
# =========================
def clean_text(text: Any) -> str:
    if text is None:
        return ""

    text = str(text)
    text = text.replace("\r", "\n").replace("\t", " ")
    text = re.sub(r"[•·●◦▪▫▸▹►▶※◆■□☞★☆]", "ㆍ", text)
    text = re.sub(r"[—–―]+", "-", text)
    text = re.sub(r"[→⇒➜➝➞]+", ">", text)
    text = re.sub(r"\((월|화|수|목|금|토|일)\)", "", text)
    text = re.sub(r"[^0-9a-zA-Z가-힣\n\s\.,:/~>\-\(\)ㆍ&\[\]()%]", " ", text)
    text = re.sub(r"\s*ㆍ\s*", " ㆍ ", text)
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ ]+", " ", text)
    return text.strip()


def clean_multiline_text(text: Any) -> str:
    return clean_text(text)


def clean_name(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def clean_url(text: Any) -> str:
    return str(text or "").strip()


def clean_text_for_embedding(text: Any) -> str:
    if text is None:
        return ""

    text = str(text)
    text = re.sub(r"[•·●◦▪▫▸▹►▶※◆■□☞★☆]", " ", text)
    text = re.sub(r"\((월|화|수|목|금|토|일)\)", " ", text)
    text = re.sub(r"[^0-9a-zA-Z가-힣\s\.:/\-~]", " ", text)
    text = re.sub(r"\b[\.\-/:~]+\b", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def remove_text_noise(text: Any) -> str:
    text = clean_text(text)
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    return text.strip()


def sanitize_fragment(text: Any) -> str:
    value = clean_text(text)
    if not value:
        return ""

    value = re.sub(r"^(\.|:|>|,|/|-)\s*", "", value).strip()
    value = re.sub(r"\s+(\.|,|:)$", "", value).strip()
    value = re.sub(
        r"^(지원방법|접수방법|접수 방법|자격요건|지원자격|우대사항|우대 사항|전형절차|전형 절차|채용절차|근무조건|급여|학력|경력|근무형태|근무일시|근무지역|근무 지역|운영시간)\s*[:：]?\s*",
        "",
        value,
    )
    value = clean_text(value)

    if value.lower() in {x.lower() for x in MEANINGLESS_VALUES}:
        return ""
    if len(value) == 1 and value in {"/", ".", ":", "-"}:
        return ""

    return value


def split_bullets(text: Any) -> list[str]:
    text = clean_text(text)
    if not text:
        return []

    parts = re.split(
        r"\s*ㆍ\s*|\s{2,}|\s*>\s*|(?<=\))\s*-\s*|(?<=\w)\s*-\s+(?=[가-힣A-Za-z])|\n",
        text,
    )
    result = []
    for part in parts:
        part = sanitize_fragment(part)
        if part:
            result.append(part)
    return unique_preserve_order(result)


def unique_preserve_order(items: list[Any]) -> list[str]:
    seen = set()
    result = []

    for item in items:
        value = sanitize_fragment(item)
        if not value:
            continue
        norm = re.sub(r"\s+", " ", value).strip().lower()
        if norm not in seen:
            seen.add(norm)
            result.append(value)

    return result


def flatten_to_list(value: Any) -> list[str]:
    result = []
    if value is None:
        return result
    if isinstance(value, list):
        for item in value:
            result.extend(flatten_to_list(item))
    elif isinstance(value, dict):
        for v in value.values():
            result.extend(flatten_to_list(v))
    else:
        txt = sanitize_fragment(value)
        if txt:
            result.append(txt)
    return result


# =========================
# 3. meta 보정
# =========================
def _get_meta_value(posting: dict, key: str) -> str:
    meta = posting.get("meta", {}) or {}
    return posting.get(key, "") or meta.get(key, "")


def get_meta_company(posting: dict) -> str:
    return clean_name(_get_meta_value(posting, "companyName"))


def get_meta_title(posting: dict) -> str:
    return clean_name(_get_meta_value(posting, "title"))


def get_meta_url(posting: dict) -> str:
    return clean_url(_get_meta_value(posting, "sourceUrl"))


def get_meta_image_url(posting: dict) -> str:
    return clean_url(_get_meta_value(posting, "imageUrl"))


# =========================
# 4. 섹션 추출
# =========================
def extract_section(text: str, start_keywords: list[str], boundary_headers: list[str]) -> str:
    text = remove_text_noise(text)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return ""

    start_idx = -1
    for i, line in enumerate(lines):
        for keyword in start_keywords:
            if keyword.lower() in line.lower():
                start_idx = i
                break
        if start_idx != -1:
            break

    if start_idx == -1:
        return ""

    collected = []
    first_line = lines[start_idx]

    first_removed = first_line
    for keyword in start_keywords:
        first_removed = re.sub(re.escape(keyword), "", first_removed, flags=re.IGNORECASE)
    first_removed = sanitize_fragment(first_removed)
    if first_removed:
        collected.append(first_removed)

    for j in range(start_idx + 1, len(lines)):
        line = lines[j]

        hit_boundary = False
        for header in boundary_headers:
            if any(header.lower() == k.lower() for k in start_keywords):
                continue
            if header.lower() in line.lower():
                hit_boundary = True
                break

        if hit_boundary:
            break

        cleaned = sanitize_fragment(line)
        if cleaned:
            collected.append(cleaned)

    return "\n".join(unique_preserve_order(collected))


def extract_all_sections(text: str) -> dict:
    sections = {}
    for key, keywords in SECTION_ALIASES.items():
        value = extract_section(text, keywords, ALL_BOUNDARY_HEADERS)
        if value:
            sections[key] = value
    return sections


def extract_tagged_value(text: str, label: str, stop_labels: list[str] | None = None) -> str:
    text = clean_text(text)
    if not text or not label:
        return ""

    stop_labels = stop_labels or []
    if stop_labels:
        stop_pattern = "|".join(re.escape(x) for x in stop_labels)
        pattern = rf"{re.escape(label)}\s*[:：]?\s*(.*?)(?=(?:{stop_pattern})|$)"
    else:
        pattern = rf"{re.escape(label)}\s*[:：]?\s*(.*)$"

    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return ""
    return sanitize_fragment(match.group(1))


# =========================
# 5. 짧은 필드 보조 추출
# =========================
def clip_before_next_label(value: str) -> str:
    value = clean_text(value)
    if not value:
        return ""

    next_labels = [
        "접수기간", "지원방법", "접수방법", "접수 방법", "전형절차", "전형 절차", "채용절차",
        "복리후생", "복지사항", "유의사항", "문의처", "근무조건",
        "근무형태", "근무일시", "근무지역", "자격요건", "지원자격", "우대사항",
        "회사소개", "About us", "우리 회사는요", "기타사항", "기타 사항",
    ]
    pattern = "|".join(re.escape(x) for x in next_labels)
    value = re.split(rf"(?={pattern})", value)[0]
    return sanitize_fragment(value)


def extract_company_name(text: str, company_name_hint: str = "") -> str:
    company_name_hint = clean_name(company_name_hint)
    if company_name_hint:
        return company_name_hint

    text = remove_text_noise(text)
    explicit_patterns = [
        r"회사명\s*[:：]?\s*([가-힣A-Za-z0-9\(\)\[\]\.&,\- ]{1,40})",
        r"기업명\s*[:：]?\s*([가-힣A-Za-z0-9\(\)\[\]\.&,\- ]{1,40})",
        r"상호\s*[:：]?\s*([가-힣A-Za-z0-9\(\)\[\]\.&,\- ]{1,40})",
    ]

    for pattern in explicit_patterns:
        match = re.search(pattern, text)
        if match:
            company = clean_name(match.group(1))
            if 1 <= len(company) <= 30:
                return company
    return ""


def extract_recruitment_info(text: str, section_text: str = "") -> dict:
    text = clean_text(f"{section_text} {text}")

    is_rolling = any(
        x in text
        for x in ["상시채용", "채용시까지", "채용 시 마감", "채용 완료시까지", "채용 완료 시까지", "조기 마감"]
    )

    raw = ""
    start_date = ""
    end_date = ""

    korean_range = re.search(
        r"(\d{4}년\s*\d{1,2}월\s*\d{1,2}일\s*[~\-]\s*\d{4}년\s*\d{1,2}월\s*\d{1,2}일|\d{4}년\s*\d{1,2}월\s*\d{1,2}일\s*[~\-]\s*\d{1,2}월\s*\d{1,2}일)",
        text,
    )
    if korean_range:
        raw = clean_text(korean_range.group(1))

    if not raw:
        patterns = [
            r"(\d{4}[\.\-]\d{1,2}[\.\-]\d{1,2}\s*[~\-]\s*\d{4}[\.\-]\d{1,2}[\.\-]\d{1,2})",
            r"(\d{2,4}[\.\-]\d{1,2}[\.\-]\d{1,2}\s*[~\-]\s*\d{2,4}[\.\-]\d{1,2}[\.\-]\d{1,2})",
            r"시작일\s*(\d{4}[\.\-]\d{1,2}[\.\-]\d{1,2}).*?마감일\s*(\d{4}[\.\-]\d{1,2}[\.\-]\d{1,2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                raw = clean_text(match.group(0))
                if len(match.groups()) >= 2 and "시작일" in match.group(0):
                    start_date = match.group(1).replace(".", "-")
                    end_date = match.group(2).replace(".", "-")
                break

    if not raw and is_rolling:
        if "상시채용" in text:
            raw = "상시채용"
        elif "채용 시 마감" in text or "채용시까지" in text or "채용시 마감" in text:
            raw = "채용 시 마감"
        elif "채용 완료시까지" in text or "채용 완료 시까지" in text:
            raw = "채용 완료시까지"
        elif "조기 마감" in text:
            raw = "조기 마감 가능"

    return {
        "raw": sanitize_fragment(raw),
        "startDate": start_date,
        "endDate": end_date,
        "isRolling": is_rolling,
    }


def extract_hiring_count(text: str, section_text: str = "") -> str:
    text = clean_text(f"{section_text} {text}")
    patterns = [
        r"모집인원\s*[:：]?\s*([0-9○O]+명)",
        r"채용인원\s*[:：]?\s*([0-9○O]+명)",
        r"\(\s*([0-9○O]+명)\s*\)",
        r"\b([0-9○O]+명)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return clean_text(match.group(1)).replace("O", "○")
    return ""


def extract_salary(text: str, salary_section: str = "", work_section: str = "") -> str:
    base = clean_text(" ".join([salary_section, work_section, text]))
    patterns = [
        r"(연봉\s*[:：]?\s*[^ ]+(?:\s*만원|\s*원)?)",
        r"(월급\s*[:：]?\s*[^ ]+(?:\s*만원|\s*원)?)",
        r"(시급\s*[:：]?\s*[^ ]+(?:\s*원)?)",
        r"(급여\s*[:：]?\s*[^ ]+(?:\s*만원|\s*원)?)",
        r"(월\s*[0-9,]+\s*만원)",
        r"(면접시\s*협의)",
        r"([0-9,]+\s*원)",
    ]
    for pattern in patterns:
        match = re.search(pattern, base, flags=re.IGNORECASE)
        if match:
            return sanitize_fragment(match.group(1))
    return ""


def extract_education(text: str, education_section: str = "", qualification_section: str = "", work_section: str = "") -> str:
    candidates = [education_section, qualification_section, work_section, text]
    joined = clean_text(" ".join([x for x in candidates if x]))

    patterns = [
        r"(학력무관)",
        r"학력\s*[:：]?\s*([^\s][^\.]+?)(?=(경력|자격요건|우대사항|지원방법|전형절차|근무조건|$))",
        r"(고졸이상|고졸 이상|초대졸이상|초대졸 이상|대졸이상|대졸 이상|학사이상|석사이상|박사이상)",
    ]

    for pattern in patterns:
        match = re.search(pattern, joined)
        if match:
            return sanitize_fragment(match.group(1))
    return ""


def normalize_employment_type(text: str) -> str:
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


def extract_experience_type(text: str) -> str:
    text = clean_text(text)

    patterns = [
        r"(신입/경력)",
        r"(신입\s*및\s*경력)",
        r"(신입\s*또는\s*경력)",
        r"(신입)",
        r"(경력무관)",
        r"(경력)",
        r"(\d+\s*~\s*\d+\s*년)",
        r"(\d+\s*년\s*이상)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return sanitize_fragment(match.group(1))

    return ""


def extract_work_hours(text: str) -> list[str]:
    text = clean_text(text)
    hours = re.findall(r"\d{1,2}:\d{2}\s*[\-~]\s*\d{1,2}:\d{2}", text)
    return unique_preserve_order(hours)


def extract_location(text: str) -> str:
    text = clean_text(text)
    patterns = [
        r"근무지역\s*[:：]?\s*(.*?)(?=(접수기간|지원방법|접수방법|접수 방법|전형절차|전형 절차|채용절차|복리후생|유의사항|문의처|기타사항|기타 사항|$))",
        r"근무지\s*[:：]?\s*(.*?)(?=(접수기간|지원방법|접수방법|접수 방법|전형절차|전형 절차|채용절차|복리후생|유의사항|문의처|기타사항|기타 사항|$))",
        r"근무장소\s*[:：]?\s*(.*?)(?=(접수기간|지원방법|접수방법|접수 방법|전형절차|전형 절차|채용절차|복리후생|유의사항|문의처|기타사항|기타 사항|$))",
        r"(서울특별시\s+[가-힣0-9\s\-로길번지]+)",
        r"(경기도\s+[가-힣0-9\s\-로길번지]+)",
        r"(부산광역시\s+[가-힣0-9\s\-로길번지]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return sanitize_fragment(match.group(1))
    return ""


def extract_short_application_method(text: str) -> str:
    text = clean_text(text)
    if not text:
        return ""

    patterns = [
        r"접수방법\s*[:：]?\s*(.*?)(?=(이력서\s*양식|지원양식|첨부서류|접수 서류|유의사항|전형절차|전형 절차|채용절차|복리후생|문의처|근무조건|기타사항|기타 사항|$))",
        r"지원방법\s*[:：]?\s*(.*?)(?=(이력서\s*양식|지원양식|첨부서류|접수 서류|유의사항|전형절차|전형 절차|채용절차|복리후생|문의처|근무조건|기타사항|기타 사항|$))",
        r"접수 방법\s*[:：]?\s*(.*?)(?=(이력서\s*양식|지원양식|첨부서류|접수 서류|유의사항|전형절차|전형 절차|채용절차|복리후생|문의처|근무조건|기타사항|기타 사항|$))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return sanitize_fragment(match.group(1))

    return sanitize_fragment(text[:80])


def extract_department(text: str) -> str:
    text = clean_text(text)
    dept_patterns = [
        r"모집분야\s*[:：]?\s*([^\n]+?)(?=(모집인원|모집기간|근무조건|자격요건|$))",
        r"모집 분야\s*[:：]?\s*([^\n]+?)(?=(모집인원|모집기간|근무조건|자격요건|$))",
        r"([가-힣A-Za-z0-9/ ]+팀\s*[가-힣A-Za-z0-9/ ]*)",
        r"([가-힣A-Za-z0-9/ ]+사무/?경리)",
    ]
    for pattern in dept_patterns:
        match = re.search(pattern, text)
        if match:
            value = sanitize_fragment(match.group(1))
            if value and len(value) <= 40:
                return value
    return ""


def extract_skills_from_text(text: str) -> list[str]:
    text = clean_text(text)
    known_skills = [
        "Python", "Java", "C", "C++", "C#", "JavaScript", "TypeScript", "React", "Next.js", "Node.js",
        "Spring", "Django", "Flask", "TensorFlow", "PyTorch", "SQL", "MySQL", "PostgreSQL", "MongoDB",
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git", "Figma", "Photoshop", "Illustrator",
        "엑셀", "ERP", "운전", "OA", "한글", "워드", "파워포인트", "SolidWorks", "Fusion", "Arduino", "MCU", "CAD",
        "안경사", "간호사", "간호조무사", "IM", "IV", "MR",
    ]

    found = []
    low_text = text.lower()
    for skill in known_skills:
        if skill.lower() in low_text:
            found.append(skill)
    return unique_preserve_order(found)


# =========================
# 6. 섹션 기반 파싱
# =========================
def parse_responsibilities(sections: dict, text: str) -> list[str]:
    raw = sections.get("responsibilities", "")
    items = split_bullets(raw)

    if not items and raw:
        items = [sanitize_fragment(raw)]

    cleaned = []
    blocked_keywords = [
        "근무환경", "복리후생", "회사전경", "구내식당", "주차장", "자유로운 연차", "복장",
        "상조회가입", "출퇴근", "오더량", "인프라", "우리 회사는요", "About us",
        "Company Welfare", "Office Environment", "최종 합격", "접수 방법", "기타사항",
        "병원소개", "Welfare",
        "접수 안내", "접수기간", "접수방법", "온라인접수", "당사채용홈페이지",
        "전형절차", "기타사항", "문의", "채용홈페이지", "지원하기",
    ]

    for item in items:
        if any(keyword.lower() in item.lower() for keyword in blocked_keywords):
            continue
        if is_placeholder_text(item):
            continue
        cleaned.append(item)

    if not cleaned:
        lines = [line.strip() for line in clean_text(text).split("\n") if line.strip()]
        for line in lines:
            if re.search(r"(관리|응대|수술보조|상담|검사|진료보조|접수|조립|설계|개선|테스트|입력)", line):
                if not re.search(r"(우대사항|우대 사항|자격요건|복리후생|전형절차|전형 절차|접수방법|접수 방법)", line):
                    frag = sanitize_fragment(line)
                    if frag and not is_placeholder_text(frag):
                        cleaned.append(frag)

    return unique_preserve_order(cleaned[:8])


def parse_required_qualifications(sections: dict, text: str) -> list[str]:
    items = split_bullets(sections.get("qualifications", ""))

    if not items:
        qual = extract_tagged_value(
            clean_text(text),
            "지원자격",
            ["우대사항", "우대 사항", "전형절차", "전형 절차", "지원방법", "접수방법", "접수 방법", "근무조건"],
        )
        items.extend(split_bullets(qual))

    cleaned = []
    for item in items:
        if len(item) > 180:
            continue
        cleaned.append(item)

    return unique_preserve_order(cleaned)


def parse_preferred_qualifications(sections: dict, text: str) -> list[str]:
    items = split_bullets(sections.get("preferredQualifications", ""))
    if not items:
        pref = extract_tagged_value(
            clean_text(text),
            "우대사항",
            ["전형절차", "전형 절차", "지원방법", "접수방법", "접수 방법", "근무조건"],
        )
        items.extend(split_bullets(pref))

    cleaned = []
    for item in items:
        if len(item) > 180:
            continue
        cleaned.append(item)

    return unique_preserve_order(cleaned)


def parse_hiring_process(sections: dict) -> list[str]:
    raw = clean_text(sections.get("hiringProcess", ""))
    if not raw:
        return []

    raw = clip_before_next_label(raw)

    if ">" in raw:
        return unique_preserve_order([sanitize_fragment(x) for x in raw.split(">")])

    numbered = re.findall(
        r"(?:STEP\s*\d+|(?:\d+단계))?\s*(서류\s*전형|면접\s*전형|1차\s*면접|2차\s*면접|실무\s*면접|임원\s*면접|대면\s*면접|최종\s*합격|인적성)",
        raw,
    )
    if numbered:
        return unique_preserve_order(numbered)

    return unique_preserve_order(split_bullets(raw))


def parse_application_info(sections: dict, text: str) -> dict:
    raw = clean_text(sections.get("applicationMethod", ""))
    if not raw:
        raw = extract_tagged_value(
            clean_text(text),
            "접수 방법",
            ["접수 서류", "기타사항", "기타 사항", "전형 절차", "복리후생", "근무형태"],
        )

    method = ""
    if raw:
        m = re.search(
            r"(온라인\s*즉시\s*지원|잡코리아\s*입사지원|홈페이지\s*지원|이메일\s*지원|방문\s*접수)",
            raw,
            flags=re.IGNORECASE,
        )
        if m:
            method = sanitize_fragment(m.group(1))
        else:
            method = extract_short_application_method(raw)

    resume_form = ""
    match = re.search(r"(잡코리아\s*온라인\s*이력서|자사\s*양식|자유\s*양식|이력서,\s*자기소개서)", raw)
    if match:
        resume_form = sanitize_fragment(match.group(1))

    attachments = []
    if "이력서" in raw:
        attachments.append("이력서")
    if "자기소개서" in raw:
        attachments.append("자기소개서")

    return {
        "raw": raw,
        "method": method,
        "resumeForm": resume_form,
        "attachments": unique_preserve_order(attachments),
    }


def parse_company_info(text: str, sections: dict) -> dict:
    raw = clean_text(sections.get("companyInfo", ""))
    location = extract_location(sections.get("workConditions", "") or text)
    return {
        "companyType": "",
        "industry": "",
        "employeeCount": "",
        "location": location,
        "raw": raw,
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
# 7. 임베딩/legacy
# =========================
def build_embedding_text(job_posting: dict) -> dict:
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

    responsibilities_text = ", ".join(job_posting.get("responsibilities", [])[:5])
    requirements_text = ", ".join(
        (
            requirements.get("requiredSkills", [])
            + requirements.get("requiredQualifications", [])
            + requirements.get("coreCompetencies", [])
        )[:8]
    )
    preferred_text = ", ".join(
        (requirements.get("preferredSkills", []) + requirements.get("preferredQualifications", []))[:6]
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


def build_legacy_fields(job_posting: dict) -> dict:
    requirements = job_posting.get("requirements", {})
    work_conditions = job_posting.get("workConditions", {})
    application = job_posting.get("application", {})
    recruitment = job_posting.get("recruitment", {})
    company_info = job_posting.get("companyInfo", {})

    recruitment_period = ""
    if recruitment.get("startDate") and recruitment.get("endDate"):
        recruitment_period = f"{recruitment['startDate']} ~ {recruitment['endDate']}"
    elif recruitment.get("isRolling"):
        recruitment_period = recruitment.get("raw", "상시채용")
    else:
        recruitment_period = recruitment.get("raw", "")

    return {
        "companyName": job_posting.get("companyName", ""),
        "title": job_posting.get("title", ""),
        "recruitmentPeriod": recruitment_period,
        "imageUrl": job_posting.get("imageUrl", ""),
        "education": requirements.get("education", {}).get("minimum", ""),
        "qualifications": "\n".join(
            unique_preserve_order(
                requirements.get("requiredQualifications", []) + requirements.get("preferredQualifications", [])
            )
        ),
        "skills": "\n".join(requirements.get("requiredSkills", [])),
        "certifications": "\n".join(requirements.get("certifications", [])),
        "salary": work_conditions.get("salary", ""),
        "applicationMethod": "\n".join(
            unique_preserve_order(
                [application.get("method", ""), application.get("resumeForm", "")] + application.get("attachments", [])
            )
        ),
        "hiringCount": job_posting.get("job", {}).get("hiringCount", ""),
        "responsibilities": "\n".join(job_posting.get("responsibilities", [])),
        "companyDescription": company_info.get("raw", ""),
        "hiringSteps": job_posting.get("hiringProcess", []),
        "extraSections": job_posting.get("extraSections", {}),
        "sourceUrl": job_posting.get("sourceUrl", ""),
        "postingType": job_posting.get("postingType", "image"),
    }


# =========================
# 8. 메인 구조화
# =========================
def structure_jobposting_from_image(
    text: str,
    image_url: str = "",
    company_name_hint: str = "",
    title_hint: str = "",
    source_url: str = "",
    meta: dict | None = None,
) -> dict:
    meta = meta or {}
    raw_text = text or ""
    cleaned_text = remove_text_noise(raw_text)

    company_name = clean_name(company_name_hint or meta.get("companyName", ""))
    title = clean_name(title_hint or meta.get("title", ""))
    source_url = clean_url(source_url or meta.get("sourceUrl", ""))
    image_url = clean_url(image_url or meta.get("imageUrl", ""))

    if not company_name:
        company_name = extract_company_name(cleaned_text, "")

    sections = extract_all_sections(cleaned_text)

    responsibilities = parse_responsibilities(sections, cleaned_text)
    required_qualifications = parse_required_qualifications(sections, cleaned_text)
    preferred_qualifications = parse_preferred_qualifications(sections, cleaned_text)
    application_info = parse_application_info(sections, cleaned_text)
    recruitment = extract_recruitment_info(cleaned_text, sections.get("recruitmentPeriod", ""))
    hiring_process = parse_hiring_process(sections)
    company_info = parse_company_info(cleaned_text, sections)

    department = extract_department(cleaned_text)
    hiring_count = extract_hiring_count(cleaned_text, sections.get("hiringCount", ""))
    education = extract_education(
        cleaned_text,
        sections.get("education", ""),
        sections.get("qualifications", ""),
        sections.get("workConditions", ""),
    )
    experience = extract_experience_type(
        " ".join(
            [
                sections.get("experience", ""),
                sections.get("qualifications", ""),
                sections.get("preferredQualifications", ""),
                cleaned_text,
            ]
        )
    )
    employment_type = normalize_employment_type(
        " ".join([sections.get("employmentType", ""), sections.get("workConditions", ""), cleaned_text])
    )
    work_hours = extract_work_hours(
        " ".join([sections.get("workTime", ""), sections.get("workConditions", ""), cleaned_text])
    )
    salary = extract_salary(cleaned_text, sections.get("salary", ""), sections.get("workConditions", ""))
    location = extract_location(
        " ".join([sections.get("workLocation", ""), sections.get("workConditions", ""), cleaned_text])
    )

    required_skills = extract_skills_from_text(
        " ".join(
            [
                sections.get("skills", ""),
                sections.get("preferredQualifications", ""),
                sections.get("qualifications", ""),
                " ".join(responsibilities),
            ]
        )
    )

    preferred_skills = []
    for item in preferred_qualifications:
        low = item.lower()
        if any(
            k in low
            for k in [
                "excel", "erp", "엑셀", "figma", "photoshop", "illustrator",
                "solidworks", "fusion", "arduino", "cad", "im", "iv", "mr"
            ]
        ):
            preferred_skills.append(item)

    certifications = []
    for item in preferred_qualifications + required_qualifications:
        if len(item) > 80:
            continue
        if "자격증" in item or "보유자" in item:
            certifications.append(item)

    employment_type_raw = clean_text(sections.get("employmentType", ""))
    work_type = ""
    if employment_type_raw:
        m = re.search(r"(정규직|계약직|인턴|프리랜서)", employment_type_raw)
        if m:
            work_type = sanitize_fragment(m.group(1))
    if not work_type:
        work_type = employment_type

    responsibilities = unique_preserve_order([x for x in responsibilities if not is_placeholder_text(x)])
    required_qualifications = unique_preserve_order([x for x in required_qualifications if not is_placeholder_text(x) and not re.fullmatch(r"[0-9○O]+명", x) and x not in {"공통", "필수요건", "우대사항", "[필수요건]", "[우대사항]"}])
    preferred_qualifications = unique_preserve_order([x for x in preferred_qualifications if not is_placeholder_text(x)])
    required_skills = unique_preserve_order([x for x in required_skills if not is_placeholder_text(x)])

    job_posting = {
        "companyName": company_name,
        "title": title,
        "postingType": "image",
        "sourceUrl": source_url,
        "imageUrl": image_url,
        "recruitment": recruitment,
        "job": {
            "department": department,
            "hiringCount": hiring_count,
            "employmentType": employment_type,
            "positionLevel": [],
        },
        "requirements": {
            "education": {"minimum": education},
            "experience": {"type": experience},
            "requiredSkills": unique_preserve_order(required_skills),
            "preferredSkills": unique_preserve_order(preferred_skills),
            "requiredQualifications": unique_preserve_order(required_qualifications),
            "preferredQualifications": unique_preserve_order(preferred_qualifications),
            "coreCompetencies": [],
            "certifications": unique_preserve_order(certifications),
        },
        "responsibilities": unique_preserve_order(responsibilities),
        "workConditions": {
            "salary": salary,
            "workHours": unique_preserve_order(work_hours),
            "location": location or company_info.get("location", ""),
            "workType": work_type,
        },
        "application": application_info,
        "hiringProcess": unique_preserve_order(hiring_process),
        "notices": [],
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


# 예전 함수명 호환용
build_job_posting_from_image_crawl = structure_jobposting_from_image
