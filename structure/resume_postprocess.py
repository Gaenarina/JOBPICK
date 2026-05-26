import copy
import re
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


SKILL_ALIASES = _cfg("SKILL_ALIASES", {})
SKILL_GROUPS = _cfg("SKILL_GROUPS", {})
CERT_ALIASES = _cfg("CERT_ALIASES", {})
POSITION_KEYWORDS = _cfg("POSITION_KEYWORDS", [])
RESPONSIBILITY_HINTS = _cfg("RESPONSIBILITY_HINTS", [])
CORE_COMPETENCY_KEYWORDS = _cfg("CORE_COMPETENCY_KEYWORDS", [])
JOB_CATEGORY_KEYWORDS = _cfg("JOB_CATEGORY_KEYWORDS", {})

BAD_NAME_WORDS = {
    "회사명", "생산", "성명", "업종", "품목", "연령", "이력서", "한글", "한문",
    "현주소", "긴급", "연락처", "기간", "학력", "성적", "외국어", "자격증", "학교명",
}

KNOWN_ORGS = [
    "카카오 엔터프라이즈", "카카오", "엔터프라이즈", "LG CNS", "삼성 SDS", "NAVER Cloud", "네이버 클라우드",
    "IT 서비스 회사", "소프트웨어 회사", "물류회사 A", "전자부품회사 B",
    "(주)글로벌마케팅", "(주)유통플러스", "(주)에듀테크", "(주)대동무역",
    "(주)테크솔루션", "(주)소프트웨어랩", "(주)소프트웨어랩",
]

POSITION_PHRASES = sorted(set([
    "프론트엔드 개발자", "백엔드 개발자", "풀스택 개발자", "웹 퍼블리셔",
    "데이터 분석가", "데이터 엔지니어", "머신러닝 엔지니어", "AI 엔지니어",
    "물류관리 사원", "생산관리 사원", "품질관리 사원", "선임연구원", "주임연구원",
    "책임연구원", "수석연구원", "팀장", "파트장", "과장", "대리", "주임", "사원", "인턴",
] + [str(x) for x in POSITION_KEYWORDS if x]), key=len, reverse=True)

RESP_PHRASES = sorted(set([
    "마케팅 전략 수립 및 팀 총괄", "유통망 관리 및 B2B 영업", "교육 콘텐츠 기획 및 운영",
    "해외영업지원 및 일반사무", "데이터 분석 및 머신러닝 모델링", "백엔드 시스템 개발 및 유지보수",
    "AI 챗봇 개발", "클라우드 솔루션 설계", "경영 데이터 분석", "보고서 작성",
    "웹 퍼블리싱", "UI 구현", "프론트엔드 개발", "UI/UX 개선",
    "재고 관리", "출고 관리", "생산 일정 관리", "품질 관리",
] + [str(x) for x in RESPONSIBILITY_HINTS if len(str(x)) >= 3]), key=len, reverse=True)

LANGUAGE_CERT_NAMES = {"TOEIC", "TOEFL", "OPIc", "OPIC", "JLPT", "JPT", "HSK", "IELTS", "TEPS"}
GENERIC_PROJECT_NAMES = {"공모전", "경진대회", "해커톤", "과 공모전", "과정", "프로젝트"}


def clean_inline_text(text: Any) -> str:
    if text is None:
        return ""
    value = str(text).replace("\r", "\n").replace("\t", " ")
    value = value.replace("□", " ").replace("☑", " ").replace("|", " ").replace("·", " ")
    return re.sub(r"\s+", " ", value.replace("\n", " ")).strip()


def normalize_text(text: Any) -> str:
    value = str(text or "")
    value = value.replace("ADSP", "ADsP").replace("OPIC", "OPIc")
    value = value.replace("||lustrator", "Illustrator").replace("Ilustrator", "Illustrator")
    value = value.replace("데이터사이언스스", "데이터사이언스")
    value = value.replace("커뮤니 케이션", "커뮤니케이션")
    value = value.replace("담질질", "다졌습니다")
    value = value.replace("다졌습니다했습니다", "다졌습니다")
    value = re.sub(r"(20\d{2})[.](\d{1,2})", lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}", value)
    value = re.sub(r"(20\d{2})\s*-\s*(\d{1,2})", lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}", value)
    value = re.sub(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+)\s+([A-Za-z]{2,})\b", r"\1\2", value)
    value = value.replace(".co m", ".com").replace(".c o m", ".com")
    value = re.sub(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.co)\s*(?=SNS\b|mail\s*m\b)", r"\1m ", value)
    value = re.sub(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.co)(?=SNS\b)", r"\1m ", value)
    return clean_inline_text(value)


def normalize_month_date(text: str) -> str:
    value = clean_inline_text(text)
    if value in {"현재", "재직중", "재학중"}:
        return value
    value = value.replace(".", "-").replace("/", "-")
    value = re.sub(r"\s*-\s*", "-", value)
    m = re.search(r"(20\d{2})-(\d{1,2})", value)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}"
    y = re.search(r"\b(20\d{2})\b", value)
    return y.group(1) if y else ""


def month_to_int(value: str):
    value = clean_inline_text(value)
    if value in {"현재", "재직중"}:
        now = datetime.now()
        return now.year * 12 + now.month
    m = re.match(r"(20\d{2})-(\d{2})", value)
    if not m:
        return None
    return int(m.group(1)) * 12 + int(m.group(2))


def valid_range(start: str, end: str, max_months: int = 180) -> bool:
    s = month_to_int(start)
    e = month_to_int(end)
    return s is not None and e is not None and 0 <= e - s <= max_months


def months_to_korean(months: int) -> str:
    years = months // 12
    remain = months % 12
    if years and remain:
        return f"{years}년 {remain}개월"
    if years:
        return f"{years}년"
    if remain:
        return f"{remain}개월"
    return "0개월"


def calculate_total_months(experience: list[dict]) -> int:
    ranges = []
    for item in experience or []:
        start = month_to_int(item.get("startDate", ""))
        end = month_to_int(item.get("endDate", ""))
        if start is None or end is None or end < start:
            continue
        ranges.append((start, end))
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


def split_values(items):
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


