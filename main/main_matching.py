import os
import sys
import re

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.firebase_init import init_firebase
from matching.matchtest import (
    flatten_resume,
    flatten_job,
    calculate_full_score,
    get_resume_embedding_text,
    get_job_embedding_text,
    calculate_full_embedding_similarity,
    clear_embedding_cache,
    preload_score_embeddings,
)


def format_experience(experience):
    if isinstance(experience, dict):
        if experience.get("raw"):
            return str(experience.get("raw"))
        if experience.get("type"):
            return str(experience.get("type"))
        if experience.get("minYears") is not None:
            return f"경력 {experience.get('minYears')}년 이상"
        return ""

    return str(experience or "")


def get_job_title(job_raw, job_posting):
    meta = job_raw.get("meta", {}) or {}
    legacy = job_raw.get("legacyJobPosting", {}) or {}

    return (
        job_posting.get("title")
        or legacy.get("title")
        or meta.get("title")
        or job_raw.get("title")
        or ""
    )


def get_company_name(job_raw, job_posting):
    meta = job_raw.get("meta", {}) or {}
    legacy = job_raw.get("legacyJobPosting", {}) or {}
    company_info = job_posting.get("companyInfo", {}) or {}

    return (
        job_posting.get("companyName")
        or job_posting.get("company")
        or company_info.get("name")
        or company_info.get("companyName")
        or legacy.get("companyName")
        or legacy.get("company")
        or meta.get("companyName")
        or meta.get("company")
        or job_raw.get("companyName")
        or job_raw.get("company")
        or ""
    )


def get_location(job_raw, job_posting):
    legacy = job_raw.get("legacyJobPosting", {}) or {}
    work_conditions = job_posting.get("workConditions", {}) or {}
    company_info = job_posting.get("companyInfo", {}) or {}

    return (
        work_conditions.get("location")
        or company_info.get("location")
        or legacy.get("location")
        or job_posting.get("location")
        or job_raw.get("location")
        or ""
    )


def clean_location_output(value):
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    text = text.replace("가산 디지털", "가산디지털")
    text = text.replace("디지털 로", "디지털로")
    text = re.sub(r"([가-힣])\s+([0-9]+로)", r"\1\2", text)

    return text.strip()


def normalize_region_name(region):
    region_map = {
        "서울특별시": "서울",
        "부산광역시": "부산",
        "대구광역시": "대구",
        "인천광역시": "인천",
        "광주광역시": "광주",
        "대전광역시": "대전",
        "울산광역시": "울산",
        "세종특별자치시": "세종",
        "경기도": "경기",
        "강원도": "강원",
        "충청북도": "충북",
        "충청남도": "충남",
        "전라북도": "전북",
        "전라남도": "전남",
        "경상북도": "경북",
        "경상남도": "경남",
        "제주도": "제주",
        "제주특별자치도": "제주",
    }

    return region_map.get(region, region)


def shorten_location(value):
    text = str(value or "").strip()

    if not text:
        return ""

    text = re.sub(r"^(근무지역|근무지|근무장소|근무지주소|주소)\s*[:：]?\s*", "", text)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    cut_keywords = [
        "지도보기",
        "인근지하철",
        "지하철",
        "도보",
        "버스",
        "출구",
        "역에서",
        "역 ",
        "주차",
        "복리후생",
        "근무시간",
        "급여",
        "담당업무",
        "자격요건",
        "우대사항",
    ]

    for keyword in cut_keywords:
        if keyword in text:
            text = text.split(keyword)[0].strip()

    region_pattern = (
        r"(서울|서울특별시|부산|부산광역시|대구|대구광역시|인천|인천광역시|"
        r"광주|광주광역시|대전|대전광역시|울산|울산광역시|세종|세종특별자치시|"
        r"경기|경기도|강원|강원도|충북|충청북도|충남|충청남도|"
        r"전북|전라북도|전남|전라남도|경북|경상북도|경남|경상남도|"
        r"제주|제주도|제주특별자치도)"
    )

    area_pattern = (
        rf"{region_pattern}\s+"
        rf"([가-힣]+(?:시|군|구))"
        rf"(?:\s+([가-힣0-9]+(?:구|군|읍|면|동|가|리)))?"
    )

    area_match = re.search(area_pattern, text)

    if area_match:
        region = normalize_region_name(area_match.group(1))
        first_area = area_match.group(2)
        second_area = area_match.group(3) or ""

        result = f"{region} {first_area}"

        if second_area:
            result += f" {second_area}"

        return result.strip()

    text = clean_location_output(text)

    if len(text) > 15:
        return text[:15].strip() + "..."

    return text


def get_salary(job_raw, job_posting):
    legacy = job_raw.get("legacyJobPosting", {}) or {}
    work_conditions = job_posting.get("workConditions", {}) or {}

    return (
        work_conditions.get("salary")
        or legacy.get("salary")
        or job_posting.get("salary")
        or job_raw.get("salary")
        or ""
    )


