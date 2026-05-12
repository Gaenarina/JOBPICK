import re
from typing import Any, Dict, List, Tuple

from sentence_transformers import SentenceTransformer, util


MODEL_NAME = "jhgan/ko-sroberta-multitask"
_model = None

RULE_WEIGHT = 50.0
SEMANTIC_WEIGHT = 50.0

RULE_SKILL_WEIGHT = 20.0
RULE_EDU_WEIGHT = 5.0
RULE_EXP_WEIGHT = 10.0
RULE_CERT_WEIGHT = 5.0
RULE_QUAL_WEIGHT = 10.0

FULL_SEMANTIC_WEIGHT = 25.0
RESPONSIBILITY_SEMANTIC_WEIGHT = 15.0
QUALIFICATION_SEMANTIC_WEIGHT = 10.0


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return " ".join(safe_str(v) for v in value if safe_str(v))
    if isinstance(value, dict):
        return " ".join(safe_str(v) for v in value.values() if safe_str(v))
    return str(value).strip()


def clean_text(value: Any) -> str:
    text = safe_str(value)
    text = re.sub(r"[\u200b\xa0]", " ", text)
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"[ㆍ•·]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        if any(sep in value for sep in [",", "\n", "|"]):
            return [x.strip() for x in re.split(r"[,\n|]+", value) if x.strip()]
        return [value]
    return [value]


def unique_preserve_order(items: List[Any]) -> List[str]:
    seen = set()
    result = []

    for item in items:
        text = clean_text(item)

        if not text:
            continue

        key = text.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(text)

    return result


def get_score_ratio(score: float, max_score: float) -> float:
    try:
        score = float(score)
        max_score = float(max_score)
    except Exception:
        return 0.0

    if max_score <= 0:
        return 0.0

    return max(0.0, min(score / max_score, 1.0))


INVALID_SKILL_TOKENS = {
    "", "c", "r", "im", "cs", "c/s", "i/b", "o/b", "ib", "ob",
    "a", "b", "d", "e", "f", "g", "n/a", "없음", "무관"
}

SKILL_ALIASES = {
    "excel": "excel",
    "엑셀": "excel",
    "microsoft excel": "excel",
    "ms excel": "excel",
    "powerpoint": "powerpoint",
    "ppt": "powerpoint",
    "파워포인트": "powerpoint",
    "word": "word",
    "워드": "word",
    "microsoft word": "word",
    "ms word": "word",
    "microsoft office": "microsoft office",
    "ms office": "microsoft office",
    "office": "microsoft office",
    "erp": "erp",
    "sap": "sap",
    "photoshop": "photoshop",
    "포토샵": "photoshop",
    "illustrator": "illustrator",
    "일러스트": "illustrator",
    "figma": "figma",
    "tableau": "tableau",
    "power bi": "power bi",
    "spss": "spss",

    "python": "python",
    "파이썬": "python",
    "java": "java",
    "javascript": "javascript",
    "java script": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "type script": "typescript",
    "ts": "typescript",
    "kotlin": "kotlin",
    "swift": "swift",
    "go": "go",
    "golang": "go",
    "php": "php",
    "ruby": "ruby",
    "c++": "c++",
    "cpp": "c++",
    "c#": "c#",
    "csharp": "c#",
    "sql": "sql",

    "react": "react",
    "react.js": "react",
    "reactjs": "react",
    "next": "next.js",
    "next.js": "next.js",
    "nextjs": "next.js",
    "vue": "vue",
    "vue.js": "vue",
    "angular": "angular",
    "node": "node.js",
    "node.js": "node.js",
    "nodejs": "node.js",
    "express": "express",
    "nestjs": "nestjs",
    "nest.js": "nestjs",
    "spring": "spring",
    "spring boot": "spring boot",
    "django": "django",
    "flask": "flask",

    "mysql": "mysql",
    "mariadb": "mysql",
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "oracle": "oracle",
    "mssql": "mssql",
    "tibero": "tibero",
    "mongodb": "mongodb",
    "redis": "redis",
    "aws": "aws",
    "gcp": "gcp",
    "azure": "azure",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "linux": "linux",
    "window server": "windows server",
    "windows server": "windows server",
    "was": "was",
    "vmware": "vmware",
    "hyper-v": "hyper-v",
    "hyper v": "hyper-v",
    "nutanix": "nutanix",
}