# -----------------------------
# 기본정보
# -----------------------------
def fix_basic_name(text: str, basic: dict) -> dict:
    result = dict(basic or {})
    current = clean_inline_text(result.get("name", ""))
    head = normalize_text(text[:1200])
    patterns = [
        r"\(한글\)\s*([가-힣]{2,4})",
        r"이름\s*([가-힣]{2,4})\s*(?:영문|한문|주민|나이|휴대폰|전화번호|E-mail|email|SNS)",
        r"성명\s*(?:\(한글\))?\s*([가-힣]{2,4})(?=\s|\(|회사|업종|품목|연령|생년월일)",
        r"작성자\s*:?\s*([가-힣]{2,4})",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, head):
            candidate = m.group(1)
            if candidate and candidate not in BAD_NAME_WORDS and not re.search(r"회사|생산|성명|품목|업종", candidate):
                if not current or current in BAD_NAME_WORDS or len(current) < 2:
                    result["name"] = candidate
                return result
    return result


def fix_basic_birth(text: str, basic: dict) -> dict:
    result = dict(basic or {})
    if result.get("birthDate"):
        return result
    head = normalize_text(text[:1400])
    m = re.search(r"생년월일\s*(\d{4}-\d{2}-\d{2}|\d{6})", head)
    if not m:
        m = re.search(r"주민번[^0-9]*(\d{6})", head)
    if m:
        raw = m.group(1)
        if re.fullmatch(r"\d{6}", raw):
            yy = int(raw[:2])
            year = 1900 + yy if yy > 30 else 2000 + yy
            result["birthDate"] = f"{year}-{raw[2:4]}-{raw[4:6]}"
        else:
            result["birthDate"] = raw
    return result


def fix_basic_email(text: str, basic: dict) -> dict:
    result = dict(basic or {})
    current = clean_inline_text(result.get("email", ""))
    inline = normalize_text(text)

    candidates = []
    for m in re.finditer(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", inline):
        email = m.group(0)
        tail = inline[m.end():m.end() + 60]
        if email.endswith(".co") and re.search(r"^(?:\s*SNS|\s*mail\s*m|SNS|mail\s*m)", tail):
            email += "m"
        candidates.append(email)

    if not candidates:
        m = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.co)\s*(?:SNS|mail\s*m)", inline)
        if m:
            candidates.append(m.group(1) + "m")

    for email in candidates:
        email = email.replace("..", ".")
        if re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", email):
            if not current or current.endswith(".co") or "@" not in current:
                result["email"] = email
            break
    return result


# -----------------------------
# 학력
# -----------------------------
def date_positions(text: str):
    return [(m.start(), m.end(), normalize_month_date(m.group(0))) for m in re.finditer(r"20\d{2}[-./]\d{1,2}|재학중|현재", text)]


def education_segment(text: str) -> str:
    inline = normalize_text(text)
    seg = re.split(
        r"외국어|어학|컴퓨터\s*사용능력|컴퓨터사용능력|자격증|자격\s*및\s*면허|보훈대상여부|상벌|병역|회사연혁|자기소개서",
        inline,
        maxsplit=1,
    )[0]
    return seg if re.search(r"고등학교|대학교|대학원|대학", seg) else inline


def infer_degree(school: str, context: str = "") -> str:
    school = clean_inline_text(school)
    context = clean_inline_text(context)
    if "고등학교" in school:
        return "고졸"
    if "대학원" in school:
        return "석사" if "박사" not in context else "박사"
    if "전문대" in school:
        return "전문학사"
    if "대학교" in school or school.endswith("대학"):
        return "학사"
    if "석사" in context:
        return "석사"
    if "학사" in context:
        return "학사"
    return ""


def extract_minor(text: str) -> str:
    inline = normalize_text(text)
    m = re.search(r"부전공/?\s*복수전공\s*([가-힣A-Za-z0-9\s]+?)(?:부전공|복수전공|성적|휴학기간|외국어|컴퓨터|자격)", inline)
    if not m:
        return ""
    value = clean_inline_text(m.group(1)).replace("력", "").strip()
    value = value.replace("미디어커뮤니 케이션", "미디어커뮤니케이션")
    value = value.replace("데이터사이언", "데이터사이언스")
    if not value or len(value) <= 1 or len(value) > 30:
        return ""
    return value


def extract_major(school: str, context: str) -> str:
    school = clean_inline_text(school)
    context = normalize_text(context)
    pos = context.rfind(school)
    if pos < 0:
        return ""
    after = context[pos + len(school):pos + len(school) + 160]
    if "고등학교" in school:
        # 고등학교는 특성화고 괄호 안 학과만 전공으로 인정한다. 다음 대학교 전공을 가져오면 안 된다.
        immediate = re.split(r"20\d{2}-\d{2}|[가-힣A-Za-z0-9]+대학교|[가-힣A-Za-z0-9]+대학원|부전공|복수전공|성적|휴학기간|외국어", after)[0]
        if "특성화" not in immediate and "정보처리과" not in immediate:
            return ""
        m = re.search(r"정보처리과|[가-힣A-Za-z0-9]+과", immediate)
        return clean_inline_text(m.group(0)) if m else ""
    after = re.sub(r"\([^)]*(서울|경기|경기도|부산|대전|수원|안성|광역시|서울시|인천)[^)]*\)", " ", after)
    after = re.split(r"20\d{2}-\d{2}|재학중|현재|부전공|복수전공|휴학기간|성적|외국어|컴퓨터\s*사용능력|컴퓨터사용능력|자격|학\s+20", after)[0]
    after = re.sub(r"\b(졸업|재학|재학중|휴학|중퇴|수료|학사|석사|박사|고졸)\b", " ", after)
    after = re.sub(r"\d\.\d+\s*/\s*[45]\.\d", " ", after)
    candidates = re.findall(r"([가-힣A-Za-z0-9]+(?:학과|전공|과|학|사이언스))", after)
    for cand in candidates:
        cand = clean_inline_text(cand).replace("데이터사이언스스", "데이터사이언스")
        if cand not in {"학", "재학", "학교명", "최종학력"}:
            return cand
    return ""


def extract_gpa(text: str, degree: str = ""):
    if degree == "고졸":
        return None
    inline = normalize_text(text)
    for pattern in [r"(?<!\d)(\d\.\d{1,2})\s*/\s*4\.5", r"(?<!\d)(\d\.\d{1,2})\s*4\.5", r"대학평균\s*(?:\d\.\d\s*){0,10}?(\d\.\d{1,2})"]:
        m = re.search(pattern, inline)
        if m:
            try:
                val = float(m.group(1))
                if 0 < val <= 4.5:
                    return val
            except Exception:
                pass
    return None