def get_category(job_raw, job_posting):
    legacy = job_raw.get("legacyJobPosting", {}) or {}
    job_info = job_posting.get("job", {}) or {}

    return (
        job_posting.get("category")
        or legacy.get("category")
        or job_raw.get("category")
        or job_info.get("department")
        or ""
    )


def get_source_url(job_raw, job_posting):
    meta = job_raw.get("meta", {}) or {}
    legacy = job_raw.get("legacyJobPosting", {}) or {}

    return (
        job_posting.get("sourceUrl")
        or legacy.get("sourceUrl")
        or meta.get("sourceUrl")
        or job_raw.get("sourceUrl")
        or job_posting.get("url")
        or job_raw.get("url")
        or ""
    )


# ============================================================
# 희망 직무/조건 필터링 관련 함수
# ============================================================

def normalize_text(value):
    """
    문자열/리스트/딕셔너리를 검색 가능한 하나의 소문자 문자열로 변환한다.
    """
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join([normalize_text(item) for item in value])

    if isinstance(value, dict):
        return " ".join([normalize_text(item) for item in value.values()])

    return str(value).strip().lower()


def normalize_list(value):
    """
    matchPreferences의 배열 값을 안전하게 정리한다.
    """
    if not value:
        return []

    if isinstance(value, list):
        return [normalize_text(item) for item in value if normalize_text(item)]

    return [normalize_text(value)]


def get_job_filter_text(job_raw):
    """
    공고 원본 데이터에서 필터링에 사용할 텍스트를 최대한 넓게 모은다.
    """
    job_posting = job_raw.get("jobPosting", {}) or {}
    legacy = job_raw.get("legacyJobPosting", {}) or {}
    meta = job_raw.get("meta", {}) or {}

    job = job_posting.get("job", {}) or {}
    requirements = job_posting.get("requirements", {}) or {}
    work_conditions = job_posting.get("workConditions", {}) or {}
    company_info = job_posting.get("companyInfo", {}) or {}

    return normalize_text([
        job_posting.get("title"),
        job_posting.get("companyName"),
        job_posting.get("category"),
        job_posting.get("responsibilities"),

        job.get("department"),
        job.get("employmentType"),
        job.get("hiringCount"),

        requirements.get("requiredSkills"),
        requirements.get("preferredSkills"),
        requirements.get("requiredQualifications"),
        requirements.get("preferredQualifications"),
        requirements.get("coreCompetencies"),
        requirements.get("certifications"),
        requirements.get("education"),
        requirements.get("experience"),

        work_conditions.get("location"),
        work_conditions.get("salary"),

        company_info.get("location"),

        legacy.get("title"),
        legacy.get("companyName"),
        legacy.get("category"),
        legacy.get("location"),
        legacy.get("skills"),
        legacy.get("qualifications"),
        legacy.get("responsibilities"),
        legacy.get("postingType"),
        legacy.get("salary"),

        meta.get("title"),
        meta.get("companyName"),
        meta.get("postingType"),

        job_raw.get("title"),
        job_raw.get("companyName"),
        job_raw.get("company"),
        job_raw.get("category"),
        job_raw.get("location"),
        job_raw.get("postingType"),
        job_raw.get("employmentType"),
        job_raw.get("salary"),
    ])


def matches_role(job_text, desired_roles):
    """
    희망 직무 조건과 공고 텍스트가 맞는지 확인한다.
    조건이 비어 있으면 전체 통과.
    """
    if not desired_roles:
        return True

    role_alias_map = {
        "프론트엔드": "frontend",
        "프론트": "frontend",
        "front-end": "frontend",
        "front end": "frontend",

        "백엔드": "backend",
        "백앤드": "backend",
        "서버": "backend",
        "back-end": "backend",
        "back end": "backend",

        "데이터": "data",
        "데이터분석": "data",
        "분석": "data",

        "인공지능": "ai",
        "머신러닝": "ai",
        "딥러닝": "ai",

        "서비스기획": "planning",
        "기획": "planning",

        "마케팅": "marketing",

        "행정": "admin",
        "사무": "admin",
        "운영": "admin",
    }

    role_keyword_map = {
        "backend": [
            "backend", "back-end", "백엔드", "백앤드", "서버",
            "spring", "java", "node", "api"
        ],
        "frontend": [
            "frontend", "front-end", "front end", "프론트엔드", "프론트",
            "react", "next", "next.js", "vue", "javascript",
            "typescript", "ui", "웹"
        ],
        "data": [
            "data", "데이터", "분석", "sql", "python", "tableau",
            "bi", "데이터분석"
        ],
        "ai": [
            "ai", "인공지능", "머신러닝", "딥러닝", "ml", "llm",
            "모델", "자연어"
        ],
        "planning": [
            "planning", "기획", "서비스기획", "pm", "po", "프로덕트"
        ],
        "marketing": [
            "marketing", "마케팅", "콘텐츠", "브랜딩", "광고", "sns"
        ],
        "admin": [
            "admin", "행정", "사무", "운영", "총무", "문서"
        ],
    }

    for role in desired_roles:
        role = normalize_text(role)

        # 사용자가 프론트엔드/백엔드처럼 한글로 넣어도 내부 기준값으로 변환
        canonical_role = role_alias_map.get(role, role)

        keywords = role_keyword_map.get(canonical_role, [role])

        for keyword in keywords:
            if keyword and keyword in job_text:
                return True

    return False