def normalize_skill(skill: Any) -> str:
    value = clean_text(skill).lower()

    if not value:
        return ""

    value = value.replace("．", ".")
    value = re.sub(r"\s+", " ", value).strip()
    value = value.strip(" ,./;:()[]{}<>|\\\"'")

    if value in INVALID_SKILL_TOKENS:
        return ""

    if len(value) == 1 and value not in {"c"}:
        return ""

    return SKILL_ALIASES.get(value, value)


def flatten_skill_items(value: Any) -> List[str]:
    raw_items = []

    if isinstance(value, dict):
        for key in ["required", "preferred", "tools", "languages", "frameworks", "etc"]:
            raw_items.extend(as_list(value.get(key)))
    else:
        raw_items.extend(as_list(value))

    normalized = []

    for item in raw_items:
        text = clean_text(item)

        if not text:
            continue

        pieces = re.split(r"[,/|·ㆍ]+", text)

        if len(pieces) > 1:
            for piece in pieces:
                normalized_skill = normalize_skill(piece)

                if normalized_skill:
                    normalized.append(normalized_skill)
        else:
            normalized_skill = normalize_skill(text)

            if normalized_skill:
                normalized.append(normalized_skill)

    return unique_preserve_order(normalized)


def calculate_skill_score(job_skills: Dict[str, Any], resume_skills: List[str]) -> Tuple[float, int, int, bool, List[str]]:
    required_skills = flatten_skill_items(job_skills.get("required", [])) if isinstance(job_skills, dict) else flatten_skill_items(job_skills)
    resume_skill_set = set(flatten_skill_items(resume_skills))

    if not required_skills:
        return 0.0, 0, 0, False, []

    matched = []

    for required_skill in required_skills:
        if required_skill in resume_skill_set:
            matched.append(required_skill)

    score = (len(matched) / len(required_skills)) * 30

    return score, len(matched), len(required_skills), True, matched


EDU_LEVELS = {
    "무관": 0,
    "학력무관": 0,
    "고졸": 1,
    "고졸이상": 1,
    "초대졸": 2,
    "초대졸이상": 2,
    "전문대졸": 2,
    "대졸": 3,
    "대졸이상": 3,
    "학사": 3,
    "석사": 4,
    "박사": 5,
}


def normalize_education(value: Any) -> str:
    text = clean_text(value)

    if not text:
        return ""

    text_no_space = re.sub(r"\s+", "", text)

    if "학력무관" in text_no_space or text_no_space == "무관":
        return "무관"
    if "고졸" in text_no_space or "고등학교" in text_no_space:
        return "고졸"
    if "초대졸" in text_no_space or "전문대" in text_no_space:
        return "초대졸"
    if "대졸" in text_no_space or "4년제" in text_no_space or "학사" in text_no_space:
        return "대졸"
    if "석사" in text_no_space:
        return "석사"
    if "박사" in text_no_space:
        return "박사"

    return text


def education_level(value: Any) -> int:
    education = normalize_education(value)
    return EDU_LEVELS.get(education, EDU_LEVELS.get(clean_text(value), 0))


def calculate_education_score(job_edu: Any, resume_edu: Any) -> Tuple[float, bool, str, str]:
    job_normalized = normalize_education(job_edu)
    resume_normalized = normalize_education(resume_edu)

    if not job_normalized or job_normalized in ["무관", "학력무관"]:
        return 10.0, True, "무관", resume_normalized or ""

    job_level = education_level(job_normalized)
    resume_level = education_level(resume_normalized)

    score = 10.0 if resume_level >= job_level else 0.0

    return score, True, job_normalized, resume_normalized