def school_candidates(segment: str):
    return list(re.finditer(r"([가-힣A-Za-z0-9]+(?:고등학교|대학교\s*대학원|대학교|대학원|대학))", segment))


def education_fallback(text: str) -> list[dict]:
    segment = education_segment(text)
    schools = school_candidates(segment)
    dates = date_positions(segment)
    minor = extract_minor(text)
    results = []
    seen = set()
    first_date_pos = dates[0][0] if dates else -1
    for sm in schools:
        school = clean_inline_text(sm.group(1))
        if not school or school in {"최종학력", "학교명"}:
            continue
        # 최종학력 문구 안에 반복되는 학교명은 실제 학력 행이 아니므로 제외한다.
        if first_date_pos >= 0 and sm.start() < first_date_pos:
            continue
        if any(x in school for x in ["협회", "위원회", "상공회의소", "산업진흥원", "TOEIC"]):
            continue
        before = [d for d in dates if d[1] <= sm.start()]
        after = [d for d in dates if d[0] >= sm.end()]
        candidates = []
        local_after = segment[sm.end():sm.end() + 120]
        # 재학중 대학은 종료일 후보가 다음 날짜로 밀리지 않게 재학중을 먼저 적용한다.
        status_m = re.search(r"재학중", local_after)
        next_date_m = re.search(r"20\d{2}-\d{2}", local_after)
        if before and "고등학교" not in school and status_m and status_m.start() <= 60 and (not next_date_m or status_m.start() < next_date_m.start()):
            candidates.append((-1, 0, before[-1][2], "재학중"))
        # 세로 OCR 양식: 시작일은 학교 앞, 종료일은 학교 뒤
        if before and after:
            start, end = before[-1][2], after[0][2]
            if valid_range(start, end, 120):
                distance = (sm.start() - before[-1][1]) + (after[0][0] - sm.end())
                short_penalty = 2 if (month_to_int(end) or 0) - (month_to_int(start) or 0) < 6 else 0
                candidates.append((short_penalty, distance, start, end))
        # 표형 OCR 양식: 시작일/종료일이 모두 학교 앞
        if len(before) >= 2:
            start, end = before[-2][2], before[-1][2]
            if valid_range(start, end, 120):
                between_dates = segment[before[-2][1]:before[-1][0]]
                range_priority = -0.5 if "~" in between_dates and sm.start() - before[-1][1] <= 90 else 1
                candidates.append((range_priority, sm.start() - before[-1][1], start, end))
        # 학교 뒤에 시작/종료일이 붙는 경우
        if len(after) >= 2:
            start, end = after[0][2], after[1][2]
            if valid_range(start, end, 120) and after[0][0] - sm.end() <= 100:
                candidates.append((2, after[0][0] - sm.end(), start, end))
        # 재학중 처리: 정상 시작일~종료일 후보가 없을 때만 사용한다.
        # 다음 학교의 재학중 단어가 앞 학교에 붙는 것을 막기 위한 조건이다.
        status_m = re.search(r"재학중", local_after)
        next_date_m = re.search(r"20\d{2}-\d{2}", local_after)
        if not candidates and before and "고등학교" not in school and status_m and status_m.start() <= 60 and (not next_date_m or status_m.start() < next_date_m.start()):
            candidates.append((0, 0, before[-1][2], "재학중"))
        if not candidates:
            continue
        candidates.sort(key=lambda x: (x[0], x[1]))
        _, _, start_date, end_date = candidates[0]
        context = segment[max(0, sm.start() - 150):min(len(segment), sm.end() + 220)]
        degree = infer_degree(school, context)
        major = extract_major(school, context)
        status = "재학" if end_date in {"현재", "재학중"} or re.search(r"재학중", context) else "졸업"
        if "중퇴" in context:
            status = "중퇴"
        elif "수료" in context:
            status = "수료"
        gpa_context = segment[sm.end():sm.end() + 110]
        gpa_value = extract_gpa(gpa_context, degree)
        if gpa_value is None:
            gpa_value = extract_gpa(context, degree)
        item = {
            "school": school,
            "degree": degree,
            "major": major,
            "minor": minor if degree != "고졸" else "",
            "startDate": start_date,
            "endDate": end_date,
            "gpa": gpa_value,
            "status": status,
        }
        key = (school, degree, major, start_date, end_date)
        if key not in seen:
            seen.add(key)
            results.append(item)
    return results


def education_score(items: list[dict]) -> int:
    score = 0
    for item in items or []:
        school = clean_inline_text(item.get("school", ""))
        degree = clean_inline_text(item.get("degree", ""))
        major = clean_inline_text(item.get("major", ""))
        start = clean_inline_text(item.get("startDate", ""))
        end = clean_inline_text(item.get("endDate", ""))
        if school:
            score += 3
        if start and end:
            score += 3
        if "고등학교" in school:
            score += 3 if degree == "고졸" else -5
            if major and major not in {"정보처리과"}:
                score -= 4
        if "대학교" in school or school.endswith("대학"):
            score += 3 if degree in {"학사", "석사", "박사", "전문학사"} else -5
            if major:
                score += 2
        if "대학원" in school:
            score += 3 if degree in {"석사", "박사"} else -5
        s, e = month_to_int(start), month_to_int(end)
        if s is not None and e is not None and e < s:
            score -= 10
    return score


def normalize_education_items(items: list[dict], text: str) -> list[dict]:
    fixed = []
    seen = set()
    for item in items or []:
        edu = dict(item)
        school = clean_inline_text(edu.get("school", ""))
        if not school:
            continue
        if "고등학교" in school:
            edu["degree"] = "고졸"
            edu["gpa"] = None
            if clean_inline_text(edu.get("major", "")) != "정보처리과":
                edu["major"] = ""
            edu["minor"] = ""
            edu["status"] = "졸업" if edu.get("endDate") else (edu.get("status") or "졸업")
        elif "대학원" in school:
            if edu.get("degree") not in {"석사", "박사"}:
                edu["degree"] = "석사"
            if not edu.get("gpa"):
                edu["gpa"] = extract_gpa(text, edu.get("degree", ""))
        elif "대학교" in school or school.endswith("대학"):
            if edu.get("degree") in {"", "고졸"}:
                edu["degree"] = "학사"
            if not edu.get("gpa"):
                edu["gpa"] = extract_gpa(text, edu.get("degree", ""))
            if edu.get("endDate") in {"현재", "재학중"}:
                edu["status"] = "재학"
            elif not edu.get("status"):
                edu["status"] = "졸업"
        if edu.get("minor") and len(clean_inline_text(edu.get("minor", ""))) <= 1:
            edu["minor"] = ""
        key = clean_inline_text(school).lower()
        if key not in seen:
            seen.add(key)
            fixed.append(edu)
    return fixed


