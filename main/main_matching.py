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


def build_match_result(job_doc_id, job_raw, resume_raw, resume_for_score):
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

    return {
        "id": job_doc_id,
        "jobId": job_doc_id,

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

        "ruleTotal": round(result.get("rule_total", 0), 2),
        "semanticTotal": round(result.get("semantic_total", 0), 2),
        "ncsTotal": ncs_total,
        "ncsDetails": ncs_details,

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
                "maxScore": ncs_details.get("ncs_score_max", 25),
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
    db, _ = init_firebase("config/firebase_key.json")

    resume_snapshot = db.collection("resumes").document(resume_doc_id).get()

    if not resume_snapshot.exists:
        raise Exception(f"이력서 문서가 없습니다: {resume_doc_id}")

    resume_raw = resume_snapshot.to_dict()
    resume_for_score = flatten_resume(resume_raw)

    job_snapshots = db.collection("job_postings").stream()

    results = []

    for job_snapshot in job_snapshots:
        job_doc_id = job_snapshot.id
        job_raw = job_snapshot.to_dict()

        final_result = build_match_result(
            job_doc_id=job_doc_id,
            job_raw=job_raw,
            resume_raw=resume_raw,
            resume_for_score=resume_for_score,
        )

        results.append(final_result)

    results.sort(
        key=sort_for_fit,
        reverse=True
    )

    return build_matching_groups(results, limit)


def main():
    if len(sys.argv) < 2:
        print("사용법: py main/main_matching.py <resume_doc_id>")
        return

    resume_doc_id = sys.argv[1]
    groups = process_matching_groups_by_resume_id(resume_doc_id)

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