def extract_min_years(experience: Any) -> int:
    if isinstance(experience, dict):
        if experience.get("minYears") is not None:
            try:
                return int(float(experience.get("minYears") or 0))
            except Exception:
                pass

        text = clean_text(experience.get("type", ""))
    else:
        text = clean_text(experience)

    if not text or "무관" in text or "신입" in text:
        return 0

    match = re.search(r"(\d+)\s*년\s*이상", text)

    if match:
        return int(match.group(1))

    match = re.search(r"(\d+)\s*년", text)

    if match:
        return int(match.group(1))

    return 0


def calculate_text_similarity(text1: str, text2: str) -> float:
    text1 = clean_text(text1)
    text2 = clean_text(text2)

    if not text1 or not text2:
        return 0.0

    model = get_model()
    emb1 = model.encode(text1, convert_to_tensor=True)
    emb2 = model.encode(text2, convert_to_tensor=True)
    similarity = util.cos_sim(emb1, emb2).item()

    return max(0.0, min(1.0, float(similarity)))


def build_experience_relevance_text(job: Dict[str, Any]) -> str:
    parts = []
    parts.extend(as_list(job.get("responsibilities", [])))

    qualifications = job.get("qualifications", {}) or {}

    if isinstance(qualifications, dict):
        parts.extend(as_list(qualifications.get("required", [])))
        parts.extend(as_list(qualifications.get("preferred", [])))

    skills = job.get("skills", {}) or {}

    if isinstance(skills, dict):
        parts.extend(flatten_skill_items(skills.get("required", [])))
        parts.extend(flatten_skill_items(skills.get("preferred", [])))

    return clean_text(" ".join(unique_preserve_order(parts)))


def calculate_experience_score(job: Dict[str, Any], resume: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    min_years = extract_min_years(job.get("experience", {}))
    resume_exp = float(resume.get("experienceYears", 0) or 0)

    year_max = 10.0
    relevance_max = 10.0

    if min_years <= 0:
        year_score = 10.0
    else:
        year_score = min(resume_exp / min_years, 1.0) * year_max

    job_relevance_text = build_experience_relevance_text(job)
    resume_experience_text = clean_text(" ".join(as_list(resume.get("projects", []))))

    if job_relevance_text and resume_experience_text:
        similarity = calculate_text_similarity(job_relevance_text, resume_experience_text)
        relevance_score = similarity * relevance_max
        relevance_used = True
    else:
        similarity = 0.0
        relevance_score = 0.0
        relevance_used = False

    if relevance_used:
        total = year_score + relevance_score
        max_score = year_max + relevance_max
    else:
        total = year_score
        max_score = year_max

    return total, {
        "min_exp": min_years,
        "resume_exp": resume_exp,
        "exp_score": total,
        "exp_score_max": max_score,
        "exp_year_score": year_score,
        "exp_year_max": year_max,
        "exp_relevance_score": relevance_score,
        "exp_relevance_max": relevance_max,
        "exp_relevance_sim": similarity,
        "exp_relevance_used": relevance_used,
    }


def normalize_cert_name(value: Any) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"\s+", "", text)
    return text


def calculate_certification_score(job_certs: List[Any], resume_certs: List[Any]) -> Tuple[float, int, int, bool, List[str]]:
    required = [normalize_cert_name(item) for item in as_list(job_certs)]
    required = [item for item in required if item]

    owned = [normalize_cert_name(item) for item in as_list(resume_certs)]
    owned = [item for item in owned if item]

    if not required:
        return 0.0, 0, 0, False, []

    matched = []

    for cert in required:
        if any(cert in owned_cert or owned_cert in cert for owned_cert in owned):
            matched.append(cert)

    score = (len(matched) / len(required)) * 10

    return score, len(matched), len(required), True, matched


QUALIFICATION_NOISE_KEYWORDS = [
    "담당업무", "업무", "상담문의", "고객문의", "청약", "배정", "정리",
    "어드민", "챗팅상담", "채팅상담", "처리", "운영관리", "유지보수",
    "근무환경", "근무기간", "전형", "접수", "급여", "근무시간", "근무장소"
]