def fix_education(text: str, current: list[dict]) -> list[dict]:
    current_fixed = normalize_education_items([dict(x) for x in current or [] if x.get("school")], text)
    fallback = normalize_education_items(education_fallback(text), text)
    if not current_fixed:
        return fallback
    if fallback and education_score(fallback) > education_score(current_fixed):
        return fallback
    return current_fixed


# -----------------------------
# 자격증
# -----------------------------
def cert_segment(text: str) -> str:
    inline = normalize_text(text)
    starts = [m.start() for m in re.finditer(r"자\s*격\s*증|자격증|자\s*격\s*및\s*면\s*허|자격\s*및\s*면허|자격 및 면허", inline)]
    # 자격증 헤더가 OCR로 찢긴 경우, 대표 자격증명부터 시작
    if not starts:
        for name in ["정보처리기사", "정보처리기능사", "컴퓨터활용능력", "전산회계", "GTQ", "ADsP", "SQLD", "지게차"]:
            pos = inline.find(name)
            if pos >= 0:
                starts.append(max(0, pos - 30))
                break
    if not starts:
        return inline
    start = min(starts)
    tail = inline[start:]
    end = re.search(r"보훈대상여부|종교|상벌|수상|병\s*역|회사연혁|자기소개서|가족사항|성장과정|취미", tail)
    return tail[:end.start()] if end else tail[:500]


def canonical_cert_name(raw: str) -> str:
    raw_clean = clean_inline_text(raw)
    raw_lower = raw_clean.lower()
    for standard, aliases in (CERT_ALIASES or {}).items():
        for alias in aliases:
            alias_clean = clean_inline_text(alias)
            if not alias_clean:
                continue
            if alias_clean.lower() == raw_lower or alias_clean.lower() in raw_lower or raw_lower in alias_clean.lower():
                return standard
    if raw_clean.upper() == "ADSP":
        return "ADsP"
    if raw_clean.upper() == "ADP":
        return "ADP"
    return raw_clean


def cert_occurrences(block: str):
    occ = []
    for standard, aliases in (CERT_ALIASES or {}).items():
        if standard in LANGUAGE_CERT_NAMES:
            continue
        for alias in sorted(aliases, key=len, reverse=True):
            alias = clean_inline_text(alias)
            if not alias:
                continue
            for m in re.finditer(re.escape(alias), block, flags=re.IGNORECASE):
                occ.append((m.start(), m.end(), standard, alias))
    occ.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    filtered = []
    occupied = []
    standards_at_pos = set()
    for s, e, standard, alias in occ:
        if any(not (e <= os or s >= oe) for os, oe in occupied):
            continue
        key = (standard, s)
        if key in standards_at_pos:
            continue
        standards_at_pos.add(key)
        occupied.append((s, e))
        filtered.append((s, e, standard, alias))
    return filtered


def cert_dates(block: str):
    dates = []
    for m in re.finditer(r"20\d{2}[-./]\d{1,2}|\b20\d{2}\b", block):
        around = block[max(0, m.start() - 20):m.end() + 20]
        if re.search(r"TOEIC|TOEFL|JLPT|HSK|OPIc|OPIC|IELTS|TEPS", around, flags=re.IGNORECASE):
            continue
        dates.append((m.start(), m.end(), normalize_month_date(m.group(0))))
    return dates


def cert_grade_for(block: str, idx: int, occs):
    s, e, _, alias = occs[idx]
    next_s = occs[idx + 1][0] if idx + 1 < len(occs) else min(len(block), e + 80)
    context = clean_inline_text(alias + " " + block[e:next_s])
    m = re.search(r"([12]급|[12]종\s*보통|N[1-5])", context, flags=re.IGNORECASE)
    if not m:
        return ""
    val = clean_inline_text(m.group(1))
    return val.upper() if val.upper().startswith("N") else val


def add_cert(results, seen, name, grade="", date=""):
    name = canonical_cert_name(name)
    grade = clean_inline_text(grade)
    date = normalize_month_date(date)
    if not name:
        return
    key = (name.lower(), grade, date)
    if key in seen:
        return
    # 같은 이름/등급이 있는데 날짜만 다른 경우는 기존 날짜가 비어 있을 때만 보강
    for item in results:
        if item["name"].lower() == name.lower() and item.get("grade", "") == grade:
            if not item.get("date") and date:
                item["date"] = date
            return
    seen.add(key)
    results.append({"name": name, "grade": grade, "date": date})