def matches_location(job_text, desired_locations):
    """
    희망 지역 조건과 공고 텍스트가 맞는지 확인한다.
    조건이 비어 있으면 전체 통과.
    """
    if not desired_locations:
        return True

    for location in desired_locations:
        location = normalize_text(location)

        if location == "전국":
            return True

        if location == "서울":
            if "서울" in job_text or "서울특별시" in job_text:
                return True

        elif location == "경기":
            if (
                "경기" in job_text
                or "경기도" in job_text
                or "성남" in job_text
                or "수원" in job_text
                or "분당" in job_text
                or "판교" in job_text
            ):
                return True

        elif location == "인천":
            if "인천" in job_text or "인천광역시" in job_text:
                return True

        elif location == "부산":
            if "부산" in job_text or "부산광역시" in job_text:
                return True

        elif location == "대전":
            if "대전" in job_text or "대전광역시" in job_text:
                return True

        elif location == "대구":
            if "대구" in job_text or "대구광역시" in job_text:
                return True

        elif location == "광주":
            if "광주" in job_text or "광주광역시" in job_text:
                return True

        elif location and location in job_text:
            return True

    return False


def matches_employment_type(job_text, employment_types):
    """
    희망 근무형태/채용유형과 공고 텍스트가 맞는지 확인한다.
    조건이 비어 있으면 전체 통과.
    """
    if not employment_types:
        return True

    for employment_type in employment_types:
        employment_type = normalize_text(employment_type)

        if employment_type == "인턴":
            if "인턴" in job_text or "intern" in job_text:
                return True

        elif employment_type == "신입":
            if "신입" in job_text or "주니어" in job_text:
                return True

        elif employment_type == "경력":
            if "경력" in job_text:
                return True

        elif employment_type and employment_type in job_text:
            return True

    return False


def is_job_matched_with_preferences(job_raw, match_preferences):
    """
    이력서의 matchPreferences를 기준으로 공고가 조건에 맞는지 판단한다.
    """
    if not isinstance(match_preferences, dict):
        match_preferences = {}

    desired_roles = normalize_list(match_preferences.get("desiredRoles"))
    desired_locations = normalize_list(match_preferences.get("desiredLocations"))
    employment_types = normalize_list(match_preferences.get("employmentTypes"))
    desired_keywords = normalize_list(match_preferences.get("desiredKeywords"))

    job_text = get_job_filter_text(job_raw)

    role_matched = matches_role(job_text, desired_roles)
    location_matched = matches_location(job_text, desired_locations)
    employment_matched = matches_employment_type(job_text, employment_types)
    keyword_matched = (
        not desired_keywords
        or any(keyword in job_text for keyword in desired_keywords)
    )

    return (
        role_matched
        and location_matched
        and employment_matched
        and keyword_matched
    )


def rank_job_candidates(candidates, resume_text, match_preferences, limit=None):
    """Cheap lexical pre-ranking before expensive embedding/NCS scoring."""
    if limit is None:
        limit = int(os.getenv("MATCHING_AI_CANDIDATE_LIMIT", "80"))
    limit = max(10, limit)
    if len(candidates) <= limit:
        return candidates

    preferred = normalize_list((match_preferences or {}).get("desiredKeywords"))
    resume_tokens = set(re.findall(r"[가-힣A-Za-z0-9+#.]{2,}", normalize_text(resume_text)))

    ranked = []
    for index, candidate in enumerate(candidates):
        job_text = get_job_filter_text(candidate[1])
        job_tokens = set(re.findall(r"[가-힣A-Za-z0-9+#.]{2,}", job_text))
        overlap = len(resume_tokens & job_tokens)
        preference_hits = sum(1 for keyword in preferred if keyword in job_text)
        ranked.append((preference_hits * 100 + overlap, -index, candidate))

    ranked.sort(reverse=True)
    return [item[2] for item in ranked[:limit]]


def is_enabled_job_source(job_raw):
    """Exclude preserved legacy crawler data from the active matching pool."""
    configured = os.getenv("JOB_POSTING_ACTIVE_SOURCES", "moef_job_alio")
    enabled_sources = {
        source.strip().lower()
        for source in configured.split(",")
        if source.strip()
    }
    if not enabled_sources or "all" in enabled_sources:
        return True

    job_posting = job_raw.get("jobPosting", {}) or {}
    meta = job_raw.get("meta", {}) or {}
    source = str(
        meta.get("source")
        or job_posting.get("sourceSite")
        or ""
    ).strip().lower()
    return source in enabled_sources


# ============================================================
# 점수 및 정렬 관련 함수
# ============================================================

