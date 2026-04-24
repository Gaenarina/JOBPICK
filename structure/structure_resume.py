import re
import uuid
from datetime import datetime
from typing import Any


# -----------------------------
# 1. 기본 설정
# -----------------------------
SECTION_ALIASES = {
    "basic": ["이력서"],
    "학력": ["학력", "학력사항", "최종학력"],
    "성적": ["성적"],
    "외국어": ["외국어", "외국어명", "어학"],
    "활용능력": [
        "컴퓨터 사용능력", "컴퓨터사용능력", "활용능력",
        "사용가능언어및TOOL", "사용가능 언어 및 TOOL"
    ],
    "자격증": ["자격증", "자격 및 면허", "자격증/면허증"],
    "활동": ["상벌", "상벌 경력", "기타활동", "수상내용"],
    "병역사항": ["병역", "병역사항"],
    "회사연혁": ["회사연혁", "사업목적", "사업목적 및 기대효과"],
    "경력사항": ["경력사항", "경력 사항", "전체경력"],
    "교육연수": ["교육/연수", "교육", "연수"],
    "프로젝트": ["수행 프로젝트", "프로젝트", "주요 프로젝트"],
    "자기소개서": ["자기소개서", "자기 소개서", "내용기술"],
    "기타": ["기타"],
}

SECTION_HEADERS = sorted(
    list({alias for aliases in SECTION_ALIASES.values() for alias in aliases}),
    key=len,
    reverse=True
)

LANGUAGE_TEST_NAMES = [
    "TOEIC", "TOEFL", "OPIc", "OPIC", "IELTS", "TEPS",
    "JLPT", "HSK", "TOEIC Speaking", "TOEFL iBT"
]

SKILL_KEYWORDS = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "C",
    "React", "Next.js", "Node.js", "Spring", "Django", "Flask",
    "TensorFlow", "PyTorch", "Pandas", "NumPy", "MySQL", "Oracle",
    "MongoDB", "Firebase", "Git", "Docker", "Kubernetes", "Linux",
    "SQL", "R", "Go", "Kotlin", "Swift", "PHP", "Vue", "Angular",
    "Excel", "ERP", "SAP", "Microsoft Office", "PowerPoint", "Word", "한글",
    "HTML", "CSS", "Photoshop", "Illustrator", "Figma", "Blender",
    "Tableau", "SPSS", "SolidWorks", "Fusion", "Arduino", "MCU",
    "React Native", "드림위버", "파워포인트"
]

CERT_KEYWORDS = [
    "정보처리기사", "정보처리산업기사", "정보처리기능사",
    "SQLD", "ADsP", "ADSP", "컴퓨터활용능력", "웹디자인기능사",
    "GTQ 포토샵", "지게차 운전기능사", "리눅스마스터",
    "한국사능력검정시험", "정보처리기능사"
]

JOB_CATEGORY_KEYWORDS = {
    "개발": [
        "개발", "백엔드", "프론트엔드", "프론트", "웹 퍼블리셔", "웹 개발",
        "AI", "소프트웨어", "머신러닝", "데이터사이언스", "UI 개발",
        "React", "Python", "JavaScript", "챗봇", "클라우드", "엔지니어"
    ],
    "데이터": [
        "데이터", "분석", "SQL", "Tableau", "SPSS", "ADsP",
        "머신러닝", "통계", "모델링", "보고서 작성"
    ],
    "디자인": [
        "디자인", "UI", "UX", "Figma", "Photoshop", "Illustrator",
        "Blender", "3D 모델링", "프로토타입", "ui설계", "UI설계"
    ],
    "기획/마케팅": [
        "기획", "마케팅", "서포터즈", "프레젠테이션", "공모전",
        "브랜드", "전략", "보고서 작성", "웹서비스기획", "모바일기획"
    ],
    "생산/품질": [
        "생산", "품질", "공정", "제조", "생산관리", "품질관리"
    ],
    "물류/재고": [
        "물류", "재고", "출고", "입고", "창고", "물류관리"
    ],
    "사무/경영지원": [
        "경리", "회계", "총무", "행정", "사무", "인사"
    ],
    "간호/의료": [
        "간호", "간호조무사", "안경사", "검안", "수술실", "병원"
    ],
}

POSITION_KEYWORDS = [
    "웹 퍼블리셔", "프론트엔드 개발자", "백엔드 개발자",
    "엔지니어", "연구원", "디자이너",
    "물류관리 사원", "생산관리 사원", "품질관리 사원",
    "물류관리", "생산관리", "품질관리",
    "기획", "기획자", "대리", "주임", "사원", "매니저",
    "인턴", "개발자", "간호사", "간호조무사", "검안사"
]

RESPONSIBILITY_HINTS = [
    "개발", "설계", "운영", "분석", "관리", "기획", "구현", "제작",
    "테스트", "배포", "유지보수", "재고", "출고", "입고", "품질",
    "생산", "AI", "챗봇", "클라우드", "모델링", "데이터", "보고서"
]


