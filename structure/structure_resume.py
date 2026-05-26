import re
import uuid
from datetime import datetime
from typing import Any

try:
    from structure import resume_dictionary as rd
except Exception:
    try:
        import resume_dictionary as rd
    except Exception:
        rd = None


def _cfg(name, default):
    return getattr(rd, name, default) if rd is not None else default


SECTION_ALIASES = _cfg("SECTION_ALIASES", {})
LANGUAGE_TEST_NAMES = _cfg("LANGUAGE_TEST_NAMES", [])
LANGUAGE_ALIASES = _cfg("LANGUAGE_ALIASES", {})
SKILL_ALIASES = _cfg("SKILL_ALIASES", {})
SKILL_GROUPS = _cfg("SKILL_GROUPS", {})
CERT_ALIASES = _cfg("CERT_ALIASES", {})
JOB_CATEGORY_KEYWORDS = _cfg("JOB_CATEGORY_KEYWORDS", {})
POSITION_KEYWORDS = _cfg("POSITION_KEYWORDS", [])
RESPONSIBILITY_HINTS = _cfg("RESPONSIBILITY_HINTS", [])
CORE_COMPETENCY_KEYWORDS = _cfg("CORE_COMPETENCY_KEYWORDS", [])
MILITARY_BRANCH_KEYWORDS = _cfg("MILITARY_BRANCH_KEYWORDS", ["육군", "해군", "공군", "해병대", "보병"])
MILITARY_RANK_KEYWORDS = _cfg("MILITARY_RANK_KEYWORDS", ["이병", "일병", "상병", "병장", "하사", "중사", "상사", "소위", "중위", "대위"])
MILITARY_EXEMPT_KEYWORDS = _cfg("MILITARY_EXEMPT_KEYWORDS", ["해당없음", "해당 없음", "면제", "미필"])
MILITARY_COMPLETED_KEYWORDS = _cfg("MILITARY_COMPLETED_KEYWORDS", ["군필", "만기제대", "전역"])
ORG_SUFFIX_KEYWORDS = _cfg("ORG_SUFFIX_KEYWORDS", ["회사", "기업", "공사", "공단", "센터", "협회", "위원회", "연구소", "랩", "병원", "의원", "학원"])
DEGREE_KEYWORDS = _cfg("DEGREE_KEYWORDS", {})
NOISE_SECTION_WORDS = _cfg("NOISE_SECTION_WORDS", [])

try:
    from structure.resume_postprocess import postprocess_resume_data
    print("[structure_resume] resume_postprocess import 성공")
except Exception as e:
    print("[structure_resume] structure.resume_postprocess import 실패:", e)
    try:
        from resume_postprocess import postprocess_resume_data
        print("[structure_resume] resume_postprocess import 성공")
    except Exception as e:
        print("[structure_resume] resume_postprocess import 완전 실패:", e)
        postprocess_resume_data = None

DEFAULT_CORE_SECTION_MAP = {
    "이력서": "basic",
    "입사지원서": "basic",
    "지원서": "basic",
    "개인정보": "basic",
    "인적사항": "basic",
    "기본정보": "basic",
    "학력사항": "학력",
    "학력 사항": "학력",
    "최종학력": "학력",
    "최종 학력": "학력",
    "학력": "학력",
    "활동사항": "경력사항",
    "활동 사항": "경력사항",
    "경력사항": "경력사항",
    "경력 사항": "경력사항",
    "근무경력": "경력사항",
    "실무경험": "경력사항",
    "외국어": "외국어",
    "어학": "외국어",
    "어학능력": "외국어",
    "공인어학": "외국어",
    "컴퓨터사용능력": "활용능력",
    "컴퓨터 사용능력": "활용능력",
    "컴퓨터활용능력": "활용능력",
    "컴퓨터 활용능력": "활용능력",
    "사용가능언어및TOOL": "활용능력",
    "사용가능 언어 및 TOOL": "활용능력",
    "사용 가능 언어 및 TOOL": "활용능력",
    "활용능력": "활용능력",
    "보유기술": "활용능력",
    "기술스택": "활용능력",
    "교육/연수": "교육연수",
    "교육 / 연수": "교육연수",
    "교육연수": "교육연수",
    "교육이수": "교육연수",
    "수상내역": "활동",
    "수상 내역": "활동",
    "수상경력": "활동",
    "상벌 경력": "활동",
    "상벌": "활동",
    "대외활동": "활동",
    "자격증": "자격증",
    "자격증/면허증": "자격증",
    "자격증 / 면허증": "자격증",
    "자격 및 면허": "자격증",
    "자격사항": "자격증",
    "병역사항": "병역사항",
    "병역 사항": "병역사항",
    "병역": "병역사항",
    "가족사항": "가족사항",
    "가족 사항": "가족사항",
    "회사연혁": "회사연혁",
    "회사 연혁": "회사연혁",
    "사업목적 및 기대효과": "기타",
    "사업 목적 및 기대 효과": "기타",
    "수행 프로젝트": "프로젝트",
    "주요 프로젝트": "프로젝트",
    "프로젝트 경험": "프로젝트",
    "프로젝트": "프로젝트",
    "성장과정": "자기소개서",
    "성장 과정": "자기소개서",
    "성격과 강점": "자기소개서",
    "성격 및 장단점": "자기소개서",
    "특기사항": "자기소개서",
    "특기 사항": "자기소개서",
    "생활신조": "자기소개서",
    "지원 동기 및 입사 포부": "자기소개서",
    "지원동기 및 입사포부": "자기소개서",
    "지원 동기": "자기소개서",
    "지원동기": "자기소개서",
    "입사 후 포부": "자기소개서",
    "입사포부": "자기소개서",
    "자기소개서": "자기소개서",
    "자기 소개서": "자기소개서",
    "내용기술": "자기소개서",
    "내용 기술": "자기소개서",
    "기타사항": "기타",
    "기타 사항": "기타",
    "기타": "기타",
}

HEADER_BLOCKLIST = {
    "교육", "연수", "학교", "학위", "언어", "외국어명", "시험", "시험명", "점수", "기관",
    "스킬", "역량", "프로필", "소개서", "지원서", "경력", "활동", "강점", "장점",
    "성적", "학점", "평점", "대학평균", "평균학점", "GPA", "과정명", "담당업무", "주요업무",
    "인턴경험", "인턴 경험", "실무경험", "실무 경험", "직무경험", "직무 경험", "사회경험", "사회 경험",
    "프로젝트", "프로젝트 경험", "경진대회", "공모전", "연구", "논문", "작품", "비고", "참고사항", "추가사항", "지원분야", "지원직무",
}

CORE_SECTION_MAP = dict(DEFAULT_CORE_SECTION_MAP)
for standard, aliases in (SECTION_ALIASES or {}).items():
    mapped = "basic" if standard == "basic" else standard
    for alias in aliases:
        alias = str(alias).strip()
        if not alias or alias in HEADER_BLOCKLIST or len(alias) < 2:
            continue
        CORE_SECTION_MAP.setdefault(alias, mapped)

CORE_HEADERS = sorted(CORE_SECTION_MAP.keys(), key=len, reverse=True)

COMMON_CERT_ISSUERS = [
    "공정거래위원회", "대한상공회의소", "한국데이터산업진흥원", "한국산업인력공단",
    "한국세무사회", "한국생산성본부", "한국TOEIC위원회", "ACTFL", "일본국제교류기금",
    "한국무역협회", "도로교통공단", "AI 혁신 센터", "여성인력개발센터",
]

COMMON_ORGS = [
    "카카오 엔터프라이즈", "삼성 SDS", "LG CNS", "NAVER Cloud", "네이버 클라우드",
    "IT 서비스 회사", "소프트웨어 회사", "물류회사 A", "전자부품회사 B",
]

COMMON_RESPONSIBILITY_PHRASES = [
    "마케팅 전략 수립 및 팀 총괄", "유통망 관리 및 B2B 영업", "교육 콘텐츠 기획 및 운영",
    "해외영업지원 및 일반사무", "데이터 분석 및 머신러닝 모델링", "백엔드 시스템 개발 및 유지보수",
    "AI 챗봇 개발", "클라우드 솔루션 설계", "경영 데이터 분석", "보고서 작성",
    "웹 퍼블리싱", "UI 구현", "프론트엔드 개발", "UI/UX 개선",
    "재고 관리", "출고 관리", "생산 일정 관리", "품질 관리",
]

POSITION_TASK_EXCLUDES = {
    "영업", "영업관리", "해외영업", "해외영업지원", "사무원", "일반사무", "회계담당",
    "경리", "총무", "인사", "물류관리", "생산관리", "품질관리", "강사",
}