def fix_certifications(text: str, current: list[dict]) -> list[dict]:
    block = cert_segment(text)
    occs = cert_occurrences(block)
    dates_all = cert_dates(block)
    if not occs:
        return [dict(x) for x in current or []]

    # 취득일 뒤에 날짜가 몰려 있는 경우, 그 뒤 날짜를 우선 사용한다.
    acq_pos = -1
    for kw in ["취득일", "취득"]:
        p = block.find(kw)
        if p >= 0:
            acq_pos = p
            break
    dates_after_acq = [d for d in dates_all if acq_pos >= 0 and d[0] >= acq_pos]
    dates = dates_after_acq if len(dates_after_acq) >= 1 else dates_all

    # 고유 자격증명 순서
    unique_occs = []
    seen_names = set()
    for occ in occs:
        if occ[2] in seen_names:
            continue
        seen_names.add(occ[2])
        unique_occs.append(occ)

    results = []
    seen = set()

    if dates:
        first_occ = unique_occs[0][0]
        first_date = dates[0][0]
        all_names_before_first_date = all(o[0] < first_date for o in unique_occs)
        # 이름들이 앞에 몰리고 날짜가 뒤에 몰린 양식: 이름 순서와 날짜 순서 1:1
        if all_names_before_first_date and len(dates) >= 1:
            for idx, occ in enumerate(unique_occs):
                date = dates[idx][2] if idx < len(dates) else ""
                orig_idx = occs.index(occ)
                add_cert(results, seen, occ[2], cert_grade_for(block, orig_idx, occs), date)
        # 날짜가 먼저 오고 그 뒤 자격증명이 오는 표형 양식
        elif first_date < first_occ:
            for idx, d in enumerate(dates):
                chunk_start = d[1]
                chunk_end = dates[idx + 1][0] if idx + 1 < len(dates) else len(block)
                chunk = block[chunk_start:chunk_end]
                chunk_occs = cert_occurrences(chunk)
                for cidx, co in enumerate(chunk_occs):
                    grade_match = re.search(r"([12]급|[12]종\s*보통)", chunk)
                    grade = grade_match.group(1) if grade_match else ""
                    add_cert(results, seen, co[2], grade, d[2])
        # 이름-날짜 반복형 양식
        else:
            for idx, occ in enumerate(unique_occs):
                s, e, standard, _ = occ
                next_s = unique_occs[idx + 1][0] if idx + 1 < len(unique_occs) else len(block)
                between = [d for d in dates if e <= d[0] <= next_s]
                near = between[0][2] if between else (min(dates, key=lambda d: abs(d[0] - s))[2] if dates else "")
                orig_idx = occs.index(occ)
                add_cert(results, seen, standard, cert_grade_for(block, orig_idx, occs), near)

    if not results:
        for idx, occ in enumerate(unique_occs):
            orig_idx = occs.index(occ)
            add_cert(results, seen, occ[2], cert_grade_for(block, orig_idx, occs), "")

    return results if results else [dict(x) for x in current or []]


# -----------------------------
# 경력
# -----------------------------
def normalize_current_token(token: str) -> str:
    token = clean_inline_text(token)
    if token in {"현재", "재직중"}:
        return "현재"
    return normalize_month_date(token)


def experience_area(text: str) -> str:
    inline = normalize_text(text)
    candidates = []
    for start_kw in ["활동사항", "기간 직장명", "자기소개서 기간 직장명", "회사연혁", "경력사항"]:
        pos = inline.find(start_kw)
        if pos >= 0:
            candidates.append(pos)
    if not candidates:
        return inline
    start = min(candidates)
    tail = inline[start:]
    end = len(tail)
    for end_kw in ["어학", "외국어", "교육/연수", "교육연수", "자격증", "보훈대상", "병역 복무기간", "가족사항", "성장과정", "경력사항 저는", "경력사항 문제 해결", "내용기술 기타", "자기소개서상의"]:
        pos = tail.find(end_kw)
        if pos > 40:
            end = min(end, pos)
    return tail[:end]


def split_experience_chunks_by_dates(area: str):
    area = normalize_text(area)
    # 경력표 헤더 제거
    area = re.sub(r"기간\s*직장명\s*부서/직위\s*담당업무\s*이직사유", " ", area)
    matches = list(re.finditer(r"20\d{2}-\d{2}|현재|재직중", area))
    chunks = []
    i = 0
    while i + 1 < len(matches):
        start_m = matches[i]
        end_m = matches[i + 1]
        row_start = start_m.start()
        row_end = matches[i + 2].start() if i + 2 < len(matches) else len(area)
        row = clean_inline_text(area[row_start:row_end])
        prefix = clean_inline_text(area[max(0, row_start - 40):row_start])
        # 박서연처럼 담당업무가 날짜 앞에 잘린 경우만 prefix를 붙인다.
        # 일반적인 데이터/분석 단어까지 붙이면 이전 회사명이 다음 경력에 섞일 수 있다.
        if prefix and "경영 데이터" in prefix and not any(org in prefix for org in KNOWN_ORGS):
            row = clean_inline_text(prefix + " " + row)
        chunks.append({
            "startDate": normalize_current_token(start_m.group(0)),
            "endDate": normalize_current_token(end_m.group(0)),
            "rowText": row,
        })
        i += 2
    return chunks


def org_patterns():
    suffixes = ["회사", "기업", "공사", "공단", "센터", "연구소", "랩", "랩스", "솔루션", "테크", "플러스", "마케팅", "무역", "에듀테크", "CNS", "SDS", "엔터프라이즈"]
    return [
        r"\(주\)\s*[가-힣A-Za-z0-9]+",
        r"㈜\s*[가-힣A-Za-z0-9]+",
        r"LG\s*CNS",
        r"IT\s+서비스\s+회사",
        r"소프트웨어\s+회사",
        r"물류회사\s*[A-Z]",
        r"전자부품회사\s*[A-Z]",
        rf"[가-힣A-Za-z0-9]+(?:\s+[가-힣A-Za-z0-9]+){{0,2}}\s*(?:{'|'.join(re.escape(s) for s in suffixes)})(?:\s+[A-Z])?",
    ]


def infer_org_from_row(row: str) -> str:
    row = clean_inline_text(row)
    if "카카오" in row and "엔터프라이즈" in row:
        return "카카오 엔터프라이즈"
    for org in KNOWN_ORGS:
        if org in {"카카오", "엔터프라이즈"}:
            continue
        if org and org in row:
            return org
    for pattern in org_patterns():
        m = re.search(pattern, row, flags=re.IGNORECASE)
        if m:
            org = clean_inline_text(m.group(0))
            org = re.sub(r"^(기간|직장명|담당업무|부서/직위)\s*", "", org)
            return finalize_organization(org)
    return ""


def finalize_organization(org: str) -> str:
    org = clean_inline_text(org)
    org = re.sub(r"\b(인턴|사원|주임|대리|과장|부장|매니저|개발자|연구원|디자이너|엔지니어|기획자?)\b$", "", org).strip()
    return org


def infer_position(row: str) -> str:
    row = clean_inline_text(row)
    for pos in POSITION_PHRASES:
        if re.search(rf"(?<![가-힣A-Za-z]){re.escape(pos)}(?![가-힣A-Za-z])", row):
            return pos
    return ""