def get_score_value(item, keys):
    if not isinstance(item, dict):
        return 0

    for key in keys:
        value = item.get(key)

        if value is None or value == "":
            continue

        try:
            value = float(value)

            if 0 < value <= 1:
                return value * 100

            return value
        except Exception:
            pass

    return 0


def get_fit_score(item):
    return get_score_value(item, [
        "fitScore",
        "fit_score",
        "finalScore",
        "final_score",
        "matchRate",
    ])


def get_accessibility_score(item):
    return get_score_value(item, [
        "accessibilityScore",
        "accessibility_score",
    ])


def get_confidence_score(item):
    return get_score_value(item, [
        "confidenceScore",
        "confidence_score",
    ])


def get_recommend_type(item):
    if not isinstance(item, dict):
        return ""

    return (
        item.get("recommendType")
        or item.get("recommend_type")
        or ""
    )


def get_match_badges(item):
    if not isinstance(item, dict):
        return []

    badges = item.get("matchBadges") or item.get("match_badges") or []

    if isinstance(badges, str):
        return [badges]

    if isinstance(badges, list):
        return badges

    return []


def get_recommend_rank(item):
    recommend_type = get_recommend_type(item)
    badges = get_match_badges(item)

    if recommend_type == "부적합" or "부적합" in badges:
        return 0

    if recommend_type == "정보 부족" or "정보 부족" in badges:
        return 1

    if recommend_type == "지원 가능" or "지원 가능" in badges:
        return 2

    if recommend_type == "보통" or "보통" in badges:
        return 3

    if recommend_type == "AI 적합" or "AI 적합" in badges:
        return 5

    return 1


def is_bad_match(item):
    recommend_type = get_recommend_type(item)
    badges = get_match_badges(item)

    if recommend_type == "부적합":
        return True

    if "부적합" in badges:
        return True

    unmet_conditions = item.get("unmetConditions") or item.get("unmet_conditions") or []

    if len(unmet_conditions) >= 1:
        return True

    return False


def is_info_poor_match(item):
    recommend_type = get_recommend_type(item)
    badges = get_match_badges(item)
    confidence_score = get_confidence_score(item)

    if recommend_type == "정보 부족":
        return True

    if "정보 부족" in badges:
        return True

    if confidence_score < 40:
        return True

    return False


def is_fit_candidate(item):
    if is_bad_match(item):
        return False

    if is_info_poor_match(item):
        return False

    return True


def sort_for_fit(item):
    return (
        get_recommend_rank(item),
        get_fit_score(item),
        get_confidence_score(item),
        get_accessibility_score(item),
    )


def sort_for_accessibility(item):
    return (
        get_accessibility_score(item),
        get_recommend_rank(item),
        get_fit_score(item),
        get_confidence_score(item),
    )


def sort_for_confidence(item):
    return (
        get_confidence_score(item),
        get_recommend_rank(item),
        get_fit_score(item),
        get_accessibility_score(item),
    )


def build_matching_groups(results, limit=5):
    fit_candidates = [
        item for item in results
        if is_fit_candidate(item)
    ]

    top_fit_matches = sorted(
        fit_candidates,
        key=sort_for_fit,
        reverse=True
    )[:limit]

    top_accessible_matches = sorted(
        results,
        key=sort_for_accessibility,
        reverse=True
    )[:limit]

    top_confidence_matches = sorted(
        results,
        key=sort_for_confidence,
        reverse=True
    )[:limit]

    return {
        "matches": results,
        "topFitMatches": top_fit_matches,
        "topAccessibleMatches": top_accessible_matches,
        "topConfidenceMatches": top_confidence_matches,
    }


def to_number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_semantic_level(similarity):
    value = to_number(similarity)

    if value >= 0.7:
        return "높게"
    if value >= 0.4:
        return "보통 이상으로"
    if value > 0:
        return "일부"
    return "확인 가능한 정보가 적게"