# -----------------------------
# 2. 공통 유틸
# -----------------------------
def clean_text(text: Any) -> str:
    if text is None:
        return ""
    text = str(text)
    text = text.replace("\r", "\n").replace("\t", " ")
    text = re.sub(r"[•·●◦▪▫▸▹►▶※◆■□☞★☆]", " ", text)
    text = re.sub(r"[ ]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def clean_inline_text(text: Any) -> str:
    return re.sub(r"\s+", " ", clean_text(text).replace("\n", " ")).strip()


def unique_preserve_order(items):
    seen = set()
    result = []

    for item in items:
        value = clean_inline_text(item)
        if not value:
            continue
        key = value.lower()
        if key not in seen:
            seen.add(key)
            result.append(value)

    return result


def normalize_date(text: str) -> str:
    text = clean_inline_text(text)
    if not text:
        return ""
    text = text.replace(".", "-").replace("/", "-")
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def normalize_month_date(text: str) -> str:
    text = normalize_date(text)
    if not text:
        return ""

    match = re.search(r"(\d{4})-(\d{1,2})(?:-(\d{1,2}))?", text)
    if not match:
        return text

    year = match.group(1)
    month = match.group(2).zfill(2)
    day = match.group(3)

    if day:
        return f"{year}-{month}-{day.zfill(2)}"
    return f"{year}-{month}"


def split_sentences(text: str):
    if not text:
        return []
    parts = re.split(r"[.!?\n]", clean_text(text))
    return unique_preserve_order([clean_inline_text(x) for x in parts if clean_inline_text(x)])


def alias_to_standard(header: str) -> str:
    header = clean_inline_text(header)
    for standard, aliases in SECTION_ALIASES.items():
        if header in aliases:
            return standard
    return header


def get_section_text(sections: dict, keys: list[str]) -> str:
    chunks = []
    for key in keys:
        if sections.get(key):
            chunks.append(sections[key])
    return clean_text("\n".join(chunks))


def extract_between(text: str, start_keywords, end_keywords):
    text = clean_text(text)
    if not text:
        return ""

    start_pattern = "|".join(re.escape(x) for x in start_keywords)
    end_pattern = "|".join(re.escape(x) for x in end_keywords)
    pattern = rf"(?:{start_pattern})\s*(.*?)(?=(?:{end_pattern})|$)"
    match = re.search(pattern, text, flags=re.DOTALL)
    return clean_text(match.group(1)) if match else ""


def parse_korean_duration_to_months(text: str) -> int:
    text = clean_inline_text(text)
    if not text:
        return 0

    year = 0
    month = 0

    y = re.search(r"(\d+)\s*년", text)
    m = re.search(r"(\d+)\s*개월", text)

    if y:
        year = int(y.group(1))
    if m:
        month = int(m.group(1))

    return year * 12 + month


def month_to_int(ym: str):
    if not ym:
        return None
    if ym == "현재":
        now = datetime.now()
        return now.year * 12 + now.month

    match = re.match(r"(\d{4})-(\d{2})", ym)
    if not match:
        return None

    year = int(match.group(1))
    month = int(match.group(2))
    return year * 12 + month


def months_to_years(months: int) -> int:
    return months // 12


def months_to_years_float(months: int) -> float:
    return round(months / 12, 1) if months > 0 else 0.0


def months_to_korean_career_text(months: int) -> str:
    years = months // 12
    remain = months % 12

    if years and remain:
        return f"{years}년 {remain}개월"
    if years:
        return f"{years}년"
    if remain:
        return f"{remain}개월"
    return "0개월"


# -----------------------------
# 3. OCR 텍스트 보정
# -----------------------------
def normalize_ocr_text(text: str) -> str:
    text = clean_text(text)

    replacements = {
        "이 력 서": "이력서",
        "이 력서": "이력서",
        "성 명": "성명",
        "생 년 월 일": "생년월일",
        "현 주 소": "현주소",
        "연 락 처": "연락처",
        "연 령": "연령",
        "회 사 명": "회사명",
        "업 종": "업종",
        "품 목": "품목",
        "학 력": "학력",
        "학 력 사 항": "학력사항",
        "외 국 어": "외국어",
        "컴퓨터 사용 능력": "컴퓨터 사용능력",
        "컴 퓨 터 사용능력": "컴퓨터사용능력",
        "컴퓨터사용 능력": "컴퓨터 사용능력",
        "자 격 증": "자격증",
        "자 격 및 면 허": "자격 및 면허",
        "면 허": "면허",
        "기 간": "기간",
        "근 무 기 간": "근무기간",
        "재 학 기 간": "재학기간",
        "부 전 공": "부전공",
        "복 수 전 공": "복수전공",
        "자 기 소 개 서": "자기소개서",
        "자 기 소개서": "자기소개서",
        "경 력 사 항": "경력사항",
        "경 력": "경력",
        "사 업 목 적": "사업목적",
        "회 사 연 혁": "회사연혁",
        "회사 연혁": "회사연혁",
        "사업 목적": "사업목적",
        "보 훈 대 상 여 부": "보훈대상여부",
        "병 역": "병역",
        "병 역 사 항": "병역사항",
        "병역 사항": "병역사항",
        "취 득 일": "취득일",
        "취 득 일 자": "취득일자",
        "일 자": "일자",
        "명 칭": "명칭",
        "내 용": "내용",
        "내용 기술": "내용기술",
        "사용가능 언어 및 TOOL": "사용가능언어및TOOL",
        "부서 / 직위": "부서/직위",
        "상벌경력": "상벌 경력",
        "회혁": "회사연혁",
        "회 혁": "회사연혁",
        "사 혁": "회사연혁",
        "경력 항": "경력사항",
        "경력항": "경력사항",
        "격 증": "자격증",
        "용기술": "내용기술",
        "자 기 소 개": "자기소개",
        "수 행 프로젝트": "수행 프로젝트",
        "교육 / 연수": "교육/연수",
        "기 타 활 동": "기타활동",
        "수 상 내 용": "수상내용",
        "자기 소개서": "자기소개서",
        "기간직장명": "기간 직장명",
        "성적기간": "성적 기간",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    word_fixes = {
        "참 여하며": "참여하며",
        "능 력": "능력",
        "모 델": "모델",
        "실 |용적인": "실용적인",
        "타 기": "기타",
        "타기": "기타",
        "간 특이사항": "특이사항",
        "보병전역": "보병 전역",
        "사업목적 및기대 효과": "사업목적 및 기대효과",
        "부전공/ 데이터사이언": "부전공 데이터사이언스",
        "ADSP": "ADsP",
        "ui설계": "UI설계",
        "웹서비스기획": "웹서비스기획",
        "모바일기획": "모바일기획",
        "경 험": "경험",
        "경력사 항": "경력사항",
        "내 기술": "내용기술",
        "내기술": "내용기술",
    }
    for old, new in word_fixes.items():
        text = text.replace(old, new)

    text = re.sub(r"([가-힣A-Za-z])\s*/\s*([가-힣A-Za-z])", r"\1/\2", text)

    section_like_headers = [alias for aliases in SECTION_ALIASES.values() for alias in aliases]
    for header in sorted(set(section_like_headers), key=len, reverse=True):
        text = re.sub(rf"\s*{re.escape(header)}\s*", f"\n{header} ", text)

    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ ]+", " ", text)
    return text.strip()


# -----------------------------
# 4. 섹션 분리
# -----------------------------
def split_resume_sections(text: str) -> dict:
    text = normalize_ocr_text(text)
    if not text:
        return {"basic": ""}

    sections = {"basic": ""}
    header_pattern = "|".join(sorted([re.escape(h) for h in SECTION_HEADERS], key=len, reverse=True))
    parts = re.split(rf"(?=({header_pattern})\b)", text)

    if parts:
        sections["basic"] = clean_text(parts[0])

    i = 1
    while i < len(parts) - 1:
        raw_header = clean_inline_text(parts[i])
        body = clean_text(parts[i + 1])

        if raw_header:
            standard = alias_to_standard(raw_header)
            if body.startswith(raw_header):
                body = clean_text(body[len(raw_header):])
            sections[standard] = clean_text((sections.get(standard, "") + "\n" + body).strip())

        i += 2

    return sections


# -----------------------------
# 5. 기본 정보
# -----------------------------
def extract_email(text: str) -> str:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group() if match else ""


def extract_phone(text: str) -> str:
    match = re.search(r"01[0-9]-?\d{3,4}-?\d{4}", text)
    return match.group() if match else ""


def extract_birth(text: str) -> str:
    patterns = [
        r"\d{4}[./-]\d{1,2}[./-]\d{1,2}",
        r"\d{2}[./-]\d{1,2}[./-]\d{1,2}",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_date(match.group())
    return ""


def extract_age(text: str):
    match = re.search(r"연령\s*(\d{1,2})", text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None

    match = re.search(r"(남|여|男|女)\s*,?\s*(\d{4})년생", text)
    if match:
        try:
            birth_year = int(match.group(2))
            current_year = datetime.now().year
            return current_year - birth_year + 1
        except ValueError:
            return None
    return None


def extract_name(text: str) -> str:
    text = normalize_ocr_text(text)

    patterns = [
        r"\(한글\)\s*([가-힣]{2,4})",
        r"성명\s*(?:\(한글\))?\s*([가-힣]{2,4})",
        r"이름\s*([가-힣]{2,4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    blocked = {
        "이력서", "회사명", "생산", "업종", "품목", "연령",
        "성명", "현주소", "연락처", "학력", "경력", "병역",
        "취미", "특기", "기타", "자격증", "외국어", "자기소개서",
        "카카오", "삼성", "엘지", "한양대학교", "경희대학교"
    }

    header = text[:150]
    candidates = re.findall(r"[가-힣]{2,4}", header)
    for cand in candidates:
        if cand not in blocked:
            return cand

    return ""


def extract_address(text: str) -> str:
    patterns = [
        r"현주소\s*(.*?)\s*(e-mail|email|긴급|연락처|학력|기간)",
        r"주소\s*(.*?)\s*(학력|학력사항|경력사항|외국어|어학|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return clean_inline_text(match.group(1))
    return ""


def extract_declared_experience_months(text: str) -> int:
    patterns = [
        r"전체경력\s*[:：]?\s*([0-9]+\s*년\s*[0-9]*\s*개월?)",
        r"경력\s*[:：]?\s*([0-9]+\s*년\s*[0-9]*\s*개월?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            months = parse_korean_duration_to_months(match.group(1))
            if months > 0:
                return months
    return 0


# -----------------------------
# 6. 학력
# -----------------------------
def extract_gpa(text: str):
    match = re.search(r"대학평균\s*(\d\.\d+)(?:\s*/\s*\d\.\d+)?", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None

    match = re.search(r"(\d\.\d+)\s*/\s*(4\.\d|5\.\d)", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None

    return None


def infer_degree_from_school(school: str) -> str:
    school = clean_inline_text(school)
    if "고등학교" in school:
        return "고졸"
    if "대학교" in school or school.endswith("대학"):
        return "학사"
    return ""


def extract_education_from_table(block: str):
    block = clean_text(block)
    if not block:
        return []

    results = []
    seen = set()

    # 박서연/강하린형 표
    pattern = re.finditer(
        r"(\d{4}[./-]\s*\d{1,2})\s*~\s*(\d{4}[./-]\s*\d{1,2})\s*([^\n]+)",
        block
    )

    for match in pattern:
        school_line = clean_inline_text(match.group(3))
        if not school_line:
            continue
        if not ("고등학교" in school_line or "대학교" in school_line or school_line.endswith("대학")):
            continue

        school = school_line
        major = ""
        major_match = re.search(r"([가-힣A-Za-z0-9·\-/]+학과)", school_line)
        if major_match:
            major = clean_inline_text(major_match.group(1))

        degree = infer_degree_from_school(school)

        item = {
            "school": school,
            "degree": degree,
            "major": major,
            "minor": "",
            "startDate": normalize_month_date(match.group(1)),
            "endDate": normalize_month_date(match.group(2)),
            "gpa": None,
            "status": "졸업" if "졸업" in school_line or degree == "고졸" else "",
        }

        key = (item["school"], item["degree"], item["startDate"], item["endDate"])
        if key not in seen:
            seen.add(key)
            results.append(item)

    return results


def extract_education(text: str, sections: dict):
    text = normalize_ocr_text(text)
    edu_block = get_section_text(sections, ["학력", "성적"])

    results = extract_education_from_table(edu_block)
    if results:
        # GPA 보정
        gpa = extract_gpa(text)
        if gpa is not None:
            for item in results:
                if item["degree"] == "학사" and item.get("gpa") is None:
                    item["gpa"] = gpa
        return results

    results = []
    seen = set()
    gpa = extract_gpa(text)

    for match in re.finditer(
        r"([가-힣A-Za-z0-9]+고등학교)\s*(졸업|재학)?",
        edu_block or text
    ):
        school = clean_inline_text(match.group(1))
        key = ("고졸", school)
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "school": school,
            "degree": "고졸",
            "major": "",
            "minor": "",
            "startDate": "",
            "endDate": "",
            "gpa": None,
            "status": clean_inline_text(match.group(2) or "졸업"),
        })

    for match in re.finditer(
        r"([가-힣A-Za-z0-9]+(?:대학교|대학))\s*([가-힣A-Za-z0-9·\-/]+학과)?",
        edu_block or text
    ):
        school = clean_inline_text(match.group(1))
        major = clean_inline_text(match.group(2) or "")
        key = ("학사", school, major)
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "school": school,
            "degree": "학사",
            "major": major,
            "minor": "",
            "startDate": "",
            "endDate": "",
            "gpa": gpa,
            "status": "졸업" if "졸업" in (edu_block or text) else "",
        })

    return results


# -----------------------------
# 7. 외국어
# -----------------------------
def infer_language_from_test(test_name: str) -> str:
    test_name_upper = test_name.upper()
    if "JLPT" in test_name_upper:
        return "일본어"
    if "HSK" in test_name_upper:
        return "중국어"
    return "영어"


def extract_language_tests(text: str, sections: dict):
    text = normalize_ocr_text(text)
    block = clean_inline_text(
        get_section_text(sections, ["외국어", "활용능력"]) + " " + text
    )

    results = []
    seen = set()

    def add_language(language: str, test_name: str, date: str = "", score: str = ""):
        item = {
            "language": language,
            "testName": test_name,
            "date": normalize_month_date(date),
            "score": clean_inline_text(score),
        }
        key = (item["language"], item["testName"], item["date"], item["score"])
        if item["testName"] and key not in seen:
            seen.add(key)
            results.append(item)

    for match in re.finditer(
        r"\bTOEIC\b\s*(20\d{2}[.-]\d{1,2})\s*(\d{3})\b",
        block,
        flags=re.IGNORECASE
    ):
        score = match.group(2)
        if 100 <= int(score) <= 990:
            add_language("영어", "TOEIC", match.group(1), score)

    for match in re.finditer(
        r"\b(TOEFL|IELTS|TEPS)\b\s*(20\d{2}[.-]\d{1,2})?\s*(\d{1,4}(?:\.\d)?)?",
        block,
        flags=re.IGNORECASE
    ):
        test = match.group(1).upper()
        add_language("영어", test, match.group(2) or "", match.group(3) or "")

    for match in re.finditer(
        r"\b(OPIc|OPIC)\b\s*(20\d{2}[.-]\d{1,2})?\s*(IM\d|IH|AL|AM|AH)?",
        block,
        flags=re.IGNORECASE
    ):
        add_language("영어", "OPIc", match.group(2) or "", (match.group(3) or "").upper())

    for match in re.finditer(
        r"\bHSK\s*([1-6])\b\s*(20\d{2}[.-]\d{1,2})?",
        block,
        flags=re.IGNORECASE
    ):
        add_language("중국어", "HSK", match.group(2) or "", match.group(1))

    for match in re.finditer(
        r"\bJLPT\s*(N\d)\b\s*(20\d{2}[.-]\d{1,2})?",
        block,
        flags=re.IGNORECASE
    ):
        add_language("일본어", "JLPT", match.group(2) or "", match.group(1).upper())

    return results


# -----------------------------
# 8. 스킬
# -----------------------------
def classify_skill(skill: str) -> str:
    languages = {
        "Python", "Java", "JavaScript", "TypeScript", "C", "C++", "C#", "SQL",
        "R", "Go", "Kotlin", "Swift", "PHP", "HTML", "CSS"
    }
    frameworks = {
        "React", "Next.js", "Node.js", "Spring", "Django", "Flask",
        "TensorFlow", "PyTorch", "Vue", "Angular", "React Native"
    }
    tools = {
        "Git", "Docker", "Kubernetes", "Firebase", "MySQL", "MongoDB",
        "Oracle", "Linux", "Pandas", "NumPy", "Excel", "ERP", "SAP",
        "Microsoft Office", "PowerPoint", "Word", "한글", "Figma", "Photoshop",
        "Illustrator", "Blender", "Tableau", "SPSS", "SolidWorks", "Fusion",
        "Arduino", "MCU", "드림위버", "파워포인트"
    }

    if skill in languages:
        return "languages"
    if skill in frameworks:
        return "frameworks"
    if skill in tools:
        return "tools"
    return "etc"


def extract_skills(text: str, sections: dict):
    text = normalize_ocr_text(text)
    skill_block = get_section_text(sections, ["활용능력", "외국어", "경력사항", "프로젝트", "자기소개서"]) or text

    found = []
    for keyword in SKILL_KEYWORDS:
        if re.search(rf"(?<![A-Za-z가-힣]){re.escape(keyword)}(?![A-Za-z가-힣])", skill_block, re.IGNORECASE):
            found.append(keyword)

    found = unique_preserve_order(found)

    result = {"languages": [], "frameworks": [], "tools": [], "etc": []}
    for skill in found:
        result[classify_skill(skill)].append(skill)

    return result


# -----------------------------
# 9. 자격증
# -----------------------------
def extract_certifications(text: str, sections: dict):
    text = normalize_ocr_text(text)

    # 섹션이 깨질 수 있으므로 자격증 섹션 + 활용능력 섹션 + 전체 텍스트를 함께 확인한다.
    block = clean_inline_text(
        get_section_text(sections, ["자격증", "활용능력"]) + " " + text
    )

    results = []

    def normalize_cert_name(name: str) -> str:
        name = clean_inline_text(name)
        if name.upper() == "ADSP":
            return "ADsP"
        return name

    def add_or_update_cert(name: str, grade: str = "", date: str = ""):
        name = normalize_cert_name(name)
        grade = clean_inline_text(grade)
        date = normalize_month_date(date)

        if not name:
            return

        # 같은 자격증 + 같은 등급이면 중복으로 추가하지 않고 날짜만 보정한다.
        for item in results:
            same_name = item.get("name", "").lower() == name.lower()
            same_grade = clean_inline_text(item.get("grade", "")) == grade
            if same_name and same_grade:
                if not item.get("date") and date:
                    item["date"] = date
                return

        results.append({
            "name": name,
            "grade": grade,
            "date": date,
        })

    # 자격증 표 구간만 먼저 좁혀서 연도 매칭 오류를 줄인다.
    cert_window = block
    cert_window_match = re.search(
        r"(컴퓨터\s*활용능력\s*(?:1급|2급)?.{0,80}?(?:ADsP|ADSP).{0,40}?20\d{2}.{0,10}?20\d{2})",
        block,
        flags=re.IGNORECASE
    )

    if cert_window_match:
        cert_window = cert_window_match.group(1)
        years = re.findall(r"20\d{2}", cert_window)

        comp_grade_match = re.search(r"컴퓨터\s*활용능력\s*(1급|2급)?", cert_window)
        if comp_grade_match:
            add_or_update_cert(
                "컴퓨터활용능력",
                comp_grade_match.group(1) or "",
                years[0] if len(years) >= 1 else ""
            )

        if re.search(r"ADsP|ADSP", cert_window, flags=re.IGNORECASE):
            add_or_update_cert(
                "ADsP",
                "",
                years[1] if len(years) >= 2 else ""
            )

    # 개별 패턴 보조 추출
    for match in re.finditer(
        r"컴퓨터\s*활용능력\s*(1급|2급)?\s*(?:취득|합격)?\s*(20\d{2}(?:[.-]\d{1,2})?)?",
        block,
        flags=re.IGNORECASE
    ):
        add_or_update_cert("컴퓨터활용능력", match.group(1) or "", match.group(2) or "")

    for match in re.finditer(
        r"(ADsP|ADSP)\s*(?:급)?\s*(?:취득|합격)?\s*(20\d{2}(?:[.-]\d{1,2})?)?",
        block,
        flags=re.IGNORECASE
    ):
        add_or_update_cert("ADsP", "", match.group(2) or "")

    for keyword in CERT_KEYWORDS:
        if keyword.upper() == "ADSP" or keyword == "컴퓨터활용능력":
            continue

        match = re.search(
            rf"{re.escape(keyword)}\s*(1급|2급)?\s*(?:취득|합격)?\s*(20\d{{2}}(?:[.-]\d{{1,2}})?)?",
            block,
            flags=re.IGNORECASE
        )
        if match:
            add_or_update_cert(keyword, match.group(1) or "", match.group(2) or "")

    # 날짜가 비어 있는 항목은 자격증 표 구간의 남은 연도로 보정한다.
    years = [normalize_month_date(y) for y in re.findall(r"20\d{2}(?:[.-]\d{1,2})?", cert_window)]
    used_dates = [item.get("date") for item in results if item.get("date")]
    remaining_years = [y for y in years if y not in used_dates]

    for item in results:
        if not item.get("date") and remaining_years:
            item["date"] = remaining_years.pop(0)

    return results


# -----------------------------
# 10. 활동 / 수상 / 교육연수
# -----------------------------
def extract_activities(text: str, sections: dict):
    text = normalize_ocr_text(text)
    block = get_section_text(sections, ["활동", "교육연수"])

    blocked_keywords = [
        "취미", "특기", "병역", "병역구분", "계급", "병과", "제대구분",
        "기간", "특이사항", "상벌", "경력", "명칭", "기관(단체)명", "일자", "내용"
    ]

    results = []

    for match in re.finditer(
        r"([가-힣A-Za-z0-9 \-]+(?:해커톤|경진대회|공모전|캡스톤(?: 디자인)?|교육|연수|활동))\s*(20\d{2}(?:[.-]\d{1,2})?)?\s*(대상|최우수상|우수상|장려상|1위|2위|3위|수상)?\s*([가-힣A-Za-z0-9협회대학교 ]+)?",
        block
    ):
        name = clean_inline_text(match.group(1))
        date = normalize_month_date(match.group(2) or "")
        award = clean_inline_text(match.group(3) or "")
        organization = clean_inline_text(match.group(4) or "")

        if not name:
            continue
        if any(bad in name for bad in blocked_keywords):
            continue

        results.append({
            "name": name,
            "organization": organization,
            "date": date,
            "award": award,
            "description": "",
        })

    dedup = []
    seen = set()
    for item in results:
        key = (item["name"], item["organization"], item["date"], item["award"])
        if key not in seen:
            seen.add(key)
            dedup.append(item)

    return dedup


# -----------------------------
# 11. 병역
# -----------------------------
def extract_military(text: str, sections: dict):
    text = normalize_ocr_text(text)
    block = get_section_text(sections, ["병역사항"])
    block = re.split(r"회사연혁|사업목적|경력사항|자기소개서|프로젝트", block)[0]

    # 빈 병역 표 헤더만 남은 경우를 제거
    block = re.sub(
        r"병역구분\s*계급\s*병과\(주특기\)\|?\s*제대구분\s*기간\s*(특이사항|사항)?",
        " ",
        block
    )
    block = re.sub(
        r"구분\s*계급\s*병과\(주특기\)\|?\s*제대구분\s*기간\s*(특이사항|사항)?",
        " ",
        block
    )
    block = clean_inline_text(block)

    branch = ""
    for cand in ["육군", "해군", "공군", "해병대", "보병"]:
        if cand in block:
            branch = "육군" if cand == "보병" else cand
            break

    rank = ""
    for cand in ["이병", "일병", "상병", "병장", "하사", "중사", "상사", "소위", "중위", "대위"]:
        if cand in block:
            rank = cand
            break

    status = ""
    if "만기제대" in block or "군필" in block or "전역" in block:
        status = "군필"
    elif "미필" in block:
        status = "미필"

    dates = re.findall(r"\d{4}[.-]\d{1,2}", block)

    result = {
        "branch": branch,
        "rank": rank,
        "status": status,
        "startDate": normalize_month_date(dates[0]) if len(dates) >= 1 else "",
        "endDate": normalize_month_date(dates[1]) if len(dates) >= 2 else "",
    }

    # 실제 병역 값이 하나도 없으면 빈 dict 대신 None으로 반환
    if not any(result.values()):
        return None

    return result

# -----------------------------
# 12. 경력
# -----------------------------
DATE_TOKEN_RE = r"(20\d{2}[.-]\d{1,2}|현재|재직중)"


def normalize_current_token(token: str) -> str:
    token = clean_inline_text(token)
    if token in {"현재", "재직중"}:
        return "현재"
    return normalize_month_date(token)


def infer_position(line: str) -> str:
    for pos in sorted(POSITION_KEYWORDS, key=len, reverse=True):
        if pos in line:
            return pos
    return ""


def looks_like_responsibility(token: str) -> bool:
    token = clean_inline_text(token)
    if not token:
        return False
    return any(hint in token for hint in RESPONSIBILITY_HINTS)


def normalize_org_candidate(org: str) -> str:
    org = clean_inline_text(org)
    if not org:
        return ""

    org = re.sub(r"^\d{4}-\d{2}\s*", "", org)
    org = re.sub(r"\s*\d{4}-\d{2}$", "", org)
    org = re.sub(r"\b(?:인턴|사원|주임|대리|과장|부장|매니저|개발자|연구원|디자이너|엔지니어|기획자?)\b.*$", "", org)
    org = re.sub(r"\s+", " ", org).strip()

    blocked = {
        "기간", "근무기간", "직장명", "근무회사", "부서", "부서/직위",
        "담당업무", "담당직무", "이직사유", "경력사항", "경력 사항"
    }
    if org in blocked:
        return ""

    return org


def merge_company_tokens(tokens: list[str]) -> str:
    tokens = [clean_inline_text(t) for t in tokens if clean_inline_text(t)]
    if not tokens:
        return ""

    merged = " ".join(tokens)
    merged = normalize_org_candidate(merged)
    return merged


def finalize_organization(org: str) -> str:
    org = clean_inline_text(org)
    org = re.sub(r"\b(인턴|사원|주임|대리|과장|부장|매니저|개발자|연구원|디자이너|엔지니어|기획)\b$", "", org).strip()
    return org


def infer_organization(line: str) -> str:
    line = clean_inline_text(line)

    special_orgs = [
        "카카오 엔터프라이즈",
        "삼성 SDS",
        "LG CNS",
        "NAVER Cloud",
        "네이버 클라우드",
        "㈜잡코리아",
        "잡코리아",
        "알바몬",
        "전자부품회사 B",
        "물류회사 A",
    ]
    for org in special_orgs:
        if org in line:
            return org

    patterns = [
        r"([㈜(주)주식회사 가-힣A-Za-z0-9&.\- ]+(?:회사|기업|공사|센터|공장|연구소|병원|의원|학교|학원|스튜디오|랩|CNS|SDS|엔터프라이즈)(?:\s+[A-Z0-9가-힣]{1,3})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            candidate = normalize_org_candidate(match.group(1))
            if candidate:
                return candidate

    tokens = line.split()
    company_tokens = []

    for tok in tokens:
        if re.fullmatch(r"\d{4}-\d{2}", tok):
            continue
        if tok in {"현재", "재직중"}:
            continue
        if tok in POSITION_KEYWORDS:
            continue
        if looks_like_responsibility(tok):
            break
        if tok in {"이직", "복귀", "종료"}:
            break
        company_tokens.append(tok)
        if len(company_tokens) >= 4:
            break

    return merge_company_tokens(company_tokens)


def infer_organization_from_row(row_text: str) -> str:
    row_text = clean_inline_text(row_text)
    if not row_text:
        return ""

    direct = infer_organization(row_text)
    if direct:
        return direct

    tokens = row_text.split()
    company_tokens = []

    for tok in tokens:
        if re.fullmatch(r"\d{4}-\d{2}", tok):
            continue
        if tok in {"현재", "재직중", "~"}:
            continue
        if tok in POSITION_KEYWORDS:
            continue
        if looks_like_responsibility(tok):
            break
        if tok in {"인턴", "사원", "주임", "대리", "과장", "부장"}:
            break
        company_tokens.append(tok)
        if len(company_tokens) >= 4:
            break

    return merge_company_tokens(company_tokens)


def repair_short_org_suffix(row_text: str, org: str) -> str:
    row_text = clean_inline_text(row_text)
    org = clean_inline_text(org)

    if not row_text or not org:
        return org

    m = re.search(rf"({re.escape(org)}\s+[A-Z0-9가-힣]{{1,3}}\b)", row_text)
    if m:
        return clean_inline_text(m.group(1))

    return org


def split_responsibilities(text: str):
    text = clean_inline_text(text)
    if not text:
        return []

    noise_patterns = [
        r"인턴 종료 및 학업 복귀",
        r"인턴 종료",
        r"계약 만기",
        r"정규직 전환",
        r"학업 복귀",
        r"이직",
        r"현재",
        r"재직중",
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, " ", text)

    parts = re.split(r",| 및 |/|\n", text)
    return unique_preserve_order([p for p in parts if clean_inline_text(p)])


def infer_reason_for_leaving(text: str) -> str:
    text = clean_inline_text(text)

    patterns = [
        r"(인턴 종료 및 학업 복귀)",
        r"(인턴 종료)",
        r"(계약 만기)",
        r"(학업 복귀)",
        r"([가-힣A-Za-z0-9 ,]+이직)",
        r"([가-힣A-Za-z0-9 ,]+복귀)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return clean_inline_text(match.group(1))

    return ""


def clean_responsibilities_list(responsibilities: list[str]) -> list[str]:
    cleaned = []

    for item in responsibilities:
        x = clean_inline_text(item)
        if not x:
            continue

        x = re.sub(r"^\d{2,4}-\d{1,2}\b", "", x).strip()
        x = re.sub(r"^[A-Z]\s+\d{4}-?$", "", x).strip()
        x = re.sub(r"^~\s*[A-Z]\s*", "", x).strip()

        # 경력표 뒤에 자기소개/확인 문구가 붙은 경우 강제 컷
        x = re.split(
            r"(경력사항|경력사\s*항|내용기술|내\s*용\s*기\s*술|저는|제가|작성자\s*:|자기소개서상의 모든 기재사항|자기소개서 상의 모든 기재사항|사실임을 확인합니다|기재사항)",
            x
        )[0].strip()

        x = re.sub(r"\b항$", "", x).strip()
        x = re.sub(r"^~\s*", "", x).strip()

        if not x:
            continue
        
        # 이직사유/종료사유로 보이는 문장은 담당업무에서 제거
        if re.search(r"(이직|학업\s*복귀|계약\s*만기|경험\s*확대|전문성\s*강화를\s*위해)", x):
            continue

        if len(x) > 30:
            continue
        if re.search(r"(저는|제가|작성자|기재사항|사실임을 확인합니다)", x):
            continue

        cleaned.append(x)

    return unique_preserve_order(cleaned)

def extract_experience_block(text: str, sections: dict) -> str:
    candidates = []

    exp_section = get_section_text(sections, ["경력사항"])
    if exp_section:
        candidates.append(exp_section)

    self_intro_block = get_section_text(sections, ["자기소개서"])
    if self_intro_block and ("기간" in self_intro_block or "근무기간" in self_intro_block or "직장명" in self_intro_block):
        match = re.search(
            r"((?:기간|근무기간)\s*(?:직장명|근무회사)\s*(?:부서/?직위|부서\s*직위|부서)?\s*(?:담당업무|담당직무)\s*(?:이직사유)?.*?)(?=(경력사항|내용기술|저는|제가|고등학교 졸업 후|대학 시절|학창 시절|자기소개서상의 모든 기재사항|작성자|기타|$))",
            self_intro_block,
            flags=re.DOTALL
        )
        if match:
            candidates.append(match.group(1))

    if not candidates:
        match = re.search(
            r"((?:기간|근무기간)\s*(?:직장명|근무회사)\s*(?:부서/?직위|부서\s*직위|부서)?\s*(?:담당업무|담당직무)\s*(?:이직사유)?.*?)(?=(경력사항|내용기술|저는|제가|고등학교 졸업 후|대학 시절|학창 시절|자기소개서상의 모든 기재사항|작성자|기타|$))",
            text,
            flags=re.DOTALL
        )
        if match:
            candidates.append(match.group(1))

    block = clean_text("\n".join(candidates))
    block = re.sub(r"\b경력사항\b", " ", block)
    block = re.sub(r"\b경력 사항\b", " ", block)
    return clean_inline_text(block)


def split_experience_chunks_by_dates(block: str):
    block = clean_inline_text(block)
    if not block:
        return []

    block = re.sub(r"^(기간|근무기간)\s*(직장명|근무회사)\s*(부서/?직위|부서\s*직위|부서)?\s*(담당업무|담당직무)\s*(이직사유)?\s*", "", block)
    block = re.sub(r"\s+", " ", block).strip()

    matches = list(re.finditer(DATE_TOKEN_RE, block))
    if len(matches) < 2:
        return []

    chunks = []
    i = 0

    while i + 1 < len(matches):
        start_match = matches[i]
        end_match = matches[i + 1]

        row_start = start_match.start()
        row_end = matches[i + 2].start() if i + 2 < len(matches) else len(block)

        row_text = clean_inline_text(block[row_start:row_end])

        if i == 0:
            prefix = clean_inline_text(block[:row_start])
            prefix = re.sub(r"^(기간|근무기간|직장명|근무회사|부서/?직위|담당업무|담당직무|이직사유)\s*", "", prefix)
            if prefix and len(prefix) <= 20 and any(hint in prefix for hint in RESPONSIBILITY_HINTS):
                row_text = clean_inline_text(prefix + " " + row_text)

        chunks.append({
            "startDate": normalize_current_token(start_match.group(1)),
            "endDate": normalize_current_token(end_match.group(1)),
            "rowText": row_text,
        })
        i += 2

    return chunks

def infer_responsibilities_from_row(text: str) -> list[str]:
    text = clean_inline_text(text)
    if not text:
        return []

    text = re.split(
        r"(경력사항|경력사\s*항|내용기술|내\s*용\s*기\s*술|저는|제가|작성자|기재사항|사실임을 확인합니다)",
        text
    )[0]

    text = re.sub(
        r"(인턴 종료 및 학업 복귀|인턴 종료|계약 만기|학업 복귀|정규직 전환|이직)",
        " ",
        text
    )

    text = re.sub(r"\b20\d{2}-\d{1,2}\b", " ", text)
    text = re.sub(r"\b현재\b|\b재직중\b", " ", text)
    text = re.sub(r"\s*~\s*", " ", text)

    org = infer_organization_from_row(text)
    pos = infer_position(text)

    for token in [org, pos]:
        if token:
            text = text.replace(token, " ")

    text = re.sub(r"\b(인턴|사원|주임|대리|과장|부장|매니저)\b", " ", text)
    text = re.sub(r"\b경\b", " ", text)
    text = clean_inline_text(text)

    parts = re.split(r",| 및 |/|\n", text)

    cleaned = []
    for p in parts:
        p = clean_inline_text(p)
        if not p:
            continue
        if len(p) < 2:
            continue
        if len(p) > 30:
            continue
        if re.search(r"(저는|제가|작성자|기재사항|사실임을 확인합니다)", p):
            continue
        if p in {"인턴", "사원"}:
            continue

        cleaned.append(p)

    return unique_preserve_order(cleaned)

def extract_experience_from_date_chunks(block: str):
    block = clean_inline_text(block)
    if not block:
        return []

    results = []

    for chunk in split_experience_chunks_by_dates(block):
        row_text = chunk["rowText"]

        org = infer_organization_from_row(row_text)
        org = repair_short_org_suffix(row_text, org)
        org = finalize_organization(org)

        pos = infer_position(row_text)
        reason = infer_reason_for_leaving(row_text)
        responsibilities = infer_responsibilities_from_row(row_text)

        # 2차 필터: OCR 찌꺼기와 자기소개 문장 제거
        filtered = []
        for r in responsibilities:
            r = clean_inline_text(r)
            if not r:
                continue

            r = re.sub(r"경력사\s*항?", "", r).strip()
            r = re.sub(r"내용기술", "", r).strip()

            if len(r) > 30:
                continue
            if r in {"인턴", "사원", "분석"}:
                continue
            if re.search(r"(저는|제가|작성자|기재사항|사실임을 확인합니다)", r):
                continue

            filtered.append(r)

        responsibilities = unique_preserve_order(filtered)
        responsibilities = clean_responsibilities_list(responsibilities)

        if not org:
            continue

        suffixless_org = normalize_company_name(org)
        filtered_responsibilities = []
        for r in responsibilities:
            rr = clean_inline_text(r)
            if rr == suffixless_org:
                continue
            if rr in {"A", "B"}:
                continue
            filtered_responsibilities.append(rr)

        reason = re.sub(r"^\d{1,2}\s*", "", clean_inline_text(reason))

        results.append({
            "organization": org,
            "department": "",
            "position": pos,
            "startDate": chunk["startDate"] if chunk["startDate"] != "현재" else "",
            "endDate": chunk["endDate"],
            "responsibilities": unique_preserve_order(filtered_responsibilities),
            "reasonForLeaving": reason,
            "source": "experience_table",
        })

    return results

def extract_experience_from_company_history(block: str):
    block = clean_text(block)
    if not block:
        return []

    results = []

    for match in re.finditer(r"([가-힣A-Za-z0-9㈜&.\- ]+(?:회사|기업|공장|병원|의원|CNS|엔터프라이즈|잡코리아|알바몬)(?:\s+[A-Z0-9가-힣]{1,3})?)\s*[: ]\s*([^\n]+)", block):
        org = clean_inline_text(match.group(1))
        desc = clean_inline_text(match.group(2))
        if not org or not desc:
            continue

        pos = "인턴" if "인턴" in desc else ""
        results.append({
            "organization": finalize_organization(org),
            "department": "",
            "position": pos,
            "startDate": "",
            "endDate": "",
            "responsibilities": split_responsibilities(desc),
            "reasonForLeaving": "",
            "source": "company_history",
        })

    return results


def extract_experience_from_dense_text(block: str):
    block = clean_inline_text(block)
    if not block:
        return []

    results = []
    results.extend(extract_experience_from_date_chunks(block))
    return results


def merge_experience_items(items):
    result = {}
    priority = {"experience_table": 0, "company_history": 1, "dense_text": 2, "": 9}

    for item in items:
        org = finalize_organization(clean_inline_text(item.get("organization", "")))
        pos = clean_inline_text(item.get("position", ""))
        start = clean_inline_text(item.get("startDate", ""))
        end = clean_inline_text(item.get("endDate", ""))
        source = clean_inline_text(item.get("source", ""))

        if not org:
            continue

        org_norm = normalize_company_name(org)
        key = (org_norm, start, end)

        current = {
            "organization": org,
            "department": clean_inline_text(item.get("department", "")),
            "position": pos,
            "startDate": start,
            "endDate": end,
            "responsibilities": unique_preserve_order(item.get("responsibilities", [])),
            "reasonForLeaving": clean_inline_text(item.get("reasonForLeaving", "")),
            "source": source,
        }

        if key not in result:
            result[key] = current
            continue

        existing = result[key]

        # source 우선순위
        if priority.get(source, 9) < priority.get(existing.get("source", ""), 9):
            merged = current
        else:
            merged = existing

        # position 보정
        if not merged.get("position"):
            merged["position"] = current.get("position") or existing.get("position")
        if merged.get("position") == "기획" and (current.get("position") == "인턴" or existing.get("position") == "인턴"):
            merged["position"] = "인턴"

        # responsibilities 짧고 깨끗한 쪽 우선, 합치기
        merged["responsibilities"] = unique_preserve_order(
            (existing.get("responsibilities", []) or []) +
            (current.get("responsibilities", []) or [])
        )

        # reason 보정
        if not merged.get("reasonForLeaving"):
            merged["reasonForLeaving"] = current.get("reasonForLeaving") or existing.get("reasonForLeaving")

        result[key] = merged

    return list(result.values())


def normalize_company_name(name: str) -> str:
    name = clean_inline_text(name)
    name = name.replace("㈜", "").replace("(주)", "").replace("주식회사", "").strip()
    return name


def repair_experience_organization_with_company_history(experience_items, company_history_items):
    if not experience_items:
        return experience_items

    history_orgs = []
    for item in company_history_items:
        org = clean_inline_text(item.get("organization", ""))
        if org:
            history_orgs.append(org)

    repaired = []
    for item in experience_items:
        new_item = dict(item)
        org = clean_inline_text(new_item.get("organization", ""))

        for hist_org in history_orgs:
            hist_norm = normalize_company_name(hist_org)
            org_norm = normalize_company_name(org)

            if org and len(org.split()) == 1 and hist_norm.startswith(org_norm) and hist_norm != org_norm:
                new_item["organization"] = hist_org
                break

            if hist_norm.startswith(org_norm + " ") and hist_norm != org_norm:
                new_item["organization"] = hist_org
                break

        repaired.append(new_item)

    return repaired


def drop_company_history_if_table_exists(experience_items):
    has_table_item = any(x.get("source") == "experience_table" for x in experience_items)
    if not has_table_item:
        return experience_items

    return [x for x in experience_items if x.get("source") != "company_history"]


def calculate_total_experience_months(experience: list[dict]) -> int:
    ranges = []

    for item in experience:
        start_i = month_to_int(item.get("startDate", ""))
        end_i = month_to_int(item.get("endDate", ""))

        if start_i is None or end_i is None:
            continue
        if end_i < start_i:
            continue

        ranges.append((start_i, end_i))

    if not ranges:
        return 0

    ranges.sort()
    merged = [list(ranges[0])]

    for s, e in ranges[1:]:
        last = merged[-1]
        if s <= last[1] + 1:
            last[1] = max(last[1], e)
        else:
            merged.append([s, e])

    total = 0
    for s, e in merged:
        total += (e - s + 1)

    return total


def extract_experience_items(text: str, sections: dict):
    text = normalize_ocr_text(text)

    exp_block = extract_experience_block(text, sections)
    table_items = extract_experience_from_date_chunks(exp_block)

    company_history_block = get_section_text(sections, ["회사연혁"])
    company_history_items = extract_experience_from_company_history(company_history_block)

    dense_block = get_section_text(sections, ["경력사항", "자기소개서"])
    dense_items = extract_experience_from_dense_text(dense_block)

    items = table_items + company_history_items + dense_items
    items = merge_experience_items(items)

    items = repair_experience_organization_with_company_history(items, company_history_items)
    items = drop_company_history_if_table_exists(items)
    items = merge_experience_items(items)

    return items


# -----------------------------
# 13. 프로젝트
# -----------------------------
def extract_projects_from_project_section(block: str, skills: dict):
    block = clean_text(block)
    if not block:
        return []

    projects = []

    project_chunks = re.split(r"(?=주요업무\(프로젝트명\))", block)
    current_company = ""
    current_department = ""
    current_role = ""

    company_match = re.search(r"회사명\s*([^\n]+)", block)
    if company_match:
        current_company = clean_inline_text(company_match.group(1))

    department_match = re.search(r"부서\s*([^\n]+)", block)
    if department_match:
        current_department = clean_inline_text(department_match.group(1))

    role_match = re.search(r"직급\s*([^\n]+)", block)
    if role_match:
        current_role = clean_inline_text(role_match.group(1))

    all_skills = (
        skills.get("languages", [])
        + skills.get("frameworks", [])
        + skills.get("tools", [])
        + skills.get("etc", [])
    )

    for chunk in project_chunks:
        if "주요업무(프로젝트명)" not in chunk:
            continue

        name_match = re.search(r"주요업무\(프로젝트명\)\s*([^\n]+)", chunk)
        period_match = re.search(r"프로젝트 기간\s*(\d{4}[./-]\d{1,2})\s*~\s*(\d{4}[./-]\d{1,2})", chunk)
        role_desc_match = re.search(r"주요역할 및 담당\s*([^\n]+)", chunk)
        achievement_match = re.search(r"업무 성과\s*([^\n]+)", chunk)

        name = clean_inline_text(name_match.group(1) if name_match else "")
        start_date = normalize_month_date(period_match.group(1)) if period_match else ""
        end_date = normalize_month_date(period_match.group(2)) if period_match else ""
        role_desc = clean_inline_text(role_desc_match.group(1) if role_desc_match else "")
        achievement = clean_inline_text(achievement_match.group(1) if achievement_match else "")

        tech_stack = []
        lowered = chunk.lower()
        for skill in all_skills:
            if skill.lower() in lowered:
                tech_stack.append(skill)

        if name:
            projects.append({
                "name": name,
                "organization": current_company,
                "role": current_role or current_department,
                "startDate": start_date,
                "endDate": end_date,
                "responsibilities": unique_preserve_order([role_desc]) if role_desc else [],
                "techStack": unique_preserve_order(tech_stack),
                "achievements": unique_preserve_order([achievement]) if achievement else [],
            })

    return projects


def extract_projects(text: str, sections: dict, skills: dict):
    project_block = get_section_text(sections, ["프로젝트"])
    projects = extract_projects_from_project_section(project_block, skills)
    if projects:
        return projects

    return []


# -----------------------------
# 14. 자기소개서 / 역량 / 직무분류
# -----------------------------
def extract_self_introduction(text: str, sections: dict):
    text = normalize_ocr_text(text)
    block = get_section_text(sections, ["자기소개서"])

    if not block:
        block = extract_between(text, ["자기소개서"], ["기타"])

    if not block:
        return ""

    start_keywords = [
        "저는", "제가", "고등학교 졸업 후", "대학 시절", "학창 시절",
        "성장과정", "성격소개", "학창시절 및 경력", "지원동기 및 포부"
    ]
    positions = [block.find(keyword) for keyword in start_keywords if keyword in block]
    if positions:
        block = block[min(positions):]

    block = re.split(
        r"(내용기술|기타|자기소개서\s*상의\s*모든\s*기재사항|자기소개서상의\s*모든\s*기재사항|"
        r"내\s*내\s*상의\s*모든\s*기재사항|상의\s*모든\s*기재사항|"
        r"위에\s*기재한\s*사항은\s*사실과\s*틀림이\s*없습니다|사실임을\s*확인합니다|작성자\s*:|"
        r"20\d{2}년\s*\d{1,2}월\s*\d{1,2}일)",
        block
    )[0]

    noise_patterns = [
        r"(기간|근무기간)\s*(직장명|근무회사)\s*(부서/?직위|부서)?\s*(담당업무|담당직무)\s*(이직사유)?",
        r"성\s*명\s*[:：].*$",
    ]
    for pattern in noise_patterns:
        block = re.sub(pattern, "", block, flags=re.MULTILINE)

    return clean_inline_text(block)

def extract_core_competencies(self_intro: str, skills: dict, experience: list):
    keywords = [
        "문제 해결", "협업", "데이터 분석", "데이터 기반", "머신러닝", "딥러닝",
        "논리적", "빠르게 학습", "커뮤니케이션", "책임감", "성실", "꼼꼼",
        "적응", "품질 관리", "생산 관리", "재고 관리", "출고 관리",
        "리더십", "기획", "프레젠테이션", "UI/UX", "3D 모델링",
        "웹서비스기획", "모바일기획", "클라우드 솔루션", "AI 챗봇",
        "보고서 작성"
    ]

    found = []
    corpus = " ".join(
        [self_intro]
        + [", ".join(v) for v in skills.values()]
        + [" ".join(x.get("responsibilities", [])) for x in experience]
    )

    for keyword in keywords:
        if keyword in corpus:
            found.append(keyword)

    return unique_preserve_order(found)


def extract_job_category(education, skills, experience, self_intro: str) -> str:
    corpus_parts = [self_intro]
    corpus_parts.extend([x.get("major", "") for x in education])
    corpus_parts.extend([", ".join(v) for v in skills.values()])
    corpus_parts.extend([" ".join(x.get("responsibilities", [])) for x in experience])

    corpus = " ".join(corpus_parts)

    for category, keywords in JOB_CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in corpus:
                return category

    return ""


# -----------------------------
# 15. 임베딩용 텍스트
# -----------------------------
def build_embedding_text(resume_data: dict):
    basic = resume_data.get("basicInfo", {})
    education = resume_data.get("education", [])
    skills = resume_data.get("skills", {})
    certifications = resume_data.get("certifications", [])
    projects = resume_data.get("projects", [])
    experience = resume_data.get("experience", [])
    self_intro = resume_data.get("selfIntroduction", "")
    job_category = resume_data.get("jobCategory", "")

    education_parts = []
    for item in education:
        part = " ".join([
            item.get("school", ""),
            item.get("major", ""),
            item.get("minor", ""),
            item.get("degree", "")
        ])
        part = clean_inline_text(part)
        if part:
            education_parts.append(part)

    skill_parts = (
        skills.get("languages", [])
        + skills.get("frameworks", [])
        + skills.get("tools", [])
        + skills.get("etc", [])
    )

    cert_parts = []
    for item in certifications:
        name = item.get("name", "")
        grade = item.get("grade", "")
        if name and grade:
            cert_parts.append(f"{name} {grade}")
        elif name:
            cert_parts.append(name)

    experience_parts = []
    for item in experience:
        org = clean_inline_text(item.get("organization", ""))
        pos = clean_inline_text(item.get("position", ""))
        resp = clean_inline_text(" ".join(item.get("responsibilities", [])))
        part = " / ".join([x for x in [org, pos, resp] if x])
        if part:
            experience_parts.append(part)

    project_parts = []
    for project in projects:
        project_parts.extend(project.get("responsibilities", []))
        project_parts.extend(project.get("techStack", []))
        project_parts.extend(project.get("achievements", []))

    summary_parts = [
        basic.get("name", ""),
        job_category,
        " / ".join(education_parts),
        ", ".join(skill_parts),
        ", ".join(cert_parts),
    ]

    summary = clean_inline_text(" / ".join([x for x in summary_parts if clean_inline_text(x)]))
    experience_text = clean_inline_text(" / ".join(unique_preserve_order(experience_parts)))
    project_text = clean_inline_text(" / ".join(unique_preserve_order(project_parts)))
    full_for_embedding = clean_inline_text(" / ".join([summary, experience_text, project_text, self_intro]))

    return {
        "summary": summary,
        "experience": experience_text,
        "projects": project_text,
        "fullForEmbedding": full_for_embedding,
    }


def sanitize_sections_for_output(sections: dict) -> dict:
    cleaned = {}

    for key, value in sections.items():
        v = clean_inline_text(value)

        if not v:
            cleaned[key] = ""
            continue

        if key == "병역사항":
            temp = re.sub(
                r"구분\s*계급\s*병과\(주특기\)\|?\s*제대구분\s*기간\s*(특이사항|사항)?",
                "",
                v
            )
            temp = re.sub(r"^(사항\s*)+$", "", clean_inline_text(temp))
            cleaned[key] = clean_inline_text(temp)
            continue

        if key == "자기소개서":
            if "저는" in v:
                v = v[v.find("저는"):]

            v = re.split(
                r"(내용기술|기타|자기소개서\s*상의\s*모든\s*기재사항|자기소개서상의\s*모든\s*기재사항|"
                r"내\s*내\s*상의\s*모든\s*기재사항|상의\s*모든\s*기재사항|"
                r"사실임을\s*확인합니다|작성자\s*:|20\d{2}년\s*\d{1,2}월\s*\d{1,2}일)",
                v
            )[0]

        cleaned[key] = clean_inline_text(v)

    return cleaned




# -----------------------------
# 15-1. 보강 추출: 학력 / 프로젝트 / 자기소개서
# -----------------------------
def enhance_education_from_full_text(text: str, education: list[dict]) -> list[dict]:
    """섹션 분리 실패로 학력이 비어 있을 때 전체 OCR 텍스트에서 학교를 보강 추출한다."""
    text = normalize_ocr_text(text)
    results = list(education or [])
    seen = {(x.get("school", ""), x.get("major", ""), x.get("degree", "")) for x in results}

    # 고등학교 보강
    for match in re.finditer(r"([가-힣A-Za-z0-9]+고등학교)\s*(?:\([^)]*\))?\s*(\d{4}[.-]\d{1,2})?", text):
        school = clean_inline_text(match.group(1))
        key = (school, "", "고졸")
        if school and key not in seen:
            seen.add(key)
            results.append({
                "school": school,
                "degree": "고졸",
                "major": "",
                "minor": "",
                "startDate": "",
                "endDate": normalize_month_date(match.group(2) or ""),
                "gpa": None,
                "status": "졸업",
            })

    # 대학교/대학 + 학과 보강
    for match in re.finditer(
        r"([가-힣A-Za-z0-9]+(?:대학교|대학))\s*([가-힣A-Za-z0-9·\-/]+학과)?(?:\s*\([^)]*\))?\s*(?:학)?\s*(\d{4}[.-]\d{1,2})?",
        text
    ):
        school = clean_inline_text(match.group(1))
        major = clean_inline_text(match.group(2) or "")
        key = (school, major, "학사")
        if school and key not in seen:
            seen.add(key)
            results.append({
                "school": school,
                "degree": "학사",
                "major": major,
                "minor": "",
                "startDate": "",
                "endDate": normalize_month_date(match.group(3) or ""),
                "gpa": extract_gpa(text),
                "status": "졸업" if normalize_month_date(match.group(3) or "") or re.search(rf"{re.escape(school)}.*?졸업", text) else "",
            })

    # 고졸과 학사가 같이 있으면 최종학력 판단용으로 둘 다 유지한다.
    return results


def enhance_self_introduction(text: str, sections: dict, current_self_intro: str) -> str:
    """자기소개서 섹션이 표 헤더만 잡힌 경우 경력사항/프로젝트 섹션에서 자기소개 문장을 복구한다."""
    current_self_intro = clean_inline_text(current_self_intro)
    if len(current_self_intro) >= 30:
        return current_self_intro

    candidates = []
    for key in ["자기소개서", "경력사항", "프로젝트"]:
        value = clean_inline_text(sections.get(key, ""))
        if value:
            candidates.append(value)

    combined = clean_inline_text(" ".join(candidates))
    if not combined:
        combined = clean_inline_text(text)

    # 자기소개 시작점 후보
    start_patterns = [
        r"(저는\s+.*)",
        r"(제가\s+.*)",
        r"(문제\s*해결\s*과정에서\s+.*)",
        r"(대학\s*시절\s+.*)",
        r"(학창\s*시절\s+.*)",
    ]

    for pattern in start_patterns:
        match = re.search(pattern, combined)
        if match:
            intro = match.group(1)
            intro = re.split(
                r"(내용기술|기타|자기소개서\s*상의\s*모든\s*기재사항|사실임을\s*확인합니다|작성자\s*:|20\d{2}년\s*\d{1,2}월\s*\d{1,2}일)",
                intro
            )[0]
            return clean_inline_text(intro)

    return current_self_intro


def enhance_projects_from_activities_and_intro(text: str, activities: list[dict], skills: dict, current_projects: list[dict]) -> list[dict]:
    """정형 프로젝트 섹션이 없어도 해커톤/캡스톤/공모전 활동을 프로젝트성 경험으로 보강한다."""
    projects = list(current_projects or [])
    seen = {clean_inline_text(p.get("name", "")).lower() for p in projects if p.get("name")}

    all_skills = unique_preserve_order(
        skills.get("languages", []) +
        skills.get("frameworks", []) +
        skills.get("tools", []) +
        skills.get("etc", [])
    )

    def add_project(name: str, organization: str = "", date: str = "", award: str = "", description: str = ""):
        name_clean = clean_inline_text(name)
        if not name_clean:
            return
        key = name_clean.lower()
        if key in seen:
            return
        seen.add(key)

        corpus = clean_inline_text(" ".join([name_clean, organization, description, text]))
        tech_stack = []
        for skill in all_skills:
            if re.search(rf"(?<![A-Za-z가-힣]){re.escape(skill)}(?![A-Za-z가-힣])", corpus, re.IGNORECASE):
                tech_stack.append(skill)

        responsibilities = []
        if "데이터" in corpus or "분석" in corpus:
            responsibilities.append("데이터 분석")
        if "알고리즘" in corpus:
            responsibilities.append("알고리즘 문제 해결")
        if "머신러닝" in corpus:
            responsibilities.append("머신러닝 프로젝트")
        if "협업" in corpus:
            responsibilities.append("협업")

        achievements = []
        if award:
            achievements.append(award)

        projects.append({
            "name": name_clean,
            "organization": clean_inline_text(organization),
            "role": "",
            "startDate": normalize_month_date(date),
            "endDate": normalize_month_date(date),
            "responsibilities": unique_preserve_order(responsibilities),
            "techStack": unique_preserve_order(tech_stack),
            "achievements": unique_preserve_order(achievements),
        })

    for activity in activities or []:
        name = clean_inline_text(activity.get("name", ""))
        if re.search(r"(해커톤|캡스톤|공모전|경진대회|프로젝트)", name):
            add_project(
                name=name,
                organization=activity.get("organization", ""),
                date=activity.get("date", ""),
                award=activity.get("award", ""),
                description=activity.get("description", ""),
            )

    # OCR상 활동 파싱이 실패한 경우 전체 텍스트에서 보조 추출
    for match in re.finditer(r"((?:AI\s*)?해커톤|교내\s*캡스톤\s*디자인|캡스톤\s*디자인|공모전)", text):
        add_project(match.group(1))

    return projects



# -----------------------------
# 15-1. 최종 보정
# -----------------------------
def final_clean_self_introduction(self_intro: str) -> str:
    value = clean_inline_text(self_intro)
    if not value:
        return ""

    value = value.replace("머신러닝 와", "머신러닝 프로젝트와")
    value = value.replace("프로젝트 와", "프로젝트와")
    value = re.sub(r"\s*내$", "", value).strip()
    value = re.split(
        r"(내용기술|기타|자기소개서\s*상의\s*모든\s*기재사항|자기소개서상의\s*모든\s*기재사항|사실임을\s*확인합니다|작성자\s*:)",
        value
    )[0]
    return clean_inline_text(value)


def final_fix_education_status(education: list[dict]) -> list[dict]:
    fixed = []
    for item in education or []:
        edu = dict(item)
        degree = clean_inline_text(edu.get("degree", ""))
        end_date = clean_inline_text(edu.get("endDate", ""))
        school = clean_inline_text(edu.get("school", ""))

        if degree == "학사" and end_date:
            edu["status"] = "졸업"
        elif "고등학교" in school:
            edu["status"] = edu.get("status") or "졸업"

        fixed.append(edu)
    return fixed


def final_dedup_projects(projects: list[dict]) -> list[dict]:
    if not projects:
        return []

    has_named_hackathon = any(
        "해커톤" in clean_inline_text(p.get("name", "")) and clean_inline_text(p.get("name", "")) != "해커톤"
        for p in projects
    )

    result = []
    seen = set()

    for project in projects:
        item = dict(project)
        name = clean_inline_text(item.get("name", ""))
        if not name:
            continue

        if name == "해커톤" and has_named_hackathon:
            continue

        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        item["responsibilities"] = unique_preserve_order(item.get("responsibilities", []))
        item["techStack"] = unique_preserve_order(item.get("techStack", []))
        item["achievements"] = unique_preserve_order(item.get("achievements", []))
        result.append(item)

    return result


def final_cleanup_resume_parts(education, projects, self_introduction):
    education = final_fix_education_status(education)
    projects = final_dedup_projects(projects)
    self_introduction = final_clean_self_introduction(self_introduction)
    return education, projects, self_introduction
# -----------------------------
# 16. 전체 구조화
# -----------------------------
def build_resume(preprocessed_text: str):
    text = normalize_ocr_text(preprocessed_text)
    sections = split_resume_sections(text)

    basic_info = {
        "name": extract_name(text),
        "birthDate": extract_birth(text),
        "age": extract_age(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "address": extract_address(text),
    }

    education = enhance_education_from_full_text(text, extract_education(text, sections))
    skills = extract_skills(text, sections)
    language_tests = extract_language_tests(text, sections)
    certifications = extract_certifications(text, sections)
    activities = extract_activities(text, sections)
    experience = extract_experience_items(text, sections)

    declared_experience_months = extract_declared_experience_months(text)
    calculated_experience_months = calculate_total_experience_months(experience)
    final_experience_months = calculated_experience_months if calculated_experience_months > 0 else declared_experience_months

    military = extract_military(text, sections)
    self_introduction = enhance_self_introduction(text, sections, extract_self_introduction(text, sections))
    projects = enhance_projects_from_activities_and_intro(text, activities, skills, extract_projects(text, sections, skills))

    # resume_data 생성 전에 최종 보정을 해야 Firestore 저장값과 embeddingText에 모두 반영된다.
    education, projects, self_introduction = final_cleanup_resume_parts(
        education,
        projects,
        self_introduction
    )

    core_competencies = extract_core_competencies(self_introduction, skills, experience)
    job_category = extract_job_category(education, skills, experience, self_introduction)

    resume_data = {
        "resumeId": str(uuid.uuid4()),
        "basicInfo": basic_info,
        "education": education,
        "skills": skills,
        "languageTests": language_tests,
        "certifications": certifications,
        "activities": activities,
        "experience": experience,
        "experienceSummary": {
            "totalMonths": final_experience_months,
            "years": months_to_years(final_experience_months),
            "yearsFloat": months_to_years_float(final_experience_months),
            "display": months_to_korean_career_text(final_experience_months),
            "declaredMonths": declared_experience_months,
            "calculatedMonths": calculated_experience_months,
            "source": "calculated" if calculated_experience_months > 0 else ("declared" if declared_experience_months > 0 else ""),
        },
        "projects": projects,
        "military": military,
        "selfIntroduction": self_introduction,
        "coreCompetencies": core_competencies,
        "jobCategory": job_category,
        "debugSections": sanitize_sections_for_output(sections),
        "rawText": text,
    }

    resume_data["embeddingText"] = build_embedding_text(resume_data)

    return {
        "resumeData": resume_data
    }


def structure_resume(preprocessed_text: str):
    return build_resume(preprocessed_text)