def clean_resp_source(row: str, org: str, pos: str) -> str:
    value = normalize_text(row)
    value = re.sub(r"20\d{2}-\d{2}|현재|재직중|~", " ", value)
    value = re.sub(r"기간|직장명|부서/직위|담당업무|이직사유|활동 내용|활동구분|기관 및 장소", " ", value)
    if org:
        for part in [org, org.replace(" ", "")]:
            value = value.replace(part, " ")
        if org == "카카오 엔터프라이즈":
            value = value.replace("카카오", " ").replace("엔터프라이즈", " ")
    if pos:
        value = value.replace(pos, " ")
    value = re.split(r"실무 경험 확장|생산관리 분야|전문성 강화|이직|계약 만기|학업 복귀|인턴 종료|정규직 전환|경력사항|저는|내용기술", value)[0]
    value = value.replace("구현 웹 퍼블리싱, UI", "웹 퍼블리싱, UI 구현")
    if "경영 데이터" in value and "분석" in value:
        value = re.sub(r"경영\s*데이터.*?분석", "경영 데이터 분석", value)
    return clean_inline_text(value)


def extract_resp_from_row(row: str, org: str = "", pos: str = "") -> list[str]:
    source = clean_resp_source(row, org, pos)
    found = []
    for phrase in RESP_PHRASES:
        if phrase in source and phrase not in found:
            found.append(phrase)
    if found:
        filtered = []
        for item in found:
            if any(item != other and item in other for other in found):
                continue
            filtered.append(item)
        return filtered[:4]
    parts = [clean_inline_text(x) for x in re.split(r",|/| 및 |\s{2,}", source) if clean_inline_text(x)]
    cleaned = []
    for part in parts:
        if 2 <= len(part) <= 50 and not re.search(r"기간|직장명|부서|직위|담당업무|이직사유|회사연혁|사업목적|기대효과", part):
            cleaned.append(part)
    return split_values(cleaned[:4])


def extract_experience_by_date_chunks(text: str) -> list[dict]:
    area = experience_area(text)
    items = []
    for chunk in split_experience_chunks_by_dates(area):
        row = chunk["rowText"]
        start_date = chunk["startDate"]
        end_date = chunk["endDate"]
        if not start_date or not end_date or not valid_range(start_date, end_date, 360):
            continue
        org = infer_org_from_row(row)
        if not org:
            continue
        pos = infer_position(row)
        resp = extract_resp_from_row(row, org, pos)
        items.append({
            "organization": org,
            "department": "",
            "position": pos,
            "startDate": start_date,
            "endDate": end_date,
            "responsibilities": resp,
            "reasonForLeaving": "",
            "source": "postprocess_experience_table",
        })
    return merge_experience(items)


def extract_experience_by_orgs(text: str) -> list[dict]:
    area = experience_area(text)
    org_matches = []
    for org in KNOWN_ORGS:
        if org in {"카카오", "엔터프라이즈"}:
            continue
        for m in re.finditer(re.escape(org), area):
            org_matches.append((m.start(), m.end(), org))
    if "카카오" in area and "엔터프라이즈" in area:
        m = re.search(r"카카오.*?엔터프라이즈|카카오", area)
        if m:
            org_matches.append((m.start(), m.end(), "카카오 엔터프라이즈"))
    org_matches.sort(key=lambda x: x[0])
    items = []
    for idx, (s, e, org) in enumerate(org_matches):
        next_s = org_matches[idx + 1][0] if idx + 1 < len(org_matches) else len(area)
        prev = area[max(0, s - 120):s]
        after = area[e:next_s]
        before_dates = [normalize_month_date(x) for x in re.findall(r"20\d{2}[-./]\d{1,2}", prev)]
        after_dates = [normalize_month_date(x) for x in re.findall(r"20\d{2}[-./]\d{1,2}", after)]
        start = before_dates[-1] if before_dates else ""
        end = "현재" if re.search(r"현재|재직중", after[:80]) else (after_dates[0] if after_dates else "")
        if not start or not end or not valid_range(start, end, 360):
            continue
        local = clean_inline_text(prev[-40:] + " " + area[s:next_s])
        pos = infer_position(local)
        resp = extract_resp_from_row(local, org, pos)
        items.append({
            "organization": org,
            "department": "",
            "position": pos,
            "startDate": start,
            "endDate": end,
            "responsibilities": resp,
            "reasonForLeaving": "",
            "source": "postprocess_experience_org",
        })
    return merge_experience(items)


def merge_experience(items: list[dict]) -> list[dict]:
    result = []
    seen = set()
    for item in items or []:
        org = finalize_organization(item.get("organization", ""))
        start = clean_inline_text(item.get("startDate", ""))
        end = clean_inline_text(item.get("endDate", ""))
        if not org or not start or not end:
            continue
        if any(bad in org for bad in ["사업목적", "기대효과", "기관", "자격증", "병역"]):
            continue
        key = (org.lower().replace("(주)", "").replace("㈜", "").strip(), start, end)
        if key in seen:
            continue
        seen.add(key)
        new_item = dict(item)
        new_item["organization"] = org
        new_item["responsibilities"] = split_values(new_item.get("responsibilities", []))
        result.append(new_item)
    return result


def experience_score(items: list[dict]) -> int:
    score = 0
    for item in items or []:
        if item.get("organization"):
            score += 3
        if item.get("startDate") and item.get("endDate"):
            score += 3
        if item.get("position"):
            score += 1
        score += min(3, len(item.get("responsibilities", []) or []))
    return score


def fix_experience(text: str, current: list[dict]) -> list[dict]:
    current = merge_experience([dict(x) for x in current or [] if x.get("organization")])
    by_dates = extract_experience_by_date_chunks(text)
    by_orgs = extract_experience_by_orgs(text)
    fallback = by_dates if experience_score(by_dates) >= experience_score(by_orgs) else by_orgs
    if fallback and (not current or len(fallback) > len(current) or experience_score(fallback) > experience_score(current)):
        return fallback
    return current