def build_explanation_summary(
    result,
    rule_details,
    semantic_details,
    ncs_details,
    fit_score,
    accessibility_score,
    confidence_score,
    recommend_type,
):
    strengths = []
    cautions = []
    reason_parts = []

    skill_total = int(to_number(rule_details.get("skill_total_count", 0)))
    skill_matches = int(to_number(rule_details.get("skill_match_count", 0)))

    if skill_total > 0:
        reason_parts.append(f"기술 조건 {skill_total}개 중 {skill_matches}개 일치")

        if skill_matches > 0:
            strengths.append("요구 기술과 보유 기술이 일부 일치합니다.")
        else:
            cautions.append("공고의 필수 기술과 일치하는 이력서 기술이 확인되지 않았습니다.")

    exp_condition_used = bool(rule_details.get("exp_condition_used", True))
    min_exp = to_number(rule_details.get("min_exp", 0))
    resume_exp = to_number(rule_details.get("resume_exp", 0))

    if exp_condition_used and min_exp > 0:
        reason_parts.append(f"요구 경력 {min_exp:g}년 대비 이력서 경력 {resume_exp:g}년")

        if resume_exp >= min_exp:
            strengths.append("요구 경력 조건을 충족합니다.")
        else:
            cautions.append("요구 경력 연수보다 이력서 경력이 부족할 수 있습니다.")

    cert_total = int(to_number(rule_details.get("cert_total_count", 0)))
    cert_matches = int(to_number(rule_details.get("cert_match_count", 0)))

    if cert_total > 0:
        if cert_matches > 0:
            strengths.append("필수 자격증 조건과 일치하는 항목이 있습니다.")
        else:
            cautions.append("필수 자격증 충족 여부를 지원 전에 확인해야 합니다.")

    qual_total = int(to_number(rule_details.get("qual_total_count", 0)))
    matched_quals = rule_details.get("matched_quals", []) or []

    if qual_total > 0:
        if matched_quals:
            strengths.append("필수 자격요건과 연결되는 이력서 항목이 있습니다.")
        else:
            cautions.append("필수 자격요건 충족 근거가 약합니다.")

    full_similarity = semantic_details.get("full_sim", 0)

    if full_similarity:
        reason_parts.append(f"직무 내용 유사도 {get_semantic_level(full_similarity)} 평가")

        if to_number(full_similarity) >= 0.4:
            strengths.append("이력서 내용과 공고 직무 설명의 의미 유사도가 보통 이상입니다.")

    if ncs_details.get("ncs_used", False):
        matched_unit = ncs_details.get("matched_unit_name", "")
        strengths.append(
            f"NCS {matched_unit} 역량 기준으로 보완 평가했습니다."
            if matched_unit
            else "NCS 직무역량 기준으로 보완 평가했습니다."
        )

    unmet_conditions = result.get("unmet_conditions", []) or []

    for condition in unmet_conditions:
        cautions.append(f"{condition} 항목을 확인해야 합니다.")

    reason = (
        ", ".join(reason_parts[:2])
        if reason_parts
        else "이력서와 공고의 조건, 직무 내용, 자격요건을 종합해 계산했습니다."
    )

    if unmet_conditions:
        status_reason = (
            "미충족 조건이 있어 추천 우선순위가 낮게 조정되었습니다: "
            + ", ".join(unmet_conditions[:2])
        )
    else:
        status_reason = (
            f"{recommend_type} 판정은 적합도 {round(fit_score)}점, "
            f"지원 가능성 {round(accessibility_score)}점, "
            f"판단 근거 충분도 {round(confidence_score)}점을 함께 반영했습니다."
        )

    next_action = (
        "지원 전 미충족 조건과 원본 공고의 세부 자격요건을 확인해보세요."
        if unmet_conditions or cautions
        else "지원 전 원본 공고의 우대사항과 제출 서류를 확인해보세요."
    )

    return {
        "reason": reason,
        "statusReason": status_reason,
        "strengths": strengths[:3] or ["이력서와 공고의 조건을 종합해 추천 후보로 분류했습니다."],
        "cautions": cautions[:3] or ["큰 미충족 조건은 발견되지 않았지만 원본 공고 확인이 필요합니다."],
        "nextAction": next_action,
        "source": "rule_based",
    }



# ============================================================
# 이력서 최신 분석 결과 선택 관련 함수
# ============================================================

def has_meaningful_value(value):
    """
    None, 빈 dict, 빈 list, 빈 문자열은 사용 가능한 값이 아니라고 판단한다.
    """
    if value is None:
        return False

    if isinstance(value, dict):
        return len(value) > 0

    if isinstance(value, list):
        return len(value) > 0

    if isinstance(value, str):
        return bool(value.strip())

    return True


def normalize_resume_analysis_payload(analysis):
    """
    Firestore에 저장된 분석 결과 구조를 매칭 함수가 이해할 수 있는 형태로 맞춘다.

    현재 저장 구조:
    effectiveAnalysis: {
        resumeData: {...}
    }

    혹시 사용자가 수정하면서 resumeData 없이 바로 basicInfo, skills 등을 둔 경우도
    기존 flatten_resume 호환을 위해 resumeData로 감싸준다.
    """
    if not isinstance(analysis, dict):
        return {}

    if "resumeData" in analysis:
        return analysis

    resume_data_like_keys = {
        "basicInfo",
        "education",
        "experience",
        "certifications",
        "skills",
        "mentionedSkills",
        "projects",
        "activities",
        "languageTests",
        "selfIntroduction",
        "jobCategory",
        "experienceSummary",
        "coreCompetencies",
        "embeddingText",
        "rawText",
    }

    if any(key in analysis for key in resume_data_like_keys):
        return {
            "resumeData": analysis
        }

    return analysis