def is_valid_required_qualification(text: Any) -> bool:
    value = clean_text(text)

    if not value:
        return False
    if len(value) <= 2:
        return False
    if value in {"담당업무 및", "자격요건 및", "[자격요건 및 ]", "근무환경"}:
        return False
    if re.fullmatch(r"[0-9○O]+명", value):
        return False
    if any(keyword in value for keyword in QUALIFICATION_NOISE_KEYWORDS):
        return False

    return True


def calculate_qualification_rule_score(required_quals: List[Any], resume: Dict[str, Any]) -> Tuple[float, List[str], int, bool]:
    required = [clean_text(item) for item in as_list(required_quals)]
    required = [item for item in required if is_valid_required_qualification(item)]

    if not required:
        return 0.0, [], 0, False

    resume_text = clean_text(" ".join([
        safe_str(resume.get("skills", [])),
        safe_str(resume.get("certifications", [])),
        safe_str(resume.get("projects", [])),
        safe_str(resume.get("education", "")),
    ])).lower()

    matched = []

    for qualification in required:
        key = clean_text(qualification).lower()

        if key and key in resume_text:
            matched.append(qualification)

    score = (len(matched) / len(required)) * 10

    return score, matched, len(required), True


def calculate_semantic_score(resume_text: str, job_text: str, max_score: float) -> Tuple[float, float]:
    similarity = calculate_text_similarity(resume_text, job_text)
    return similarity, similarity * max_score


def flatten_resume(firebase_resume_doc: Dict[str, Any]) -> Dict[str, Any]:
    resume_root = firebase_resume_doc.get("resume", firebase_resume_doc) or {}
    data = resume_root.get("resumeData", resume_root) or {}

    skills_map = data.get("skills", {}) or {}
    skills = []

    if isinstance(skills_map, dict):
        skills.extend(as_list(skills_map.get("tools", [])))
        skills.extend(as_list(skills_map.get("languages", [])))
        skills.extend(as_list(skills_map.get("frameworks", [])))
        skills.extend(as_list(skills_map.get("etc", [])))
    else:
        skills.extend(as_list(skills_map))

    skills = unique_preserve_order(skills)

    education_list = data.get("education", []) or []
    education = ""

    if education_list:
        first_education = education_list[0]

        if isinstance(first_education, dict):
            education = first_education.get("degree", "") or first_education.get("status", "") or ""
        else:
            education = clean_text(first_education)

    exp_summary = data.get("experienceSummary", {}) or {}
    experience_years = float(exp_summary.get("yearsFloat", 0) or exp_summary.get("years", 0) or 0)

    certifications = []

    for cert in as_list(data.get("certifications", [])):
        if isinstance(cert, dict):
            certifications.append(cert.get("name", ""))
        else:
            certifications.append(cert)

    certifications = unique_preserve_order(certifications)

    projects = []

    for exp in as_list(data.get("experience", [])):
        if isinstance(exp, dict):
            parts = [
                exp.get("organization", ""),
                exp.get("position", ""),
                " ".join(as_list(exp.get("responsibilities", []))),
            ]
            text = " / ".join([clean_text(part) for part in parts if clean_text(part)])

            if text:
                projects.append(text)
        else:
            projects.append(clean_text(exp))

    for project in as_list(data.get("projects", [])):
        if isinstance(project, dict):
            text = " / ".join([clean_text(value) for value in project.values() if clean_text(value)])

            if text:
                projects.append(text)
        else:
            projects.append(clean_text(project))

    intro = clean_text(data.get("selfIntroduction", ""))

    if intro:
        projects.append(intro)

    return {
        "skills": skills,
        "education": normalize_education(education),
        "experienceYears": experience_years,
        "certifications": certifications,
        "projects": unique_preserve_order(projects),
    }