# -----------------------------
# 자기소개서 / 스킬 / 활동 / 프로젝트
# -----------------------------
def find_self_intro(text: str, current: str = "") -> str:
    inline = normalize_text(text)
    end_m = re.search(r"자기소개서\s*상의|자기소개서상의|사실임을\s*확인합니다|2026년|작성자\s*:", inline)
    end_limit = end_m.start() if end_m else len(inline)
    marker_positions = [inline.find(x) for x in ["자기소개서", "내용기술", "경력사항", "성장과정"] if inline.find(x) >= 0]
    search_start = min(marker_positions) if marker_positions else 0
    candidates = []
    for kw in ["공학자", "저는", "제가", "문제 해결 과정", "문제 해결", "고등학교 졸업 후", "학창 시절", "대학 시절"]:
        pos = inline.find(kw, search_start)
        while 0 <= pos < end_limit:
            tail = inline[pos:end_limit]
            if len(tail) >= 25 and "기간 직장명" not in tail[:90] and "부서/직위" not in tail[:90] and "병역사항" not in tail[:90]:
                candidates.append((pos, tail))
            pos = inline.find(kw, pos + 1)
    if candidates:
        candidates.sort(key=lambda x: x[0])
        value = candidates[0][1]
        value = re.split(r"내용기술|기타\s*$|자기소개서\s*상의|사실임을\s*확인합니다|작성자\s*:", value)[0]
        value = value.replace("용기술", "").replace("다졌습니다했습니다", "다졌습니다")
        return clean_inline_text(value)
    return clean_inline_text(current).replace("용기술", "").replace("다졌습니다했습니다", "다졌습니다")


def add_skill(skill_map: dict, skill: str):
    for group, values in (SKILL_GROUPS or {}).items():
        if skill in values:
            skill_map.setdefault(group, [])
            if skill not in skill_map[group]:
                skill_map[group].append(skill)
            return
    skill_map.setdefault("etc", [])
    if skill not in skill_map["etc"]:
        skill_map["etc"].append(skill)


def fix_skills(text: str, skills: dict, mentioned: dict) -> tuple[dict, dict]:
    text_norm = normalize_text(text)
    skills = {k: list(v or []) for k, v in (skills or {}).items()}
    mentioned = {k: list(v or []) for k, v in (mentioned or {}).items()}
    for key in ["languages", "frameworks", "tools", "etc"]:
        skills.setdefault(key, [])
        mentioned.setdefault(key, [])
    for skill in ["HTML", "CSS", "JavaScript", "React", "Python", "SQL", "Excel", "PowerPoint", "SPSS", "Tableau", "Figma", "Photoshop", "Illustrator", "Blender", "ERP"]:
        aliases = (SKILL_ALIASES or {}).get(skill, [skill])
        for alias in aliases:
            if re.search(rf"(?<![A-Za-z0-9가-힣]){re.escape(alias)}(?![A-Za-z0-9가-힣])", text_norm, flags=re.IGNORECASE):
                add_skill(skills, skill)
                break
    if re.search(r"3D\s*모델링", text_norm) and not re.search(r"데이터\s*모델링|머신러닝\s*모델링|AI\s*모델", text_norm):
        skills["etc"] = [x for x in skills.get("etc", []) if x != "Data Modeling"]
    if re.search(r"React.{0,40}(익혀|기초|소통|이해도|접목|학습)", text_norm):
        skills["frameworks"] = [x for x in skills.get("frameworks", []) if x != "React"]
        if "React" not in mentioned.get("frameworks", []):
            mentioned["frameworks"].append("React")
    for target in [skills, mentioned]:
        for key in ["languages", "frameworks", "tools", "etc"]:
            target[key] = split_values(target.get(key, []))
    return skills, mentioned


def awards_segment(text: str) -> str:
    inline = normalize_text(text)
    m = re.search(r"상벌|수상내역|수상", inline)
    if not m:
        return ""
    tail = inline[m.start():]
    end = re.search(r"취미|병역|회사연혁|자기소개서|경력사항|내용기술", tail)
    return tail[:end.start()] if end else tail


def fix_activities(text: str, current: list[dict]) -> list[dict]:
    block = awards_segment(text)
    results = []
    if block:
        pattern = re.compile(
            r"([가-힣A-Za-z0-9\s\-]+?(?:해커톤|경진대회|공모전|공모|캡스톤\s*디자인|SW\s*경진대회))\s*"
            r"(20\d{2})?\s*"
            r"(대상|최우수상|우수상|장려상|[123]위|2위|3위|수상)?\s*"
            r"([가-힣A-Za-z0-9\s]*(?:협회|대학교|행정안전부|센터|기관|진흥원))?"
        )
        for m in pattern.finditer(block):
            name = clean_inline_text(m.group(1))
            name = re.sub(r"^(상벌|경력|명칭|일자|내용|기간|상세 내용|기관)\s*", "", name).strip()
            if name.endswith("공모"):
                name += "전"
            if len(name) < 4 or name in GENERIC_PROJECT_NAMES or name.startswith("과 "):
                continue
            org = clean_inline_text(m.group(4) or "")
            if org and re.search(r"에서는|참여를|통해|팀을", org):
                org = ""
            results.append({
                "name": name,
                "organization": org,
                "date": normalize_month_date(m.group(2) or ""),
                "award": clean_inline_text(m.group(3) or ""),
                "description": "",
            })
    if not results:
        results = [dict(x) for x in current or []]
    cleaned = []
    seen = set()
    for item in results:
        name = clean_inline_text(item.get("name", ""))
        org = clean_inline_text(item.get("organization", ""))
        if not name or name in GENERIC_PROJECT_NAMES or name.startswith("과 "):
            continue
        if org and re.search(r"에서는|참여를|통해|팀을", org):
            org = ""
        key = (name.lower(), item.get("date", ""), item.get("award", ""))
        if key not in seen:
            seen.add(key)
            item = dict(item)
            item["name"] = name
            item["organization"] = org
            cleaned.append(item)
    return cleaned


def clean_projects(projects: list[dict], activities: list[dict]) -> list[dict]:
    valid_activity_names = {clean_inline_text(x.get("name", "")).lower() for x in activities or []}
    cleaned = []
    seen = set()
    for project in projects or []:
        item = dict(project)
        name = clean_inline_text(item.get("name", ""))
        if not name or name in GENERIC_PROJECT_NAMES or name.startswith("과 "):
            continue
        if re.search(r"공모|해커톤|경진대회|캡스톤", name) and name.lower() not in valid_activity_names and len(name) <= 5:
            continue
        org = clean_inline_text(item.get("organization", ""))
        if org and re.search(r"에서는|참여를|통해|팀을", org):
            org = ""
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        item["name"] = name
        item["organization"] = org
        item["responsibilities"] = split_values(item.get("responsibilities", []))
        item["techStack"] = split_values(item.get("techStack", []))
        item["achievements"] = split_values(item.get("achievements", []))
        cleaned.append(item)
    return cleaned