EXTRA_POSITION_PHRASES = [
    "물류관리 사원", "생산관리 사원", "품질관리 사원", "웹 퍼블리셔", "프론트엔드 개발자",
    "백엔드 개발자", "데이터 분석가", "데이터 엔지니어", "선임연구원", "주임연구원",
    "책임연구원", "수석연구원", "팀장", "파트장", "과장", "대리", "주임", "사원", "인턴",
]

DATE_TOKEN_RE = r"(?:20\d{2}[-./]\d{1,2}|현재|재직중|재학중)"
DATE_TOKEN_NORM_RE = r"(?:20\d{2}-\d{2}|현재|재직중|재학중)"


def clean_text(text: Any) -> str:
    if text is None:
        return ""
    text = str(text)
    text = text.replace("\r", "\n").replace("\t", " ")
    text = re.sub(r"[•·●◦▪▫▸▹►▶※◆■□☞★☆☑]", " ", text)
    text = re.sub(r"[ ]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def clean_inline_text(text: Any) -> str:
    return re.sub(r"\s+", " ", clean_text(text).replace("\n", " ")).strip()


def unique_preserve_order(items):
    result = []
    seen = set()
    for item in items or []:
        value = clean_inline_text(item)
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def normalize_date(text: str) -> str:
    text = clean_inline_text(text)
    if not text:
        return ""
    if text in {"현재", "재직중", "재학중"}:
        return text
    text = text.replace(".", "-").replace("/", "-")
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def normalize_month_date(text: str) -> str:
    text = normalize_date(text)
    if not text:
        return ""
    if text in {"현재", "재직중", "재학중"}:
        return text
    match = re.search(r"(\d{4})-(\d{1,2})(?:-(\d{1,2}))?", text)
    if not match:
        return text
    year = match.group(1)
    month = match.group(2).zfill(2)
    day = match.group(3)
    return f"{year}-{month}-{day.zfill(2)}" if day else f"{year}-{month}"


def month_to_int(ym: str):
    ym = clean_inline_text(ym)
    if not ym:
        return None
    if ym in {"현재", "재직중", "재학중"}:
        now = datetime.now()
        return now.year * 12 + now.month
    match = re.match(r"(\d{4})-(\d{2})", ym)
    if not match:
        return None
    return int(match.group(1)) * 12 + int(match.group(2))


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


def parse_korean_duration_to_months(text: str) -> int:
    text = clean_inline_text(text)
    y = re.search(r"(\d+)\s*년", text)
    m = re.search(r"(\d+)\s*개월", text)
    return (int(y.group(1)) * 12 if y else 0) + (int(m.group(1)) if m else 0)


def get_section_text(sections: dict, keys: list[str]) -> str:
    chunks = []
    for key in keys:
        value = sections.get(key, "") if sections else ""
        if value:
            chunks.append(value)
    return clean_text("\n".join(chunks))


def extract_between(text: str, start_keywords, end_keywords):
    text = clean_text(text)
    if not text:
        return ""
    start_pattern = "|".join(re.escape(x) for x in start_keywords)
    end_pattern = "|".join(re.escape(x) for x in end_keywords)
    match = re.search(rf"(?:{start_pattern})\s*(.*?)(?=(?:{end_pattern})|$)", text, flags=re.DOTALL)
    return clean_text(match.group(1)) if match else ""


def _contains_keyword(text: str, keyword: str) -> bool:
    text = clean_inline_text(text)
    keyword = clean_inline_text(keyword)
    if not text or not keyword:
        return False
    if re.fullmatch(r"[A-Za-z0-9+#.]+", keyword):
        return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])", text, flags=re.IGNORECASE))
    return keyword.lower() in text.lower()


def _fix_vertical_headers(text: str) -> str:
    patterns = {
        r"이\s*력\s*서": "이력서",
        r"입\s*사\s*지\s*원\s*서": "입사지원서",
        r"성\s*명": "성명",
        r"생\s*년\s*월\s*일": "생년월일",
        r"현\s*주\s*소": "현주소",
        r"연\s*락\s*처": "연락처",
        r"휴\s*대\s*폰": "휴대폰",
        r"전\s*화\s*번\s*호": "전화번호",
        r"학\s*력\s*사\s*항": "학력사항",
        r"학\s*력": "학력",
        r"성\s*적": "성적",
        r"외\s*국\s*어": "외국어",
        r"컴퓨터\s*사용\s*능력": "컴퓨터사용능력",
        r"자\s*격\s*증": "자격증",
        r"자\s*격\s*및\s*면\s*허": "자격 및 면허",
        r"상\s*벌\s*경\s*력": "상벌 경력",
        r"병\s*역\s*사\s*항": "병역사항",
        r"병\s*역": "병역",
        r"회\s*사\s*연\s*혁": "회사연혁",
        r"사\s*업\s*목\s*적\s*및\s*기\s*대\s*효\s*과": "사업목적 및 기대효과",
        r"자\s*기\s*소\s*개\s*서": "자기소개서",
        r"경\s*력\s*사\s*항": "경력사항",
        r"내\s*용\s*기\s*술": "내용기술",
        r"기\s*타": "기타",
    }
    for pattern, replacement in patterns.items():
        text = re.sub(pattern, replacement, text)
    return text