def flatten_job(firebase_job_doc: Dict[str, Any]) -> Dict[str, Any]:
    job = firebase_job_doc.get("jobPosting", firebase_job_doc) or {}
    requirements = job.get("requirements", {}) or {}

    required_skills = flatten_skill_items(requirements.get("requiredSkills", []))
    preferred_skills = flatten_skill_items(requirements.get("preferredSkills", []))

    education = ""
    education_obj = requirements.get("education", {}) or {}

    if isinstance(education_obj, dict):
        education = education_obj.get("minimum", "")
    else:
        education = education_obj

    experience = requirements.get("experience", {}) or {}
    certifications = requirements.get("certifications", []) or []

    required_quals = as_list(requirements.get("requiredQualifications", []))
    preferred_quals = as_list(requirements.get("preferredQualifications", []))

    return {
        "skills": {
            "required": required_skills,
            "preferred": preferred_skills,
        },
        "responsibilities": unique_preserve_order(job.get("responsibilities", [])),
        "qualifications": {
            "required": unique_preserve_order(required_quals),
            "preferred": unique_preserve_order(preferred_quals),
        },
        "education": normalize_education(education),
        "experience": {
            "minYears": extract_min_years(experience),
            "raw": experience,
        },
        "certifications": unique_preserve_order(certifications),
    }


def get_resume_embedding_text(firebase_resume_doc: Dict[str, Any]) -> str:
    resume_root = firebase_resume_doc.get("resume", firebase_resume_doc) or {}
    data = resume_root.get("resumeData", resume_root) or {}
    embedding = data.get("embeddingText", {}) or {}

    if embedding.get("fullForEmbedding"):
        return clean_text(embedding.get("fullForEmbedding"))

    flat = flatten_resume(firebase_resume_doc)

    return clean_text(" / ".join([
        safe_str(flat.get("education", "")),
        safe_str(flat.get("skills", [])),
        safe_str(flat.get("certifications", [])),
        safe_str(flat.get("projects", [])),
    ]))


def get_job_embedding_text(firebase_job_doc: Dict[str, Any]) -> str:
    job = firebase_job_doc.get("jobPosting", firebase_job_doc) or {}
    embedding = job.get("embeddingText", {}) or {}

    if embedding.get("fullForEmbedding"):
        return clean_text(embedding.get("fullForEmbedding"))

    flat = flatten_job(firebase_job_doc)

    return clean_text(" / ".join([
        safe_str(flat.get("education", "")),
        safe_str(flat.get("skills", {})),
        safe_str(flat.get("responsibilities", [])),
        safe_str(flat.get("qualifications", {})),
        safe_str(flat.get("certifications", [])),
    ]))


def calculate_full_embedding_similarity(resume_embedding_text: str, job_embedding_text: str) -> Tuple[float, float]:
    similarity = calculate_text_similarity(resume_embedding_text, job_embedding_text)
    return similarity, similarity * FULL_SEMANTIC_WEIGHT


def build_resume_full_text(resume: Dict[str, Any]) -> str:
    return clean_text(" / ".join([
        safe_str(resume.get("education", "")),
        safe_str(resume.get("skills", [])),
        safe_str(resume.get("certifications", [])),
        safe_str(resume.get("projects", [])),
    ]))


def build_job_full_text(job: Dict[str, Any]) -> str:
    return clean_text(" / ".join([
        safe_str(job.get("education", "")),
        safe_str(job.get("experience", {})),
        safe_str(job.get("skills", {})),
        safe_str(job.get("responsibilities", [])),
        safe_str(job.get("qualifications", {})),
        safe_str(job.get("certifications", [])),
    ]))


def calculate_accessibility_score(
    skill_used: bool,
    skill_match_count: int,
    skill_total_count: int,
    edu_score_raw: float,
    exp_detail: Dict[str, Any],
    cert_used: bool,
    cert_match_count: int,
    cert_total_count: int,
    qual_used: bool,
    qual_rule_score_raw: float,
) -> float:
    score = 0.0

    min_exp = float(exp_detail.get("min_exp", 0) or 0)
    resume_exp = float(exp_detail.get("resume_exp", 0) or 0)

    if min_exp <= 0:
        score += 30
    elif resume_exp >= min_exp:
        score += 30
    else:
        score += 10

    if edu_score_raw > 0:
        score += 20

    if not skill_used:
        score += 20
    elif skill_total_count > 0:
        score += (skill_match_count / skill_total_count) * 20

    if not cert_used:
        score += 15
    elif cert_total_count > 0:
        score += (cert_match_count / cert_total_count) * 15

    if not qual_used:
        score += 15
    else:
        score += get_score_ratio(qual_rule_score_raw, 10) * 15

    return round(min(score, 100.0), 2)