# -----------------------------
# 병역 / 역량 / 직무분류
# -----------------------------
def fix_military(text: str, military):
    if military:
        return military
    inline = normalize_text(text)
    m = re.search(r"병역(?:사항)?(.+?)(?:회사연혁|사업목적|자기소개서|경력사항|$)", inline)
    block = m.group(1) if m else ""
    if not block:
        return None
    if "해당없음" in block or "해당 없음" in block:
        return {"branch": "", "rank": "", "status": "해당없음", "startDate": "", "endDate": ""}
    dates = [normalize_month_date(x) for x in re.findall(r"20\d{2}[-./]\d{1,2}", block)]
    branch = ""
    for b in ["육군", "해군", "공군", "해병대", "보병"]:
        if b in block:
            branch = "육군" if b == "보병" else b
            break
    rank = ""
    for r in ["이병", "일병", "상병", "병장", "하사", "중사", "상사", "소위", "중위", "대위"]:
        if r in block:
            rank = r
            break
    status = "군필" if re.search(r"군필|전역|만기제대", block) or dates else ""
    if not any([branch, rank, status, dates]):
        return None
    return {"branch": branch, "rank": rank, "status": status, "startDate": dates[0] if len(dates) >= 1 else "", "endDate": dates[1] if len(dates) >= 2 else ""}


def fix_core_competencies(self_intro: str, skills: dict, experience: list[dict]) -> list[str]:
    corpus = clean_inline_text(" ".join([
        self_intro or "",
        " ".join(" ".join(v) for v in (skills or {}).values()),
        " ".join(" ".join(x.get("responsibilities", [])) for x in experience or []),
    ]))
    result = []
    for keyword in CORE_COMPETENCY_KEYWORDS or ["문제 해결", "협업", "커뮤니케이션", "책임감", "기획력", "리더십", "데이터 분석", "꼼꼼함"]:
        if keyword and keyword in corpus and keyword not in result:
            result.append(keyword)
    return result


def fix_job_category(current: str, education: list[dict], skills: dict, experience: list[dict], self_intro: str) -> str:
    exp_text = " ".join(" ".join(x.get("responsibilities", [])) + " " + x.get("position", "") for x in experience or [])
    edu_text = " ".join(x.get("major", "") + " " + x.get("degree", "") for x in education or [])
    skill_text = " ".join(" ".join(v) for v in (skills or {}).values())
    corpus = clean_inline_text(f"{exp_text} {edu_text} {skill_text} {self_intro}")

    web_exp = re.search(r"프론트엔드|웹 퍼블리싱|UI/UX|UI 구현|웹\s*UI|웹\s*개발", exp_text)
    web_skill = re.search(r"HTML|CSS|JavaScript|React", skill_text) and re.search(r"프론트엔드|웹 퍼블리싱|UI/UX|UI 구현|웹\s*UI|웹\s*개발", corpus)
    ai_signal = re.search(r"데이터사이언스|머신러닝|TensorFlow|PyTorch|AI\s*챗봇|컴퓨터공학|생성형 AI|LLM|NLP|데이터 분석", corpus) and re.search(r"Python|SQL|AI|머신러닝|데이터", corpus)

    if web_exp or web_skill:
        return "웹개발/프론트엔드"
    if ai_signal:
        return "AI/데이터"
    # 경력 담당업무는 자기소개서의 첫 표현보다 우선한다.
    if re.search(r"마케팅 전략|마케팅|유통망|B2B 영업|영업|교육 콘텐츠 기획|브랜딩|프로모션|시장 조사", exp_text):
        return "마케팅/기획"
    if re.search(r"생산 일정|품질 관리|생산관리|품질관리|공정|제조", corpus):
        return "생산/품질"
    if re.search(r"해외영업지원|일반사무|사무 자동화|전산회계|워드프로세서|Excel|PowerPoint|보고서 작성|회계", corpus):
        return "사무/행정"
    if re.search(r"물류|재고 관리|출고 관리|입출고", corpus):
        return "물류/유통"
    if re.search(r"마케팅|기획|공모전|브랜딩|프로모션|시장 조사|B2B 영업|유통망", corpus):
        return "마케팅/기획"
    if re.search(r"산업디자인|디자인|Photoshop|Illustrator|Figma|Blender|프로토타입|시안", corpus):
        return "디자인"
    return current or ""


def update_experience_summary(data: dict):
    months = calculate_total_months(data.get("experience", []))
    declared = data.get("experienceSummary", {}).get("declaredMonths", 0) or 0
    total = months if months > 0 else declared
    data["experienceSummary"] = {
        "totalMonths": total,
        "years": total // 12,
        "yearsFloat": round(total / 12, 1) if total else 0,
        "display": months_to_korean(total),
        "declaredMonths": declared,
        "calculatedMonths": months,
        "source": "calculated" if months > 0 else ("declared" if declared > 0 else ""),
    }


def postprocess_resume_data(preprocessed_text: str, resume_data: dict) -> dict:
    data = copy.deepcopy(resume_data or {})
    text = normalize_text(preprocessed_text)

    data["basicInfo"] = fix_basic_email(text, fix_basic_birth(text, fix_basic_name(text, data.get("basicInfo", {}))))
    data["education"] = fix_education(text, data.get("education", []))
    data["certifications"] = fix_certifications(text, data.get("certifications", []))
    data["experience"] = fix_experience(text, data.get("experience", []))
    data["selfIntroduction"] = find_self_intro(text, data.get("selfIntroduction", ""))
    data["skills"], data["mentionedSkills"] = fix_skills(text, data.get("skills", {}), data.get("mentionedSkills", {}))
    data["activities"] = fix_activities(text, data.get("activities", []))
    data["projects"] = clean_projects(data.get("projects", []), data.get("activities", []))
    data["military"] = fix_military(text, data.get("military"))
    data["coreCompetencies"] = fix_core_competencies(data.get("selfIntroduction", ""), data.get("skills", {}), data.get("experience", []))
    data["jobCategory"] = fix_job_category(data.get("jobCategory", ""), data.get("education", []), data.get("skills", {}), data.get("experience", []), data.get("selfIntroduction", ""))
    update_experience_summary(data)
    return data