def get_latest_resume_analysis(resume_raw):
    """
    항상 최신 이력서 분석 결과를 선택한다.

    우선순위:
    1. effectiveAnalysis: 사용자가 수정했으면 수정본, 아니면 원본
    2. editedAnalysis
    3. originalAnalysis
    4. resume

    반환:
    - selected_analysis: 매칭에 사용할 분석 데이터
    - analysis_meta: 저장/로그/프론트 표시용 메타데이터
    """
    if not isinstance(resume_raw, dict):
        resume_raw = {}

    candidates = [
        ("effectiveAnalysis", resume_raw.get("effectiveAnalysis")),
        ("editedAnalysis", resume_raw.get("editedAnalysis")),
        ("originalAnalysis", resume_raw.get("originalAnalysis")),
        ("resume", resume_raw.get("resume")),
    ]

    selected_source = "none"
    selected_analysis = {}

    for source, analysis in candidates:
        if has_meaningful_value(analysis):
            selected_source = source
            selected_analysis = normalize_resume_analysis_payload(analysis)
            break

    is_analysis_edited = bool(resume_raw.get("isAnalysisEdited", False))
    analysis_version = resume_raw.get("analysisVersion", 1)

    # 사용자에게 보여줄 기준값
    if is_analysis_edited and selected_source in ["effectiveAnalysis", "editedAnalysis"]:
        analysis_source_label = "edited"
    elif selected_source in ["effectiveAnalysis", "originalAnalysis", "resume"]:
        analysis_source_label = "original"
    else:
        analysis_source_label = selected_source

    analysis_meta = {
        "selectedAnalysisField": selected_source,
        "analysisSource": analysis_source_label,
        "resumeAnalysisVersion": analysis_version,
        "isAnalysisEdited": is_analysis_edited,
    }

    return selected_analysis, analysis_meta