def calculate_confidence_score(job: Dict[str, Any]) -> float:
    score = 0.0

    skills = job.get("skills", {}) or {}
    required_skills = flatten_skill_items(skills.get("required", [])) if isinstance(skills, dict) else []

    responsibilities = as_list(job.get("responsibilities", []))

    qualifications = job.get("qualifications", {}) or {}
    required_quals = as_list(qualifications.get("required", [])) if isinstance(qualifications, dict) else []

    certifications = as_list(job.get("certifications", []))
    job_full_text = build_job_full_text(job)

    if required_skills:
        score += 25

    if responsibilities:
        score += 25

    if required_quals:
        score += 20

    if certifications:
        score += 5

    if len(job_full_text) >= 120:
        score += 20
    elif len(job_full_text) >= 60:
        score += 10

    if job.get("education") or job.get("experience"):
        score += 5

    return round(min(score, 100.0), 2)


def get_match_badges(fit_score: float, accessibility_score: float, confidence_score: float) -> List[str]:
    badges = []

    if fit_score >= 70 and confidence_score >= 45:
        badges.append("AI 적합")

    if accessibility_score >= 75:
        badges.append("지원 가능")

    if confidence_score < 40:
        badges.append("정보 부족")

    if fit_score < 40 and accessibility_score < 60:
        badges.append("부적합")

    if not badges:
        badges.append("보통")

    return badges


def get_recommend_type(fit_score: float, accessibility_score: float, confidence_score: float) -> str:
    badges = get_match_badges(fit_score, accessibility_score, confidence_score)

    if "AI 적합" in badges:
        return "AI 적합"

    if "지원 가능" in badges:
        return "지원 가능"

    if "정보 부족" in badges:
        return "정보 부족"

    if "부적합" in badges:
        return "부적합"

    return "보통"