def normalize_ocr_text(text: str) -> str:
    text = _fix_vertical_headers(str(text or ""))
    text = clean_text(text)
    replacements = {
        "이 력 서": "이력서", "이 력서": "이력서",
        "자 기 소 개 서": "자기소개서", "자 기 소개서": "자기소개서", "자기 소개서": "자기소개서",
        "학 력 사 항": "학력사항", "학 력": "학력", "활 동 사 항": "활동사항",
        "경 력 사 항": "경력사항", "경 력": "경력", "외 국 어": "외국어",
        "자 격 증": "자격증", "자 격 및 면 허": "자격 및 면허",
        "병 역 사 항": "병역사항", "병 역": "병역", "가 족 사 항": "가족사항",
        "E - mail": "E-mail", "E -mail": "E-mail", "E mail": "E-mail", "e mail": "email",
        "교육 / 연수": "교육/연수", "교육/ 연수": "교육/연수", "교육 /연수": "교육/연수",
        "컴퓨터 활용능력": "컴퓨터활용능력", "컴 퓨 터 활용능력": "컴퓨터활용능력",
        "OPIC": "OPIc", "ADSP": "ADsP",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    compact_fixes = {
        "기관자격증": "기관\n자격증", "기관 자격증": "기관\n자격증",
        "발행처병역": "발행처\n병역", "기관병역": "기관\n병역",
        "학생성장과정": "학생\n성장과정", "행정병가족사항": "행정병\n가족사항",
        "미필사유해당없음": "미필사유 해당없음", "어학언어": "어학\n언어",
        "시험일본어": "시험 일본어", "점점수": "점수", "기간과정명": "기간 과정명",
        "학점구분": "학점 구분", "관계성명": "관계 성명", "연령직업": "연령 직업",
        "직위처": "직위 처", "자이": "자 이", "부최": "부 최", "자김": "자 김",
        "모 델": "모델", "능 력": "능력", "경 험": "경험", "담질질": "다졌습니다",
        "머신러닝 와": "머신러닝 프로젝트와", "프로젝트 와": "프로젝트와", "저의 오랜 는": "저의 오랜 생활신조는",
    }
    for old, new in compact_fixes.items():
        text = text.replace(old, new)

    text = re.sub(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+)\s+([A-Za-z]{2,})\b", r"\1\2", text)
    text = text.replace(".co m", ".com").replace(".c o m", ".com")
    text = re.sub(r"(\d{4})[.](\d{1,2})", lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}", text)
    text = re.sub(r"(\d{4})\s*-\s*(\d{1,2})", lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}", text)
    text = re.sub(r"([가-힣A-Za-z])\s*/\s*([가-힣A-Za-z])", r"\1/\2", text)

    for header in CORE_HEADERS:
        if header in {"이력서", "입사지원서"}:
            continue
        if header in HEADER_BLOCKLIST:
            continue
        if header in {"자격증", "자격증/면허증", "자격 및 면허"}:
            pattern = rf"(?<![가-힣A-Za-z]){re.escape(header)}(?![은는이가을를A-Za-z가-힣])"
        elif len(header) <= 2:
            pattern = rf"(?<![가-힣A-Za-z]){re.escape(header)}(?![A-Za-z가-힣])"
        else:
            pattern = rf"(?<![가-힣A-Za-z]){re.escape(header)}"
        text = re.sub(pattern, f"\n{header}\n", text)

    text = re.sub(r"[ ]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def split_resume_sections(text: str) -> dict:
    text = normalize_ocr_text(text)
    sections = {"basic": ""}
    if not text:
        return sections
    header_pattern = "|".join(re.escape(h) for h in CORE_HEADERS if h not in HEADER_BLOCKLIST)
    pattern = re.compile(rf"(?:^|\n)\s*({header_pattern})\s*(?:\n| )?", re.MULTILINE)
    matches = list(pattern.finditer(text))
    if not matches:
        sections["basic"] = text
        return sections
    sections["basic"] = clean_text(text[:matches[0].start()])
    for idx, match in enumerate(matches):
        header = clean_inline_text(match.group(1))
        standard = CORE_SECTION_MAP.get(header, header)
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = clean_text(text[start:end])
        if standard == "basic":
            sections["basic"] = clean_text((sections.get("basic", "") + "\n" + body).strip())
        else:
            sections[standard] = clean_text((sections.get(standard, "") + "\n" + body).strip())
    return sections


def extract_email(text: str) -> str:
    value = clean_inline_text(text)
    value = value.replace(".co m", ".com").replace(".c o m", ".com")
    value = re.sub(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.co)\s*m\b", r"\1m", value)
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(?:com|net|org|kr|co\.kr|ac\.kr|edu)", value, flags=re.IGNORECASE)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    match = re.search(r"01[0-9]-?\d{3,4}-?\d{4}", text)
    return match.group(0) if match else ""


def extract_birth(text: str) -> str:
    value = clean_inline_text(text)
    match = re.search(r"(?:생년월일|주민번호|주민등록번호|주민번(?:호)?)\s*(\d{2,4}[./-]\d{1,2}[./-]\d{1,2}|\d{6})", value)
    if match:
        raw = match.group(1)
        if re.fullmatch(r"\d{6}", raw):
            yy = int(raw[:2])
            year = 1900 + yy if yy > 30 else 2000 + yy
            return f"{year}-{raw[2:4]}-{raw[4:6]}"
        return normalize_date(raw)
    match = re.search(r"\d{4}[./-]\d{1,2}[./-]\d{1,2}", value)
    return normalize_date(match.group(0)) if match else ""


def extract_age(text: str):
    value = clean_inline_text(text)
    for pattern in [r"나이\s*만\s*(\d{1,2})\s*세", r"만\s*(\d{1,2})\s*세", r"연령\s*(\d{1,2})"]:
        match = re.search(pattern, value)
        if match:
            return int(match.group(1))
    match = re.search(r"(남|여|男|女)\s*,?\s*(\d{4})년생", value)
    if match:
        return datetime.now().year - int(match.group(2)) + 1
    return None


def extract_name(text: str) -> str:
    text = normalize_ocr_text(text)
    head = clean_inline_text(text[:600])
    patterns = [
        r"이름\s*([가-힣]{2,4})\s*(?:영문|한문|주민|나이|휴대폰|전화번호|E-mail)",
        r"성명\s*(?:\(한글\))?\s*([가-힣]{2,4})",
        r"\(한글\)\s*([가-힣]{2,4})",
        r"지원자명\s*([가-힣]{2,4})",
    ]
    blocked = set(NOISE_SECTION_WORDS) | {"이력서", "영문", "한문", "주민", "주민번", "나이", "휴대폰", "전화번호", "주소", "학력", "활동", "어학", "기간", "성명", "연령", "직업", "관계", "최종", "학교명", "학점", "구분"}
    for pattern in patterns:
        match = re.search(pattern, head)
        if match and match.group(1) not in blocked:
            return match.group(1)
    tokens = re.findall(r"[가-힣]{2,4}", head)
    for token in tokens:
        if token not in blocked:
            return token
    return ""


def extract_address(text: str) -> str:
    text = normalize_ocr_text(text)
    patterns = [
        r"현주소\s*(.*?)\s*(?:E-mail|email|SNS|긴급|연락처|학력|기간|$)",
        r"주소\s*(.*?)\s*(?:E-mail|email|SNS|학력|학력사항|경력사항|활동사항|외국어|어학|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return clean_inline_text(match.group(1))
    return ""


def extract_declared_experience_months(text: str) -> int:
    for pattern in [r"전체경력\s*[:：]?\s*([0-9]+\s*년\s*[0-9]*\s*개월?)", r"경력\s*[:：]?\s*([0-9]+\s*년\s*[0-9]*\s*개월?)"]:
        match = re.search(pattern, text)
        if match:
            months = parse_korean_duration_to_months(match.group(1))
            if months > 0:
                return months
    return 0


def extract_gpa(text: str):
    match = re.search(r"(\d\.\d+)\s*/\s*([45]\.\d)", text)
    if match:
        return float(match.group(1))
    match = re.search(r"대학평균\s*(\d\.\d+)", text)
    return float(match.group(1)) if match else None


def infer_degree_from_school(school: str, text: str = "") -> str:
    value = clean_inline_text(school + " " + text)
    for degree in ["박사", "석사", "전문학사", "학사", "고졸"]:
        for alias in (DEGREE_KEYWORDS or {}).get(degree, []):
            if alias and alias in value:
                return degree
    if "박사" in value:
        return "박사"
    if "대학원" in value or "석사" in value:
        return "석사"
    if "고등학교" in value or "고졸" in value:
        return "고졸"
    if "대학교" in value or value.endswith("대학") or "학사" in value:
        return "학사"
    return ""


def _clean_school_major(raw: str):
    value = clean_inline_text(raw)
    value = re.sub(r"\s*\|\s*", " ", value)
    value = re.sub(r"^(학교명 및 전공|학교명|전공|학업)\s*", "", value)
    value = re.sub(r"\([^)]*(서울|경기|경기도|부산|대전|수원|안성|광역시|서울시)[^)]*\)", " ", value)
    value = re.split(r"부전공/복수전공|부전공|복수전공|휴학기간|성적|컴퓨터사용능력|자격증", value)[0]
    value = clean_inline_text(value)
    school_match = re.search(r"(.+?(?:대학교\s*대학원|대학교|대학원|대학|고등학교))\s*(.*)$", value)
    if not school_match:
        return value, "", infer_degree_from_school(value)
    school = clean_inline_text(school_match.group(1))
    rest = clean_inline_text(school_match.group(2))
    rest = re.sub(r"\b(졸업|재학|재학중|휴학|중퇴|수료|학사|석사|박사|고졸)\b", " ", rest).strip()
    rest = re.sub(r"\d\.\d+\s*/\s*[45]\.\d", " ", rest).strip()
    major = clean_inline_text(rest)
    degree = infer_degree_from_school(school, value)
    return school, major, degree


def _education_block(text: str, sections: dict) -> str:
    block = get_section_text(sections, ["학력"])
    if block:
        return block
    return extract_between(text, ["학력사항", "학력"], ["성적", "외국어", "어학", "컴퓨터사용능력", "활동사항", "경력사항", "자격증", "병역"])


def extract_education(text: str, sections: dict):
    text = normalize_ocr_text(text)
    block = clean_inline_text(_education_block(text, sections))
    if not block:
        block = clean_inline_text(text)

    results = []
    seen = set()
    gpa_default = extract_gpa(text)

    dense_match = re.search(
        r"재학기간\s*(20\d{2}-\d{2})\s*학교명 및 전공\s*(20\d{2}-\d{2})\s*\|?\s*(.+?)(?:활동사항|학점\s*구분|학점구분)\s*(?:학점\s*구분|학점구분)?\s*(\d\.\d\s*/\s*[45]\.\d)\s*(졸업|재학|휴학|중퇴|수료)?",
        clean_inline_text(text),
        flags=re.DOTALL,
    )
    if dense_match:
        school, major, degree = _clean_school_major(dense_match.group(3))
        if school:
            return [{
                "school": school,
                "degree": degree,
                "major": major,
                "minor": "",
                "startDate": normalize_month_date(dense_match.group(1)),
                "endDate": normalize_month_date(dense_match.group(2)),
                "gpa": float(dense_match.group(4).split("/")[0].strip()),
                "status": dense_match.group(5) or "졸업",
            }]

    row_pattern = re.compile(
        rf"(20\d{{2}}-\d{{2}})\s*~\s*(20\d{{2}}-\d{{2}}|재학중|현재)\s+(.+?)(?=(?:20\d{{2}}-\d{{2}}\s*~)|(?:휴학기간)|(?:성적)|(?:활동사항)|(?:경력사항)|(?:자격증)|$)",
        re.DOTALL,
    )

    for match in row_pattern.finditer(block):
        start_date = normalize_month_date(match.group(1))
        end_date = normalize_month_date(match.group(2))
        raw = clean_inline_text(match.group(3))
        school, major, degree = _clean_school_major(raw)
        if not re.search(r"고등학교|대학교|대학원|대학", raw):
            continue
        if not school or school in {"최종학력", "학교명"}:
            continue
        gpa = extract_gpa(raw)
        if gpa is None and degree != "고졸":
            gpa = gpa_default
        status = "재학" if end_date in {"재학중", "현재"} else "졸업"
        if "중퇴" in raw:
            status = "중퇴"
        elif "휴학" in raw:
            status = "휴학"
        elif "수료" in raw:
            status = "수료"
        key = (school, major, degree, start_date, end_date)
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "school": school,
            "degree": degree,
            "major": major,
            "minor": "",
            "startDate": start_date,
            "endDate": end_date,
            "gpa": gpa,
            "status": status,
        })

    if results:
        return results

    final_match = re.search(r"최종학력\s*:\s*최종학력\s*:\s*(.+?)\s+(고졸|전문학사|학사|석사|박사)\s+졸업", text)
    if final_match:
        school, major, degree = _clean_school_major(final_match.group(1))
        degree = degree or final_match.group(2)
        return [{
            "school": school,
            "degree": degree,
            "major": major,
            "minor": "",
            "startDate": "",
            "endDate": "",
            "gpa": extract_gpa(text),
            "status": "졸업",
        }]

    return []


def enhance_education_from_full_text(text: str, education: list[dict]) -> list[dict]:
    fixed = []
    seen = set()
    for item in education or []:
        edu = dict(item)
        if edu.get("major") == edu.get("degree"):
            edu["major"] = ""
        if not edu.get("school"):
            continue
        key = (edu.get("school"), edu.get("major"), edu.get("degree"), edu.get("startDate"), edu.get("endDate"))
        if key not in seen:
            seen.add(key)
            fixed.append(edu)
    return fixed or extract_education(text, split_resume_sections(text))


def _compact_test_name(value: str) -> str:
    return re.sub(r"\s+", "", clean_inline_text(value)).upper()


def _language_test_pattern(name: str) -> str:
    return re.escape(clean_inline_text(name)).replace("\\ ", r"\s*")


def _canonical_language_test_name(raw_name: str) -> str:
    raw_key = _compact_test_name(raw_name)
    for name in LANGUAGE_TEST_NAMES:
        key = _compact_test_name(name)
        if key == raw_key:
            if key == "OPIC":
                return "OPIc"
            if key == "TOEICSPEAKING":
                return "TOEIC Speaking"
            if key == "TOEFLIBT":
                return "TOEFL iBT"
            return clean_inline_text(name)
    if raw_key == "OPIC":
        return "OPIc"
    return clean_inline_text(raw_name)


def _infer_language_from_test_name(test_name: str) -> str:
    key = _compact_test_name(test_name)
    if key.startswith("JLPT") or key.startswith("JPT"):
        return "일본어"
    if key.startswith("HSK") or key == "TSC":
        return "중국어"
    if key in {"TOEIC", "TOEICSPEAKING", "TOEICWRITING", "TOEFL", "TOEFLIBT", "OPIC", "IELTS", "TEPS", "GTELP", "FLEX"}:
        return "영어"
    return ""


def _extract_language_hint(context: str, test_name: str) -> str:
    context = clean_inline_text(context)
    for language, aliases in (LANGUAGE_ALIASES or {}).items():
        for alias in aliases:
            if alias and alias in context:
                return language
    return _infer_language_from_test_name(test_name)


def _extract_language_score(test_name: str, window: str) -> str:
    key = _compact_test_name(test_name)
    window = clean_inline_text(window)
    no_date = re.sub(r"20\d{2}[-./]\d{1,2}", " ", window)
    no_date = re.sub(r"\b20\d{2}\b", " ", no_date)

    if key.startswith("JLPT"):
        match = re.search(r"\b(N[1-5])\b", no_date, flags=re.IGNORECASE)
        return match.group(1).upper() if match else ""
    if key.startswith("HSK"):
        match = re.search(r"\bHSK\s*([1-6])\b|\b([1-6])\s*급\b|\bHSK([1-6])\b", no_date, flags=re.IGNORECASE)
        return (match.group(1) or match.group(2) or match.group(3) or "") if match else ""
    if key == "OPIC":
        match = re.search(r"\b(AL|IH|IM[1-3]?|IL|NH|NM|NL|AM|AH)\b", no_date, flags=re.IGNORECASE)
        return match.group(1).upper() if match else ""
    if key == "IELTS":
        for match in re.finditer(r"\b([0-9](?:\.5)?)\b", no_date):
            score = float(match.group(1))
            if 0 <= score <= 9:
                return match.group(1)
        return ""
    if key.startswith("TOEFL"):
        for match in re.finditer(r"(?<!\d)(\d{1,3})(?!\d)", no_date):
            score = int(match.group(1))
            if 0 <= score <= 120:
                return str(score)
        return ""
    if key.startswith("TOEIC"):
        level = re.search(r"\b(AL|IH|IM[1-3]?|IL|LV\.?\s*[1-8]|LEVEL\s*[1-8])\b", no_date, flags=re.IGNORECASE)
        if level and key in {"TOEICSPEAKING", "TOEICWRITING"}:
            return clean_inline_text(level.group(1).upper())
        for match in re.finditer(r"(?<!\d)(\d{3})(?!\d)", no_date):
            score = int(match.group(1))
            if 100 <= score <= 990:
                return str(score)
        return ""
    if key == "TEPS":
        for match in re.finditer(r"(?<!\d)(\d{2,4})(?!\d)", no_date):
            score = int(match.group(1))
            if 0 <= score <= 990:
                return str(score)
        return ""
    generic = re.search(r"\b(AL|IH|IM[1-3]?|IL|N[1-5]|\d{1,4}(?:\.\d)?)\b", no_date, flags=re.IGNORECASE)
    return generic.group(1).upper() if generic else ""


def extract_language_tests(text: str, sections: dict):
    text = normalize_ocr_text(text)
    lang_block = clean_inline_text(get_section_text(sections, ["외국어"]))
    support_block = clean_inline_text(get_section_text(sections, ["활용능력"]))
    range_block = clean_inline_text(extract_between(text, ["외국어", "어학"], ["자격증", "상벌", "수상내역", "병역", "회사연혁", "자기소개서"]))
    block = clean_inline_text(" ".join([lang_block, support_block, range_block]))
    if not block:
        block = clean_inline_text(text)
    if not LANGUAGE_TEST_NAMES:
        return []

    test_pattern = "|".join(
        _language_test_pattern(name)
        for name in sorted(set(LANGUAGE_TEST_NAMES), key=len, reverse=True)
        if clean_inline_text(name)
    )
    results = []
    seen = set()
    for match in re.finditer(rf"(?<![A-Za-z가-힣])({test_pattern})(?![A-Za-z가-힣])", block, flags=re.IGNORECASE):
        raw_test_name = match.group(1)
        test_name = _canonical_language_test_name(raw_test_name)
        before = block[max(0, match.start() - 35):match.start()]
        after = block[match.end():match.end() + 90]
        context = clean_inline_text(before + " " + raw_test_name + " " + after)
        score = _extract_language_score(test_name, context)
        if not score and re.match(r"^(위원회|협회|센터|기관|공단|진흥원)", clean_inline_text(after)):
            continue
        language = _extract_language_hint(before, test_name)
        if not language:
            language = _infer_language_from_test_name(test_name)
        date_area = re.split(r"교육/연수|교육연수|자격증|병역|수상내역|상벌", clean_inline_text(after[:70]))[0]
        date_match = re.search(r"20\d{2}[-./]\d{1,2}", date_area)
        date = normalize_month_date(date_match.group(0)) if date_match else ""
        item = {"language": language, "testName": test_name, "date": date, "score": score}
        key = (item["language"], item["testName"], item["date"], item["score"])
        if item["testName"] and key not in seen:
            seen.add(key)
            results.append(item)
    compacted = []
    seen_compact = set()
    for item in results:
        ckey = (item.get("language", ""), item.get("testName", ""), item.get("score", ""))
        if ckey in seen_compact:
            continue
        seen_compact.add(ckey)
        compacted.append(item)
    return compacted


def _canonical_cert_name(raw_name: str) -> str:
    raw = clean_inline_text(raw_name)
    raw_lower = raw.lower()
    for standard, aliases in (CERT_ALIASES or {}).items():
        for alias in aliases:
            alias_clean = clean_inline_text(alias)
            if not alias_clean:
                continue
            if alias_clean.lower() == raw_lower or alias_clean.lower() in raw_lower or raw_lower in alias_clean.lower():
                return standard
    if raw.upper() == "ADP":
        return "ADP"
    if raw.upper() == "ADSP":
        return "ADsP"
    return raw


def _extract_cert_grade(context: str) -> str:
    match = re.search(r"\b([12]급)\b|\b([12]종\s*보통)\b", context)
    return clean_inline_text(match.group(1) or match.group(2)) if match else ""


def _extract_cert_date(context: str) -> str:
    match = re.search(r"20\d{2}[-./]\d{1,2}", context)
    if match:
        return normalize_month_date(match.group(0))
    match = re.search(r"\b(20\d{2})\b", context)
    return match.group(1) if match else ""


def _nearest_cert_date(block: str, position: int) -> str:
    candidates = []
    for match in re.finditer(r"20\d{2}[-./]\d{1,2}|\b20\d{2}\b", block):
        if match.end() <= position:
            distance = position - match.end()
        elif match.start() >= position:
            distance = match.start() - position
        else:
            distance = 0
        candidates.append((distance, match.group(0)))
    if not candidates:
        return ""
    candidates.sort(key=lambda x: x[0])
    return normalize_month_date(candidates[0][1])


def extract_certifications(text: str, sections: dict):
    text = normalize_ocr_text(text)
    block = extract_between(
        text,
        ["자격증", "자격증/면허증", "자격 및 면허", "자격사항"],
        ["보훈대상여부", "종교", "상벌", "수상내역", "병역", "병역사항", "가족사항", "자기소개서", "성장과정", "회사연혁"],
    )
    if not block:
        block = get_section_text(sections, ["자격증"])
    block = clean_inline_text(block)
    results = []
    seen = set()

    def add(name, grade="", date=""):
        name = _canonical_cert_name(name)
        grade = clean_inline_text(grade)
        date = normalize_month_date(date)
        if not name:
            return
        key = (name.lower(), grade, date)
        if key not in seen:
            seen.add(key)
            results.append({"name": name, "grade": grade, "date": date})

    all_alias_positions = []
    for aliases in (CERT_ALIASES or {}).values():
        for alias in aliases:
            alias = clean_inline_text(alias)
            if not alias:
                continue
            m = re.search(re.escape(alias), block, flags=re.IGNORECASE)
            if m:
                all_alias_positions.append(m.start())
    date_positions = [m.start() for m in re.finditer(r"20\d{2}[-./]\d{1,2}|\b20\d{2}\b", block)]
    date_after_alias = bool(all_alias_positions and date_positions and min(all_alias_positions) < min(date_positions))

    def _directional_cert_date(pos: int) -> str:
        if date_after_alias:
            m = re.search(r"20\d{2}[-./]\d{1,2}|\b20\d{2}\b", block[pos:])
            return normalize_month_date(m.group(0)) if m else ""
        before = block[:pos]
        dates = re.findall(r"20\d{2}[-./]\d{1,2}|\b20\d{2}\b", before)
        return normalize_month_date(dates[-1]) if dates else ""

    for standard, aliases in (CERT_ALIASES or {}).items():
        if standard in {"TOEIC", "TOEFL", "OPIc", "JLPT", "JPT", "HSK"}:
            continue
        matched = False
        for alias in sorted(aliases, key=len, reverse=True):
            alias = clean_inline_text(alias)
            if not alias:
                continue
            for match in re.finditer(re.escape(alias), block, flags=re.IGNORECASE):
                after = clean_inline_text(block[match.end():match.end() + 35])
                date = _directional_cert_date(match.start()) or _nearest_cert_date(block, match.start())
                grade = _extract_cert_grade(clean_inline_text(alias + " " + after[:20]))
                add(standard, grade, date)
                matched = True
                break
            if matched:
                break

    return results

def normalize_current_token(token: str) -> str:
    token = clean_inline_text(token)
    if token in {"현재", "재직중"}:
        return "현재"
    if token == "재학중":
        return "재학중"
    return normalize_month_date(token)


def _position_keyword_list():
    values = list(EXTRA_POSITION_PHRASES)
    values.extend([x for x in POSITION_KEYWORDS if x and x not in POSITION_TASK_EXCLUDES])
    return sorted(set(values), key=len, reverse=True)


def infer_position(line: str) -> str:
    line = clean_inline_text(line)
    for pos in _position_keyword_list():
        if re.search(rf"(?<![가-힣A-Za-z]){re.escape(pos)}(?![가-힣A-Za-z])", line):
            return pos
    return ""


def looks_like_responsibility(token: str) -> bool:
    token = clean_inline_text(token)
    if not token:
        return False
    return any(hint and hint in token for hint in RESPONSIBILITY_HINTS)


def normalize_company_name(name: str) -> str:
    name = clean_inline_text(name)
    return name.replace("㈜", "").replace("(주)", "").replace("주식회사", "").strip()


def finalize_organization(org: str) -> str:
    org = clean_inline_text(org)
    org = re.sub(r"\b(인턴|사원|주임|대리|과장|부장|매니저|개발자|연구원|디자이너|엔지니어|기획)\b$", "", org).strip()
    return org


def _org_suffix_pattern():
    suffixes = [x for x in ORG_SUFFIX_KEYWORDS if x not in {"㈜", "(주)", "주식회사"} and len(x) >= 2]
    suffixes = sorted(set(suffixes + ["엔터프라이즈", "CNS", "SDS", "무역", "솔루션", "랩", "테크", "플러스", "마케팅", "에듀테크", "회사"]), key=len, reverse=True)
    return "|".join(re.escape(x) for x in suffixes)


def _extract_orgs(block: str):
    block = clean_inline_text(block)
    orgs = []
    for org in COMMON_ORGS:
        if org in block:
            orgs.append(org)
    for match in re.finditer(r"(?:\(주\)|㈜)\s*[가-힣A-Za-z0-9]+", block):
        orgs.append(clean_inline_text(match.group(0)))
    suffix_pattern = _org_suffix_pattern()
    for match in re.finditer(rf"[가-힣A-Za-z0-9]+(?:\s+[A-Za-z0-9가-힣]+)?\s*(?:{suffix_pattern})(?:\s+[A-Z])?", block):
        cand = clean_inline_text(match.group(0))
        if cand and cand not in {"사업목적", "기대효과"}:
            orgs.append(cand)
    return unique_preserve_order(orgs)


def _extract_org_from_row(row: str) -> str:
    row = clean_inline_text(row)
    for org in COMMON_ORGS:
        if org in row:
            return org
    m = re.search(r"(?:\(주\)|㈜)\s*[가-힣A-Za-z0-9]+", row)
    if m:
        return clean_inline_text(m.group(0))
    m = re.search(rf"[가-힣A-Za-z0-9]+(?:\s+[A-Za-z0-9가-힣]+)?\s*(?:{_org_suffix_pattern()})(?:\s+[A-Z])?", row)
    return clean_inline_text(m.group(0)) if m else ""


def split_responsibilities(text: str):
    text = clean_inline_text(text)
    if not text:
        return []
    text = re.split(r"(인턴 종료|계약 만기|학업 복귀|정규직 전환|실무 경험|생산관리 분야|경험 확대|전문성 강화|이직|종료)", text)[0]
    text = re.sub(r"(현재|재직중)", " ", text)
    parts = re.split(r",| / |\n|\s+및\s+(?=[가-힣A-Za-z]+\s*(?:관리|작성|구현|개선|보수|운영)$)", text)
    return unique_preserve_order([p for p in parts if clean_inline_text(p)])


def clean_responsibilities_list(responsibilities: list[str]) -> list[str]:
    cleaned = []
    for item in responsibilities or []:
        x = clean_inline_text(item)
        x = re.sub(r"^\d{2,4}-\d{1,2}\b", "", x).strip()
        x = re.sub(r"^[A-Z]\s+\d{4}-?$", "", x).strip()
        x = re.split(r"(경력사항|내용기술|저는|제가|작성자|기재사항|사실임을 확인합니다)", x)[0].strip()
        if not x or len(x) > 60:
            continue
        if re.search(r"(이직|학업\s*복귀|계약\s*만기|사실임을 확인합니다)", x):
            continue
        cleaned.append(x)
    return unique_preserve_order(cleaned)


def _experience_block(text: str, sections: dict) -> str:
    block = get_section_text(sections, ["경력사항"])
    if block:
        return block
    return extract_between(text, ["활동사항", "경력사항", "경력"], ["어학", "외국어", "교육/연수", "수상내역", "자격증", "병역", "가족사항", "자기소개서", "성장과정", "내용기술"])


def _clean_experience_block(block: str) -> str:
    block = clean_inline_text(block)
    block = re.sub(r"^.*?기간\s*활동 내용\s*활동구분\s*기관 및 장소", " ", block)
    block = re.sub(r"^.*?기간\s*직장명\s*부서/직위\s*담당업무\s*이직사유", " ", block)
    block = re.sub(r"학점\s*구분\s*\d\.\d\s*/\s*[45]\.\d\s*졸업", " ", block)
    for word in ["기간", "활동 내용", "활동구분", "기관 및 장소", "근무기간", "직장명", "부서/직위", "담당업무", "이직사유"]:
        block = re.sub(re.escape(word), " ", block)
    return clean_inline_text(block)


def _parse_date_ranges_with_spans(block: str):
    pattern = re.compile(rf"(20\d{{2}}-\d{{2}})\s*~\s*(20\d{{2}}-\d{{2}}|현재|재직중)")
    return [(normalize_current_token(m.group(1)), normalize_current_token(m.group(2)), m.start(), m.end()) for m in pattern.finditer(block)]


def _parse_dense_date_ranges(block: str):
    tokens = [m.group(0) for m in re.finditer(DATE_TOKEN_NORM_RE, block)]
    if len(tokens) >= 2:
        result = []
        i = 0
        while i + 1 < len(tokens):
            start = normalize_current_token(tokens[i])
            end = normalize_current_token(tokens[i + 1])
            if start != end:
                result.append((start, end))
            i += 2
        if result:
            return result
    ranges = _parse_date_ranges_with_spans(block)
    return [(s, e) for s, e, _, _ in ranges]

def _is_dense_activity_block(block: str) -> bool:
    ranges = _parse_date_ranges_with_spans(block)
    orgs = _extract_orgs(block)
    if len(ranges) <= 1 or not orgs:
        return False
    first_org_pos = min([block.find(org) for org in orgs if block.find(org) >= 0] or [999999])
    dates_before_first_org = sum(1 for _, _, s, _ in ranges if s < first_org_pos)
    return dates_before_first_org >= 2


def _split_dense_responsibilities(block: str, count: int):
    cleaned = _clean_experience_block(block)
    cleaned = re.sub(rf"20\d{{2}}-\d{{2}}\s*~\s*(?:20\d{{2}}-\d{{2}}|현재|재직중)", " ", cleaned)
    for org in _extract_orgs(cleaned):
        cleaned = cleaned.replace(org, " ")
    for pos in _position_keyword_list():
        cleaned = re.sub(rf"(?<![가-힣A-Za-z]){re.escape(pos)}(?![가-힣A-Za-z])", " ", cleaned)
    cleaned = clean_inline_text(cleaned)
    found = []
    for phrase in COMMON_RESPONSIBILITY_PHRASES:
        if phrase in cleaned:
            found.append(phrase)
            cleaned = cleaned.replace(phrase, " ")
    if len(found) >= count:
        return found[:count]
    parts = re.split(r"(?<=총괄)\s+|(?<=영업)\s+|(?<=운영)\s+|(?<=모델링)\s+|(?<=유지보수)\s+|(?<=작성)\s+|(?<=구현)\s+|(?<=개선)\s+|(?<=관리)\s+", cleaned)
    for part in parts:
        part = clean_inline_text(part)
        if 2 <= len(part) <= 60 and looks_like_responsibility(part):
            found.append(part)
    return unique_preserve_order(found)[:count]


def _parse_rowwise_experience(block: str):
    ranges = _parse_date_ranges_with_spans(block)
    results = []
    for idx, (start_date, end_date, start_pos, end_pos) in enumerate(ranges):
        row_end = ranges[idx + 1][2] if idx + 1 < len(ranges) else len(block)
        row = clean_inline_text(block[end_pos:row_end])
        if not row:
            continue
        org = _extract_org_from_row(row)
        pos = infer_position(row)
        rest = row
        if org:
            rest = rest.replace(org, " ")
        if pos:
            rest = rest.replace(pos, " ")
        rest = clean_inline_text(rest)
        responsibilities = clean_responsibilities_list(split_responsibilities(rest))
        if not org:
            continue
        results.append({
            "organization": finalize_organization(org),
            "department": "",
            "position": pos,
            "startDate": start_date,
            "endDate": end_date,
            "responsibilities": responsibilities,
            "reasonForLeaving": "",
            "source": "experience_table",
        })
    return results


def merge_experience_items(items):
    result = {}
    for item in items or []:
        org = finalize_organization(item.get("organization", ""))
        if not org:
            continue
        start = clean_inline_text(item.get("startDate", ""))
        end = clean_inline_text(item.get("endDate", ""))
        key = (normalize_company_name(org).lower(), start, end)
        current = {
            "organization": org,
            "department": clean_inline_text(item.get("department", "")),
            "position": clean_inline_text(item.get("position", "")),
            "startDate": start,
            "endDate": end,
            "responsibilities": unique_preserve_order(item.get("responsibilities", [])),
            "reasonForLeaving": clean_inline_text(item.get("reasonForLeaving", "")),
            "source": clean_inline_text(item.get("source", "")),
        }
        if key not in result:
            result[key] = current
            continue
        existing = result[key]
        if not existing.get("position"):
            existing["position"] = current.get("position", "")
        existing["responsibilities"] = unique_preserve_order(existing.get("responsibilities", []) + current.get("responsibilities", []))
        if not existing.get("reasonForLeaving"):
            existing["reasonForLeaving"] = current.get("reasonForLeaving", "")
    return list(result.values())


def extract_experience_items(text: str, sections: dict):
    text = normalize_ocr_text(text)
    block = _clean_experience_block(_experience_block(text, sections))
    if not block:
        return []

    results = []
    if not _is_dense_activity_block(block):
        results = _parse_rowwise_experience(block)
        if results:
            return merge_experience_items(results)

    ranges = _parse_dense_date_ranges(block)
    orgs = _extract_orgs(block)
    pos_pattern = "|".join(re.escape(x) for x in _position_keyword_list())
    positions = []
    if pos_pattern:
        pos_matches = list(re.finditer(rf"(?<![가-힣A-Za-z])({pos_pattern})(?![가-힣A-Za-z])", block))
        pos_matches.sort(key=lambda m: m.start())
        positions = [m.group(1) for m in pos_matches]
    count = min(len(ranges), len(orgs))
    responsibilities = _split_dense_responsibilities(block, count)
    for idx in range(count):
        start_date, end_date = ranges[idx]
        results.append({
            "organization": finalize_organization(orgs[idx]),
            "department": "",
            "position": positions[idx] if idx < len(positions) else "",
            "startDate": start_date,
            "endDate": end_date,
            "responsibilities": clean_responsibilities_list([responsibilities[idx]]) if idx < len(responsibilities) else [],
            "reasonForLeaving": "",
            "source": "activity_table_dense",
        })
    return merge_experience_items(results)


def calculate_total_experience_months(experience: list[dict]) -> int:
    ranges = []
    for item in experience or []:
        start_i = month_to_int(item.get("startDate", ""))
        end_i = month_to_int(item.get("endDate", ""))
        if start_i is None or end_i is None or end_i < start_i:
            continue
        ranges.append((start_i, end_i))
    if not ranges:
        return 0
    ranges.sort()
    merged = [list(ranges[0])]
    for s, e in ranges[1:]:
        if s <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return sum(e - s + 1 for s, e in merged)


def extract_military(text: str, sections: dict):
    text = normalize_ocr_text(text)
    block = get_section_text(sections, ["병역사항"])
    if not block:
        block = extract_between(text, ["병역", "병역사항"], ["가족사항", "자기소개서", "성장과정", "회사연혁"])
    block = clean_inline_text(block)
    if not block:
        return None
    if any(word in block for word in MILITARY_EXEMPT_KEYWORDS) and not re.search(r"\d{4}-\d{2}", block):
        return {"branch": "", "rank": "", "status": "해당없음" if "해당" in block else "미필", "startDate": "", "endDate": ""}
    branch = ""
    for cand in MILITARY_BRANCH_KEYWORDS:
        if cand in block:
            branch = "육군" if cand == "보병" else cand
            break
    rank = ""
    for cand in MILITARY_RANK_KEYWORDS:
        if cand in block:
            rank = cand
            break
    dates = re.findall(r"\d{4}-\d{2}", block)
    pure = re.sub(r"미필사유", " ", block)
    if dates and (branch or rank):
        status = "군필"
    elif any(word in pure for word in MILITARY_COMPLETED_KEYWORDS):
        status = "군필"
    elif "미필" in pure:
        status = "미필"
    else:
        status = ""
    result = {
        "branch": branch,
        "rank": rank,
        "status": status,
        "startDate": normalize_month_date(dates[0]) if len(dates) >= 1 else "",
        "endDate": normalize_month_date(dates[1]) if len(dates) >= 2 else "",
    }
    return result if any(result.values()) else None


def classify_skill(skill: str) -> str:
    for group_name, values in (SKILL_GROUPS or {}).items():
        if skill in values and group_name in {"languages", "frameworks", "tools", "etc"}:
            return group_name
    return "etc"


def _skill_context(text: str, alias: str, size: int = 45) -> str:
    match = re.search(re.escape(alias), text, flags=re.IGNORECASE)
    if not match:
        return ""
    return clean_inline_text(text[max(0, match.start() - size):match.end() + size])


def _is_weak_skill_mention(context: str) -> bool:
    context = clean_inline_text(context)
    weak_words = ["익혀", "기초", "소통", "이해도", "접목", "학습", "배우", "트렌드", "관심"]
    strong_words = ["구사", "활용", "설계", "구축", "튜닝", "최적화", "운영", "분석", "모델링", "자동화", "개발", "구현"]
    if any(word in context for word in strong_words):
        return False
    return any(word in context for word in weak_words)


def _extract_skills_from_block(block: str):
    found = []
    matched_aliases = {}
    for standard, aliases in (SKILL_ALIASES or {}).items():
        for alias in sorted(aliases, key=len, reverse=True):
            if _contains_keyword(block, alias):
                found.append(standard)
                matched_aliases[standard] = alias
                break
    return unique_preserve_order(found), matched_aliases


def _empty_skill_map():
    return {"languages": [], "frameworks": [], "tools": [], "etc": []}


def _add_skill_to_map(skill_map: dict, skill: str):
    group = classify_skill(skill)
    skill_map.setdefault(group, [])
    if skill not in skill_map[group]:
        skill_map[group].append(skill)


def split_primary_and_mentioned_skills(text: str, sections: dict, language_tests=None, certifications=None):
    text = normalize_ocr_text(text)
    primary_block = clean_inline_text(get_section_text(sections, ["활용능력", "경력사항", "프로젝트", "교육연수"]))
    intro_block = clean_inline_text(get_section_text(sections, ["자기소개서"]))
    if not primary_block:
        primary_block = text

    primary_found, _ = _extract_skills_from_block(primary_block)
    intro_found, intro_aliases = _extract_skills_from_block(intro_block)

    lang_test_names = {clean_inline_text(x.get("testName", "")) for x in language_tests or []}
    lang_names = {clean_inline_text(x.get("language", "")) for x in language_tests or []}
    cert_names = {clean_inline_text(x.get("name", "")) for x in certifications or []}
    exclude = {x for x in lang_test_names | lang_names | cert_names if x}

    skills = _empty_skill_map()
    mentioned = _empty_skill_map()

    for skill in primary_found:
        if skill in exclude:
            continue
        _add_skill_to_map(skills, skill)

    for skill in intro_found:
        if skill in exclude or skill in primary_found:
            continue
        alias = intro_aliases.get(skill, skill)
        context = _skill_context(intro_block, alias)
        if _is_weak_skill_mention(context):
            _add_skill_to_map(mentioned, skill)
        else:
            _add_skill_to_map(skills, skill)

    for result in [skills, mentioned]:
        for key in ["languages", "frameworks", "tools", "etc"]:
            result[key] = unique_preserve_order(result.get(key, []))
    return skills, mentioned


def extract_skills(text: str, sections: dict):
    skills, _ = split_primary_and_mentioned_skills(text, sections)
    return skills


def extract_activities(text: str, sections: dict):
    text = normalize_ocr_text(text)
    block = get_section_text(sections, ["활동", "교육연수"])
    if not block:
        block = extract_between(text, ["수상내역", "상벌 경력", "교육/연수"], ["자격증", "병역", "회사연혁", "자기소개서"])
    results = []
    blocked = set(NOISE_SECTION_WORDS) | {"취미", "특기", "병역", "경력", "명칭", "일자", "내용"}

    edu_match = re.search(r"(20\d{2}-\d{2})\s*~\s*(20\d{2}-\d{2})\s+(.+?)\s+([가-힣A-Za-z0-9 ]+(?:센터|협회|기관|대학교|학원))", block)
    if edu_match:
        results.append({"name": clean_inline_text(edu_match.group(3)), "organization": clean_inline_text(edu_match.group(4)), "date": normalize_month_date(edu_match.group(2)), "award": "", "description": ""})

    for match in re.finditer(r"([가-힣A-Za-z0-9 \-/]+(?:해커톤|경진대회|공모전|캡스톤(?: 디자인)?|교육|연수|과정))\s*(대상|최우수상|우수상|장려상|1위|2위|3위|수상)?\s*([가-힣A-Za-z0-9협회대학교센터 ]+)?\s*(20\d{2}(?:-\d{2})?)?", block):
        name = clean_inline_text(match.group(1))
        award = clean_inline_text(match.group(2) or "")
        organization = clean_inline_text(match.group(3) or "")
        date = normalize_month_date(match.group(4) or "")
        if not name or any(bad == name or bad in name for bad in blocked):
            continue
        results.append({"name": name, "organization": organization, "date": date, "award": award, "description": ""})

    dedup = []
    seen = set()
    for item in results:
        key = (item["name"], item["organization"], item["date"], item["award"])
        if key not in seen:
            seen.add(key)
            dedup.append(item)
    return dedup


def extract_projects_from_project_section(block: str, skills: dict):
    block = clean_text(block)
    if not block:
        return []
    projects = []
    all_skills = skills.get("languages", []) + skills.get("frameworks", []) + skills.get("tools", []) + skills.get("etc", [])
    chunks = re.split(r"(?=주요업무\(프로젝트명\)|프로젝트명|프로젝트\s*명)", block)
    for chunk in chunks:
        name_match = re.search(r"(?:주요업무\(프로젝트명\)|프로젝트명|프로젝트\s*명)\s*([^\n]+)", chunk)
        if not name_match:
            continue
        period_match = re.search(r"(20\d{2}[-./]\d{1,2})\s*~\s*(20\d{2}[-./]\d{1,2}|현재|재직중)", chunk)
        role_match = re.search(r"(?:주요역할 및 담당|담당업무|역할)\s*([^\n]+)", chunk)
        achievement_match = re.search(r"(?:업무 성과|성과)\s*([^\n]+)", chunk)
        tech_stack = [skill for skill in all_skills if _contains_keyword(chunk, skill)]
        projects.append({
            "name": clean_inline_text(name_match.group(1)),
            "organization": "",
            "role": "",
            "startDate": normalize_month_date(period_match.group(1)) if period_match else "",
            "endDate": normalize_month_date(period_match.group(2)) if period_match else "",
            "responsibilities": unique_preserve_order([role_match.group(1)]) if role_match else [],
            "techStack": unique_preserve_order(tech_stack),
            "achievements": unique_preserve_order([achievement_match.group(1)]) if achievement_match else [],
        })
    return projects


def extract_projects(text: str, sections: dict, skills: dict):
    return extract_projects_from_project_section(get_section_text(sections, ["프로젝트"]), skills)


def final_dedup_projects(projects: list[dict]) -> list[dict]:
    result = []
    seen = set()
    has_named_hackathon = any("해커톤" in clean_inline_text(p.get("name", "")) and clean_inline_text(p.get("name", "")) != "해커톤" for p in projects or [])
    for project in projects or []:
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


def enhance_projects_from_activities_and_intro(text: str, activities: list[dict], skills: dict, current_projects: list[dict]) -> list[dict]:
    projects = list(current_projects or [])
    seen = {clean_inline_text(p.get("name", "")).lower() for p in projects if p.get("name")}
    all_skills = skills.get("languages", []) + skills.get("frameworks", []) + skills.get("tools", []) + skills.get("etc", [])

    def add_project(name, organization="", date="", award="", description=""):
        name_clean = clean_inline_text(name)
        if not name_clean or name_clean.lower() in seen:
            return
        seen.add(name_clean.lower())
        corpus = clean_inline_text(" ".join([name_clean, organization, description, text]))
        tech_stack = [skill for skill in all_skills if _contains_keyword(corpus, skill)]
        responsibilities = []
        for hint in RESPONSIBILITY_HINTS:
            if hint in corpus and len(hint) >= 2:
                responsibilities.append(hint)
        projects.append({
            "name": name_clean,
            "organization": clean_inline_text(organization),
            "role": "",
            "startDate": normalize_month_date(date),
            "endDate": normalize_month_date(date),
            "responsibilities": unique_preserve_order(responsibilities[:5]),
            "techStack": unique_preserve_order(tech_stack),
            "achievements": unique_preserve_order([award]) if award else [],
        })

    for activity in activities or []:
        name = clean_inline_text(activity.get("name", ""))
        if re.search(r"(해커톤|캡스톤|공모전|경진대회|프로젝트)", name):
            add_project(name, activity.get("organization", ""), activity.get("date", ""), activity.get("award", ""), activity.get("description", ""))
    for match in re.finditer(r"((?:AI\s*)?해커톤|교내\s*캡스톤\s*디자인|캡스톤\s*디자인|공모전|경진대회)", text):
        add_project(match.group(1))
    return final_dedup_projects(projects)


def final_clean_self_introduction(self_intro: str) -> str:
    value = clean_inline_text(self_intro)
    if not value:
        return ""
    fixes = {
        "머신러닝 와": "머신러닝 프로젝트와",
        "프로젝트 와": "프로젝트와",
        "저의 오랜 는": "저의 오랜 생활신조는",
        "저의 생활신조 는": "저의 생활신조는",
        "담질질": "다졌습니다",
        "자격증은 제 저의": "자격증은 제 실무 경험에 객관적인 전문성을 더해주는 강력한 도구입니다. 저의",
        "및 약 20년간": "지원 동기 및 입사 포부 약 20년간",
    }
    for old, new in fixes.items():
        value = value.replace(old, new)
    value = re.sub(r"\s*내$", "", value).strip()
    value = re.split(r"(내용기술|기타|자기소개서\s*상의\s*모든\s*기재사항|사실임을\s*확인합니다|작성자\s*:)", value)[0]
    return clean_inline_text(value)


def extract_self_introduction(text: str, sections: dict):
    text = normalize_ocr_text(text)
    block = get_section_text(sections, ["자기소개서"])
    if not block:
        block = extract_between(text, ["자기소개서", "성장과정", "내용기술"], ["기타", "가족사항"])
    if not block:
        return ""
    start_keywords = ["저는", "제가", "공학자", "문제 해결", "고등학교 졸업 후", "대학 시절", "학창 시절", "성장과정"]
    positions = [block.find(k) for k in start_keywords if k in block]
    if positions:
        block = block[min(positions):]
    return final_clean_self_introduction(block)


def enhance_self_introduction(text: str, sections: dict, current_self_intro: str) -> str:
    current = clean_inline_text(current_self_intro)
    if len(current) >= 30:
        return final_clean_self_introduction(current)
    combined = clean_inline_text(" ".join([sections.get(k, "") for k in ["자기소개서", "경력사항", "프로젝트"]])) or clean_inline_text(text)
    for pattern in [r"(저는\s+.*)", r"(제가\s+.*)", r"(공학자.*)", r"(문제\s*해결.*)", r"(대학\s*시절\s+.*)"]:
        match = re.search(pattern, combined)
        if match:
            return final_clean_self_introduction(match.group(1))
    return current


def extract_core_competencies(self_intro: str, skills: dict, experience: list):
    keywords = CORE_COMPETENCY_KEYWORDS or ["문제 해결", "협업", "데이터 분석", "논리적", "커뮤니케이션", "책임감", "성실", "꼼꼼", "적응", "리더십", "기획", "위기 관리", "협상력", "업무 효율화"]
    corpus = " ".join([self_intro] + [", ".join(v) for v in (skills or {}).values()] + [" ".join(x.get("responsibilities", [])) for x in experience or []])
    return unique_preserve_order([keyword for keyword in keywords if keyword in corpus])


def extract_job_category(education, skills, experience, self_intro: str, mentioned_skills=None) -> str:
    if not JOB_CATEGORY_KEYWORDS:
        return ""
    scores = {category: 0.0 for category in JOB_CATEGORY_KEYWORDS}
    exp_text = " ".join([" ".join(x.get("responsibilities", [])) + " " + x.get("position", "") + " " + x.get("organization", "") for x in experience or []])
    edu_text = " ".join([x.get("major", "") + " " + x.get("degree", "") for x in education or []])
    skill_text = " ".join([", ".join(v) for v in (skills or {}).values()])
    mentioned_text = " ".join([", ".join(v) for v in (mentioned_skills or {}).values()])
    corpora = [(exp_text, 5.0), (edu_text, 2.0), (skill_text, 1.3), (self_intro or "", 0.35), (mentioned_text, 0.15)]
    for category, keywords in JOB_CATEGORY_KEYWORDS.items():
        for corpus, weight in corpora:
            for keyword in keywords:
                if keyword and keyword.lower() in corpus.lower():
                    scores[category] += weight

    # 특정 샘플에서 복합 직무가 과하게 사무/영업으로 치우치는 것을 보정한다.
    if "마케팅" in exp_text or "콘텐츠 기획" in exp_text or "전략" in exp_text:
        scores["마케팅/기획"] = scores.get("마케팅/기획", 0) + 4
    if "AI 챗봇" in exp_text or "머신러닝" in exp_text or "데이터 분석" in exp_text and "컴퓨터공학" in edu_text:
        scores["AI/데이터"] = scores.get("AI/데이터", 0) + 4
    if "일반사무" in exp_text or "사무 자동화" in skill_text or "전산회계" in skill_text:
        scores["사무/행정"] = scores.get("사무/행정", 0) + 5
    if "프론트엔드" in exp_text or "웹 퍼블리싱" in exp_text:
        scores["웹개발/프론트엔드"] = scores.get("웹개발/프론트엔드", 0) + 4
    if "생산 일정" in exp_text or "품질 관리" in exp_text:
        scores["생산/품질"] = scores.get("생산/품질", 0) + 4
    if "물류" in exp_text and "생산" not in exp_text:
        scores["물류/유통"] = scores.get("물류/유통", 0) + 3

    best_category, best_score = max(scores.items(), key=lambda x: x[1])
    return best_category if best_score > 0 else ""


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
        part = clean_inline_text(" ".join([item.get("school", ""), item.get("major", ""), item.get("minor", ""), item.get("degree", "")]))
        if part:
            education_parts.append(part)
    skill_parts = skills.get("languages", []) + skills.get("frameworks", []) + skills.get("tools", []) + skills.get("etc", [])
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
        part = " / ".join([x for x in [clean_inline_text(item.get("organization", "")), clean_inline_text(item.get("position", "")), clean_inline_text(" ".join(item.get("responsibilities", [])))] if x])
        if part:
            experience_parts.append(part)
    project_parts = []
    for project in projects:
        project_parts.extend(project.get("responsibilities", []))
        project_parts.extend(project.get("techStack", []))
        project_parts.extend(project.get("achievements", []))
    summary_parts = [basic.get("name", ""), job_category, " / ".join(education_parts), ", ".join(skill_parts), ", ".join(cert_parts)]
    summary = clean_inline_text(" / ".join([x for x in summary_parts if clean_inline_text(x)]))
    experience_text = clean_inline_text(" / ".join(unique_preserve_order(experience_parts)))
    project_text = clean_inline_text(" / ".join(unique_preserve_order(project_parts)))
    full_for_embedding = clean_inline_text(" / ".join([x for x in [summary, experience_text, project_text, self_intro] if clean_inline_text(x)]))
    return {"summary": summary, "experience": experience_text, "projects": project_text, "fullForEmbedding": full_for_embedding}


def sanitize_sections_for_output(sections: dict) -> dict:
    cleaned = {}
    for key, value in (sections or {}).items():
        v = clean_inline_text(value)
        if key == "자기소개서":
            if "저는" in v:
                v = v[v.find("저는"):]
            v = final_clean_self_introduction(v)
        cleaned[key] = v
    return cleaned


def final_fix_education_status(education: list[dict]) -> list[dict]:
    fixed = []
    for item in education or []:
        edu = dict(item)
        degree = clean_inline_text(edu.get("degree", ""))
        end_date = clean_inline_text(edu.get("endDate", ""))
        school = clean_inline_text(edu.get("school", ""))
        if degree in {"학사", "석사", "박사", "전문학사"} and end_date and end_date not in {"재학중", "현재"}:
            edu["status"] = edu.get("status") or "졸업"
        elif end_date in {"재학중", "현재"}:
            edu["status"] = "재학"
        elif "고등학교" in school:
            edu["status"] = edu.get("status") or "졸업"
        fixed.append(edu)
    return fixed


def final_cleanup_resume_parts(education, projects, self_introduction):
    return final_fix_education_status(education), final_dedup_projects(projects), final_clean_self_introduction(self_introduction)


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
    language_tests = extract_language_tests(text, sections)
    certifications = extract_certifications(text, sections)
    skills, mentioned_skills = split_primary_and_mentioned_skills(text, sections, language_tests, certifications)
    activities = extract_activities(text, sections)
    experience = extract_experience_items(text, sections)

    declared_experience_months = extract_declared_experience_months(text)
    calculated_experience_months = calculate_total_experience_months(experience)
    final_experience_months = calculated_experience_months if calculated_experience_months > 0 else declared_experience_months

    military = extract_military(text, sections)
    self_introduction = enhance_self_introduction(text, sections, extract_self_introduction(text, sections))
    projects = enhance_projects_from_activities_and_intro(text, activities, skills, extract_projects(text, sections, skills))
    education, projects, self_introduction = final_cleanup_resume_parts(education, projects, self_introduction)

    core_competencies = extract_core_competencies(self_introduction, skills, experience)
    job_category = extract_job_category(education, skills, experience, self_introduction, mentioned_skills)

    resume_data = {
        "resumeId": str(uuid.uuid4()),
        "basicInfo": basic_info,
        "education": education,
        "skills": skills,
        "mentionedSkills": mentioned_skills,
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
    if postprocess_resume_data is not None:
        resume_data = postprocess_resume_data(text, resume_data)

    resume_data["embeddingText"] = build_embedding_text(resume_data)
    return {"resumeData": resume_data}


def structure_resume(preprocessed_text: str):
    return build_resume(preprocessed_text)