def build_match_result(job_doc_id, job_raw, resume_raw, resume_for_score, analysis_meta=None):
    analysis_meta = analysis_meta or {}

    job_posting = job_raw.get("jobPosting", {}) or {}
    requirements = job_posting.get("requirements", {}) or {}

    job_for_score = flatten_job(job_raw)

    result = calculate_full_score(
        job_for_score,
        resume_for_score,
        label=f"job {job_doc_id}"
    )

    resume_embedding_text = get_resume_embedding_text(resume_raw)
    job_embedding_text = get_job_embedding_text(job_raw)

    full_sim, full_score = calculate_full_embedding_similarity(
        resume_embedding_text,
        job_embedding_text
    )

    rule_details = result.get("rule_details", {})
    semantic_details = result.get("semantic_details", {})
    score_details = result.get("score_details", {})
    ncs_details = result.get("ncs_details", {})

    fit_score = round(result.get("fit_score", result.get("final_score", 0)), 2)
    accessibility_score = round(result.get("accessibility_score", 0), 2)
    confidence_score = round(result.get("confidence_score", 0), 2)
    ncs_total = round(result.get("ncs_total", 0), 2)

    company_name = get_company_name(job_raw, job_posting)

    recommend_type = result.get("recommend_type", "보통")
    match_badges = result.get("match_badges", [])
    explanation_summary = build_explanation_summary(
        result=result,
        rule_details=rule_details,
        semantic_details=semantic_details,
        ncs_details=ncs_details,
        fit_score=fit_score,
        accessibility_score=accessibility_score,
        confidence_score=confidence_score,
        recommend_type=recommend_type,
    )

    return {
        "id": job_doc_id,
        "jobId": job_doc_id,

        # 어떤 이력서 분석 버전으로 계산했는지 결과에 남긴다.
        "resumeAnalysisSource": analysis_meta.get("analysisSource", "original"),
        "resumeAnalysisVersion": analysis_meta.get("resumeAnalysisVersion", 1),
        "isAnalysisEdited": analysis_meta.get("isAnalysisEdited", False),
        "selectedAnalysisField": analysis_meta.get("selectedAnalysisField", ""),

        "title": get_job_title(job_raw, job_posting),
        "company": company_name,
        "companyName": company_name,
        "location": shorten_location(get_location(job_raw, job_posting)),
        "career": format_experience(requirements.get("experience", "")),
        "category": get_category(job_raw, job_posting),
        "salary": get_salary(job_raw, job_posting),
        "sourceUrl": get_source_url(job_raw, job_posting),

        "matchRate": round(fit_score),
        "finalScore": fit_score,
        "fitScore": fit_score,
        "accessibilityScore": accessibility_score,
        "confidenceScore": confidence_score,

        "recommendType": recommend_type,
        "matchBadges": match_badges,
        "explanationSummary": explanation_summary,

        "ruleTotal": round(result.get("rule_total", 0), 2),
        "ruleTotalMax": result.get("rule_total_max", 25),
        "semanticTotal": round(result.get("semantic_total", 0), 2),
        "semanticTotalMax": result.get("semantic_total_max", 50),
        "ncsTotal": ncs_total,
        "ncsTotalMax": result.get("ncs_total_max", 25),
        "ncsDetails": ncs_details,
        "scoringMode": result.get("scoring_mode", ""),
        "ruleEvidenceCount": result.get("rule_evidence_count", 0),

        "embeddingSimilarity": round(full_sim, 4),
        "embeddingScore": round(full_score, 2),

        "unmetConditions": result.get("unmet_conditions", []),

        "matchDetail": {
            "skills": {
                "score": round(rule_details.get("skill_score", 0), 2),
                "maxScore": rule_details.get("skill_score_max", 10),
                "rawScore": round(rule_details.get("skill_raw_score", 0), 2),
                "rawMaxScore": rule_details.get("skill_raw_score_max", 30),
                "matchCount": rule_details.get("skill_match_count", 0),
                "totalCount": rule_details.get("skill_total_count", 0),
                "matchedSkills": rule_details.get("matched_skills", []),
                "used": rule_details.get("skill_used", False),
            },
            "education": {
                "score": round(rule_details.get("edu_score", 0), 2),
                "maxScore": rule_details.get("edu_score_max", 2.5),
                "rawScore": round(rule_details.get("edu_raw_score", 0), 2),
                "rawMaxScore": rule_details.get("edu_raw_score_max", 10),
                "jobLevel": rule_details.get("job_edu_level", ""),
                "resumeLevel": rule_details.get("resume_edu_level", ""),
                "used": rule_details.get("edu_used", False),
            },
            "experience": {
                "score": round(rule_details.get("exp_score", 0), 2),
                "maxScore": rule_details.get("exp_score_max", 5),
                "rawScore": round(rule_details.get("exp_raw_score", 0), 2),
                "minExp": rule_details.get("min_exp", 0),
                "resumeExp": rule_details.get("resume_exp", 0),
                "yearScore": round(rule_details.get("exp_year_score", 0), 2),
                "yearMax": rule_details.get("exp_year_max", 10),
                "relevanceScore": round(rule_details.get("exp_relevance_score", 0), 2),
                "relevanceMax": rule_details.get("exp_relevance_max", 10),
                "relevanceSimilarity": round(rule_details.get("exp_relevance_sim", 0), 4),
                "relevanceUsed": rule_details.get("exp_relevance_used", False),
                "conditionUsed": rule_details.get("exp_condition_used", True),
            },
            "certifications": {
                "score": round(rule_details.get("cert_score", 0), 2),
                "maxScore": rule_details.get("cert_score_max", 2.5),
                "rawScore": round(rule_details.get("cert_raw_score", 0), 2),
                "rawMaxScore": rule_details.get("cert_raw_score_max", 10),
                "matchCount": rule_details.get("cert_match_count", 0),
                "totalCount": rule_details.get("cert_total_count", 0),
                "matchedCerts": rule_details.get("matched_certs", []),
                "used": rule_details.get("cert_used", False),
            },
            "qualifications": {
                "score": round(rule_details.get("qual_rule_score", 0), 2),
                "maxScore": rule_details.get("qual_rule_score_max", 5),
                "rawScore": round(rule_details.get("qual_raw_score", 0), 2),
                "rawMaxScore": rule_details.get("qual_raw_score_max", 10),
                "matchedQuals": rule_details.get("matched_quals", []),
                "totalCount": rule_details.get("qual_total_count", 0),
                "used": rule_details.get("qual_used", False),
            },
            "semantic": {
                "fullScore": round(semantic_details.get("full_score", 0), 2),
                "fullMaxScore": semantic_details.get("full_score_max", 25),
                "fullSimilarity": round(semantic_details.get("full_sim", 0), 4),
                "responsibilityScore": round(semantic_details.get("resp_score", 0), 2),
                "responsibilityMaxScore": semantic_details.get("resp_score_max", 15),
                "responsibilitySimilarity": round(semantic_details.get("resp_sim", 0), 4),
                "qualificationScore": round(semantic_details.get("qual_score", 0), 2),
                "qualificationMaxScore": semantic_details.get("qual_score_max", 10),
                "qualificationSimilarity": round(semantic_details.get("qual_sim", 0), 4),
                "beforeAdjustTotal": round(semantic_details.get("semantic_before_adjust", result.get("semantic_total", 0)), 2),
                "adjustRatio": round(semantic_details.get("semantic_adjust_ratio", 1), 4),
                "requiredConditionRatio": round(semantic_details.get("required_condition_ratio", 1), 4),
            },
            "ncs": {
                "score": ncs_total,
                "maxScore": result.get("ncs_total_max", ncs_details.get("ncs_score_max", 25)),
                "used": ncs_details.get("ncs_used", False),
                "category": ncs_details.get("ncs_category", ""),
                "similarity": ncs_details.get("ncs_similarity", 0),
                "matchedDutyCd": ncs_details.get("matched_duty_cd", ""),
                "matchedDutyName": ncs_details.get("matched_duty_name", ""),
                "matchedUnitCd": ncs_details.get("matched_unit_cd", ""),
                "matchedUnitName": ncs_details.get("matched_unit_name", ""),
                "reason": ncs_details.get("reason", ""),
            },
            "score": score_details,
        },
    }


def process_matching_by_resume_id(resume_doc_id, limit=5):
    groups = process_matching_groups_by_resume_id(resume_doc_id, limit)
    return groups["topFitMatches"]