def calculate_full_score(job: Dict[str, Any], resume: Dict[str, Any], label: str = "매칭") -> Dict[str, Any]:
    print(f"\n=== {label} 계산 과정 ===")

    skill_score_raw, skill_match_count, skill_total_count, skill_used, matched_skills = calculate_skill_score(
        job.get("skills", {}), resume.get("skills", [])
    )

    edu_score_raw, edu_used, job_edu_level, resume_edu_level = calculate_education_score(
        job.get("education", ""), resume.get("education", "")
    )

    exp_score_raw, exp_detail = calculate_experience_score(job, resume)
    exp_used = True

    cert_score_raw, cert_match_count, cert_total_count, cert_used, matched_certs = calculate_certification_score(
        job.get("certifications", []), resume.get("certifications", [])
    )

    required_quals = (job.get("qualifications", {}) or {}).get("required", [])
    qual_rule_score_raw, matched_quals, qual_total_count, qual_used = calculate_qualification_rule_score(
        required_quals, resume
    )

    skill_score = get_score_ratio(skill_score_raw, 30) * RULE_SKILL_WEIGHT if skill_used else 0.0
    edu_score = get_score_ratio(edu_score_raw, 10) * RULE_EDU_WEIGHT if edu_used else 0.0
    exp_score = get_score_ratio(exp_detail.get("exp_year_score", 0), 10) * RULE_EXP_WEIGHT if exp_used else 0.0
    cert_score = get_score_ratio(cert_score_raw, 10) * RULE_CERT_WEIGHT if cert_used else 0.0
    qual_rule_score = get_score_ratio(qual_rule_score_raw, 10) * RULE_QUAL_WEIGHT if qual_used else 0.0

    rule_total = skill_score + edu_score + exp_score + cert_score + qual_rule_score

    resume_full_text = build_resume_full_text(resume)
    job_full_text = build_job_full_text(job)

    resume_exp_text = clean_text(" ".join(as_list(resume.get("projects", []))))
    job_resp_text = clean_text(" ".join(as_list(job.get("responsibilities", []))))
    job_qual_text = clean_text(" ".join(as_list((job.get("qualifications", {}) or {}).get("required", []))))

    full_sim, full_score = calculate_semantic_score(
        resume_full_text,
        job_full_text,
        FULL_SEMANTIC_WEIGHT
    ) if resume_full_text and job_full_text else (0.0, 0.0)

    resp_sim, resp_score = calculate_semantic_score(
        resume_exp_text,
        job_resp_text,
        RESPONSIBILITY_SEMANTIC_WEIGHT
    ) if resume_exp_text and job_resp_text else (0.0, 0.0)

    qual_sim, qual_score = calculate_semantic_score(
        resume_exp_text,
        job_qual_text,
        QUALIFICATION_SEMANTIC_WEIGHT
    ) if resume_exp_text and job_qual_text else (0.0, 0.0)

    semantic_total = full_score + resp_score + qual_score
    fit_score = round(min(rule_total + semantic_total, 100.0), 2)

    accessibility_score = calculate_accessibility_score(
        skill_used=skill_used,
        skill_match_count=skill_match_count,
        skill_total_count=skill_total_count,
        edu_score_raw=edu_score_raw,
        exp_detail=exp_detail,
        cert_used=cert_used,
        cert_match_count=cert_match_count,
        cert_total_count=cert_total_count,
        qual_used=qual_used,
        qual_rule_score_raw=qual_rule_score_raw,
    )

    confidence_score = calculate_confidence_score(job)
    match_badges = get_match_badges(fit_score, accessibility_score, confidence_score)
    recommend_type = get_recommend_type(fit_score, accessibility_score, confidence_score)

    unmet_conditions = []

    if skill_used and skill_match_count < skill_total_count:
        unmet_conditions.append("필수 기술 미충족")
    if edu_used and edu_score_raw < 10:
        unmet_conditions.append("학력 조건 미충족")
    if exp_used and exp_detail.get("resume_exp", 0) < exp_detail.get("min_exp", 0):
        unmet_conditions.append("경력 연수 미충족")
    if cert_used and cert_match_count < cert_total_count:
        unmet_conditions.append("필수 자격증 미충족")
    if qual_used and qual_rule_score_raw < 10:
        unmet_conditions.append("필수 자격요건 미충족")

    print("[룰 기반]")
    print(f"- 기술 스택 일치도: {skill_score:.2f}/{RULE_SKILL_WEIGHT:.0f} (일치 {skill_match_count}/{skill_total_count}, 매칭: {matched_skills})")
    print(f"- 학력 조건: {edu_score:.2f}/{RULE_EDU_WEIGHT:.0f} (공고: {job_edu_level or '무관'}, 이력서: {resume_edu_level or '미확인'})")
    print(f"- 경력 조건: {exp_score:.2f}/{RULE_EXP_WEIGHT:.0f} (지원자 {exp_detail.get('resume_exp', 0)}년 / 요구 {exp_detail.get('min_exp', 0)}년)")
    print(f"- 자격증: {cert_score:.2f}/{RULE_CERT_WEIGHT:.0f} (일치 {cert_match_count}/{cert_total_count})")
    print(f"- 필수 자격요건: {qual_rule_score:.2f}/{RULE_QUAL_WEIGHT:.0f} (일치 {len(matched_quals)}/{qual_total_count})")
    print(f"룰 기반 점수 합계: {rule_total:.2f}/{RULE_WEIGHT:.0f}")

    print("[의미 기반]")
    print(f"- 이력서 전체와 공고 전체 유사도: {full_score:.2f}/{FULL_SEMANTIC_WEIGHT:.0f} (유사도 {full_sim:.4f})")
    print(f"- 자기소개서·경험과 담당업무 유사도: {resp_score:.2f}/{RESPONSIBILITY_SEMANTIC_WEIGHT:.0f} (유사도 {resp_sim:.4f})")
    print(f"- 자기소개서·경험과 자격요건 유사도: {qual_score:.2f}/{QUALIFICATION_SEMANTIC_WEIGHT:.0f} (유사도 {qual_sim:.4f})")
    print(f"의미 기반 점수 합계: {semantic_total:.2f}/{SEMANTIC_WEIGHT:.0f}")

    print("[최종 점수]")
    print(f"- 적합도 점수: {fit_score:.2f}/100")
    print(f"- 지원 가능성 점수: {accessibility_score:.2f}/100")
    print(f"- 매칭 신뢰도 점수: {confidence_score:.2f}/100")
    print(f"- 추천 유형: {recommend_type}")
    print(f"- 배지: {match_badges}")

    print("[미충족 조건]")

    if unmet_conditions:
        for condition in unmet_conditions:
            print(f"- {condition}")
    else:
        print("- 없음")

    return {
        "final_score": fit_score,
        "fit_score": fit_score,
        "accessibility_score": accessibility_score,
        "confidence_score": confidence_score,
        "recommend_type": recommend_type,
        "match_badges": match_badges,
        "rule_total": round(rule_total, 2),
        "semantic_total": round(semantic_total, 2),
        "unmet_conditions": unmet_conditions,
        "rule_details": {
            "skill_score": round(skill_score, 2),
            "skill_score_max": RULE_SKILL_WEIGHT,
            "skill_raw_score": skill_score_raw,
            "skill_raw_score_max": 30,
            "skill_match_count": skill_match_count,
            "skill_total_count": skill_total_count,
            "skill_used": skill_used,
            "matched_skills": matched_skills,

            "edu_score": round(edu_score, 2),
            "edu_score_max": RULE_EDU_WEIGHT,
            "edu_raw_score": edu_score_raw,
            "edu_raw_score_max": 10,
            "job_edu_level": job_edu_level,
            "resume_edu_level": resume_edu_level,
            "edu_used": edu_used,

            "exp_score": round(exp_score, 2),
            "exp_score_max": RULE_EXP_WEIGHT,
            "exp_raw_score": exp_score_raw,
            "min_exp": exp_detail.get("min_exp", 0),
            "resume_exp": exp_detail.get("resume_exp", 0),
            "exp_used": exp_used,
            **exp_detail,

            "cert_score": round(cert_score, 2),
            "cert_score_max": RULE_CERT_WEIGHT,
            "cert_raw_score": cert_score_raw,
            "cert_raw_score_max": 10,
            "cert_match_count": cert_match_count,
            "cert_total_count": cert_total_count,
            "cert_used": cert_used,
            "matched_certs": matched_certs,

            "qual_rule_score": round(qual_rule_score, 2),
            "qual_rule_score_max": RULE_QUAL_WEIGHT,
            "qual_raw_score": qual_rule_score_raw,
            "qual_raw_score_max": 10,
            "matched_quals": matched_quals,
            "qual_total_count": qual_total_count,
            "qual_used": qual_used,
        },
        "semantic_details": {
            "full_sim": full_sim,
            "full_score": round(full_score, 2),
            "full_score_max": FULL_SEMANTIC_WEIGHT,

            "resp_sim": resp_sim,
            "resp_score": round(resp_score, 2),
            "resp_score_max": RESPONSIBILITY_SEMANTIC_WEIGHT,

            "qual_sim": qual_sim,
            "qual_score": round(qual_score, 2),
            "qual_score_max": QUALIFICATION_SEMANTIC_WEIGHT,

            "semantic_total_max": SEMANTIC_WEIGHT,
        },
        "score_details": {
            "fit_score": fit_score,
            "fit_score_max": 100,
            "accessibility_score": accessibility_score,
            "accessibility_score_max": 100,
            "confidence_score": confidence_score,
            "confidence_score_max": 100,
            "recommend_type": recommend_type,
            "match_badges": match_badges,
        },
    }