def process_matching_groups_by_resume_id(resume_doc_id, limit=5):
    clear_embedding_cache()
    db, _ = init_firebase("config/firebase_key.json")

    resume_snapshot = db.collection("resumes").document(resume_doc_id).get()

    if not resume_snapshot.exists:
        raise Exception(f"이력서 문서가 없습니다: {resume_doc_id}")

    resume_raw = resume_snapshot.to_dict() or {}

    # 핵심:
    # 항상 effectiveAnalysis를 최우선으로 사용한다.
    # 사용자가 분석 결과를 수정한 경우 effectiveAnalysis에는 수정본이 들어있다.
    # 수정하지 않은 경우 effectiveAnalysis에는 원본 분석 결과가 들어있다.
    resume_analysis, analysis_meta = get_latest_resume_analysis(resume_raw)

    # 기존 flatten_resume / get_resume_embedding_text 함수가 resumes 문서 전체 구조를
    # 기준으로 동작할 수 있으므로, 최신 분석 결과를 resume과 effectiveAnalysis에 모두 넣는다.
    resume_raw_for_matching = {
        **resume_raw,
        "resume": resume_analysis,
        "effectiveAnalysis": resume_analysis,
    }

    resume_for_score = flatten_resume(resume_raw_for_matching)

    match_preferences = resume_raw.get("matchPreferences", {}) or {}

    job_snapshots = db.collection("job_postings").stream()

    results = []
    candidate_jobs = []
    total_job_count = 0
    filtered_job_count = 0

    print(f"[matching] 이력서 문서 ID: {resume_doc_id}")
    print(f"[matching] 사용 분석 필드: {analysis_meta.get('selectedAnalysisField')}")
    print(f"[matching] 분석 출처: {analysis_meta.get('analysisSource')}")
    print(f"[matching] 분석 버전: {analysis_meta.get('resumeAnalysisVersion')}")
    print(f"[matching] 수정 여부: {analysis_meta.get('isAnalysisEdited')}")

    for job_snapshot in job_snapshots:
        job_doc_id = job_snapshot.id
        job_raw = job_snapshot.to_dict() or {}

        if not is_enabled_job_source(job_raw):
            continue

        total_job_count += 1

        # 이력서에 저장된 희망 직무/지역/근무형태 조건에 맞지 않는 공고는 점수계산 전에 제외
        if not is_job_matched_with_preferences(job_raw, match_preferences):
            continue

        filtered_job_count += 1
        candidate_jobs.append((job_doc_id, job_raw))

    candidate_jobs = rank_job_candidates(
        candidate_jobs,
        get_resume_embedding_text(resume_raw_for_matching),
        match_preferences,
    )

    preload_score_embeddings(
        [flatten_job(job_raw) for _, job_raw in candidate_jobs],
        resume_for_score,
    )

    for job_doc_id, job_raw in candidate_jobs:
        final_result = build_match_result(
            job_doc_id=job_doc_id,
            job_raw=job_raw,
            resume_raw=resume_raw_for_matching,
            resume_for_score=resume_for_score,
            analysis_meta=analysis_meta,
        )

        results.append(final_result)

    results.sort(
        key=sort_for_fit,
        reverse=True
    )

    groups = build_matching_groups(results, limit)

    # 확인 및 저장용 메타 정보
    groups["matchPreferences"] = match_preferences
    groups["totalJobCount"] = total_job_count
    groups["filteredJobCount"] = filtered_job_count
    groups["candidateJobCount"] = len(candidate_jobs)

    # 어떤 이력서 분석 결과로 계산했는지 groups에도 남긴다.
    groups["selectedAnalysisField"] = analysis_meta.get("selectedAnalysisField")
    groups["analysisSource"] = analysis_meta.get("analysisSource")
    groups["resumeAnalysisVersion"] = analysis_meta.get("resumeAnalysisVersion")
    groups["isAnalysisEdited"] = analysis_meta.get("isAnalysisEdited")

    print(f"[matching] 전체 공고 수: {total_job_count}")
    print(f"[matching] 조건 필터링 후 공고 수: {filtered_job_count}")
    print(f"[matching] 적용된 조건: {match_preferences}")
    print(f"[matching] AI 정밀 비교 공고 수: {len(candidate_jobs)}")

    return groups

def main():
    if len(sys.argv) < 2:
        print("사용법: py main/main_matching.py <resume_doc_id>")
        return

    resume_doc_id = sys.argv[1]
    groups = process_matching_groups_by_resume_id(resume_doc_id)

    print("\n[매칭 조건]")
    print(groups.get("matchPreferences"))

    print("\n[공고 필터링 결과]")
    print(f"전체 공고 수: {groups.get('totalJobCount')}")
    print(f"조건 통과 공고 수: {groups.get('filteredJobCount')}")

    print("\n[AI 적합순 상위 5개]")
    for item in groups["topFitMatches"]:
        print(item)

    print("\n[지원 가능순 상위 5개]")
    for item in groups["topAccessibleMatches"]:
        print(item)

    print("\n[신뢰도 높은 순 상위 5개]")
    for item in groups["topConfidenceMatches"]:
        print(item)


if __name__ == "__main__":
    main()
