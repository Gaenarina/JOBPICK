import re
import time
from collections import OrderedDict
from typing import Any, Dict, List, Tuple

from sentence_transformers import SentenceTransformer, util

from matching.keyword_dictionary import (
    standardize_text,
    remove_stopwords,
    extract_dictionary_features,
    get_category_overlap,
)
from matching.ncs_matcher import calculate_ncs_score
from matching.vector_store import get_vector


MODEL_NAME = "jhgan/ko-sroberta-multitask"
_model = None
_embedding_cache = OrderedDict()
EMBEDDING_CACHE_LIMIT = 1024

NO_NCS_RULE_WEIGHT = 30.0
NO_NCS_SEMANTIC_WEIGHT = 70.0
NCS_WITH_RULE_RULE_WEIGHT = 15.0
NCS_WITH_RULE_SEMANTIC_WEIGHT = 70.0
NCS_WITH_RULE_NCS_WEIGHT = 15.0
NCS_NO_RULE_SEMANTIC_WEIGHT = 70.0
NCS_NO_RULE_NCS_WEIGHT = 30.0

RULE_SKILL_RATIO = 0.40
RULE_EDU_RATIO = 0.10
RULE_EXP_RATIO = 0.20
RULE_CERT_RATIO = 0.10
RULE_QUAL_RATIO = 0.20

FULL_SEMANTIC_RATIO = 0.50
RESPONSIBILITY_SEMANTIC_RATIO = 0.30
QUALIFICATION_SEMANTIC_RATIO = 0.20

FULL_SEMANTIC_WEIGHT = NO_NCS_SEMANTIC_WEIGHT * FULL_SEMANTIC_RATIO
RESPONSIBILITY_SEMANTIC_WEIGHT = NO_NCS_SEMANTIC_WEIGHT * RESPONSIBILITY_SEMANTIC_RATIO
QUALIFICATION_SEMANTIC_WEIGHT = NO_NCS_SEMANTIC_WEIGHT * QUALIFICATION_SEMANTIC_RATIO


def get_model():
    global _model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def get_text_embedding(text: str):
    normalized = prepare_semantic_text(text)
    cached = _embedding_cache.get(normalized)
    if cached is not None:
        _embedding_cache.move_to_end(normalized)
        return cached

    stored = get_vector(normalized)
    if stored is not None:
        import torch
        embedding = torch.from_numpy(stored.copy())
    else:
        embedding = get_model().encode(normalized, convert_to_tensor=True)
    _embedding_cache[normalized] = embedding
    while len(_embedding_cache) > EMBEDDING_CACHE_LIMIT:
        _embedding_cache.popitem(last=False)
    return embedding


def clear_embedding_cache():
    _embedding_cache.clear()


# ============================================================
# calculate_full_score 성능 측정용 누적 통계
# ============================================================

_FULL_SCORE_PERF_STATS = {}


def reset_full_score_perf_stats():
    """calculate_full_score() 내부 단계별 누적 시간을 초기화한다."""
    _FULL_SCORE_PERF_STATS.clear()
    _FULL_SCORE_PERF_STATS["calls"] = 0


def get_full_score_perf_stats():
    """calculate_full_score() 내부 단계별 누적 시간의 복사본을 반환한다."""
    return dict(_FULL_SCORE_PERF_STATS)


def _record_full_score_perf(key: str, elapsed: float):
    _FULL_SCORE_PERF_STATS[key] = (
        float(_FULL_SCORE_PERF_STATS.get(key, 0.0))
        + float(elapsed)
    )


def get_score_semantic_texts(
    job: Dict[str, Any],
    resume: Dict[str, Any],
):
    resume_full = prepare_semantic_text(
        " / ".join([
            safe_str(
                resume.get(
                    "education",
                    "",
                )
            ),
            safe_str(
                resume.get(
                    "majors",
                    [],
                )
            ),
            safe_str(
                resume.get(
                    "skills",
                    [],
                )
            ),
            safe_str(
                resume.get(
                    "certifications",
                    [],
                )
            ),
            safe_str(
                resume.get(
                    "projects",
                    [],
                )
            ),
        ])
    )

    qualifications = (
        job.get(
            "qualifications",
            {},
        )
        or {}
    )

    # ------------------------------------------------------
    # 의미 유사도에서는
    # 실제 이력서와 비교 가능한 자격요건만 사용
    # ------------------------------------------------------

    required_qualifications = [
        qualification
        for qualification
        in as_qualification_list(
            qualifications.get(
                "required",
                [],
            )
        )
        if is_scorable_required_qualification(
            qualification
        )
    ]

    preferred_qualifications = [
        qualification
        for qualification
        in as_qualification_list(
            qualifications.get(
                "preferred",
                [],
            )
        )
        if is_scorable_required_qualification(
            qualification
        )
    ]

    semantic_qualifications = (
        unique_preserve_order(
            [
                *required_qualifications,
                *preferred_qualifications,
            ]
        )
    )

    job_full = prepare_semantic_text(
        " / ".join([
            safe_str(
                job.get(
                    "category",
                    "",
                )
            ),
            safe_str(
                job.get(
                    "education",
                    "",
                )
            ),
            safe_str(
                job.get(
                    "experience",
                    {},
                )
            ),
            safe_str(
                job.get(
                    "skills",
                    {},
                )
            ),
            safe_str(
                job.get(
                    "responsibilities",
                    [],
                )
            ),
            safe_str(
                semantic_qualifications
            ),
            safe_str(
                job.get(
                    "certifications",
                    [],
                )
            ),
        ])
    )

    resume_experience = (
        prepare_semantic_text(
            " ".join(
                as_list(
                    resume.get(
                        "projects",
                        [],
                    )
                )
            )
        )
    )

    job_responsibilities = (
        prepare_semantic_text(
            " ".join(
                as_list(
                    job.get(
                        "responsibilities",
                        [],
                    )
                )
            )
        )
    )

    # 자격요건 전용 의미 점수에는
    # 필수조건 중 실제 비교 가능한 조건만 사용
    job_qualifications = (
        prepare_semantic_text(
            " ".join(
                required_qualifications
            )
        )
    )

    return (
        resume_full,
        job_full,
        resume_experience,
        job_responsibilities,
        job_qualifications,
    )


def get_similarity_cache_key(text: str) -> str:
    """
    기존 calculate_text_similarity()가 실제 임베딩 조회에 사용하는 최종 캐시 키를 만든다.

    calculate_text_similarity()에서 prepare_semantic_text() 1회,
    get_text_embedding() 내부에서 prepare_semantic_text() 1회가 더 적용되는
    기존 동작을 그대로 재현한다.
    """
    first = prepare_semantic_text(text)

    if not first:
        return ""

    return prepare_semantic_text(first)


def preload_score_embeddings(
    jobs: List[Dict[str, Any]],
    resume: Dict[str, Any],
    batch_size: int = 32,
    extra_similarity_texts: List[str] | None = None,
):
    """
    기존 점수 계산 경로는 그대로 유지하고,
    실제 similarity 계산에서 쓰일 최종 임베딩만 미리 batch encode한다.

    따라서 기존 점수 산정 결과를 유지하면서
    공고별 개별 SBERT encode를 줄인다.
    """
    texts = []
    seen = set()

    def collect_similarity_text(text):
        cache_key = get_similarity_cache_key(text)

        if not cache_key:
            return

        if cache_key in seen or cache_key in _embedding_cache:
            return

        if get_vector(cache_key) is not None:
            return

        seen.add(cache_key)
        texts.append(cache_key)

    for job in jobs:
        for text in get_score_semantic_texts(job, resume):
            collect_similarity_text(text)

    for text in extra_similarity_texts or []:
        collect_similarity_text(text)

    if not texts:
        return

    embeddings = get_model().encode(
        texts,
        convert_to_tensor=True,
        batch_size=batch_size,
        show_progress_bar=False,
    )

    for text, embedding in zip(texts, embeddings):
        _embedding_cache[text] = embedding

    while len(_embedding_cache) > EMBEDDING_CACHE_LIMIT:
        _embedding_cache.popitem(last=False)


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


def prepare_semantic_text(value: Any) -> str:
    text = clean_text(value)

    if not text:
        return ""

    return clean_text(standardize_text(text))


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



def as_qualification_list(value: Any) -> List[str]:
    """
    자격요건 전용 파서.

    일반 as_list()는 쉼표(,)까지 분리하지만,
    공공기관 API의 자격요건 문장에는 쉼표가 자주 포함되므로
    쉼표로 조건을 잘게 쪼개지 않는다.

    - list/tuple/set: 각 항목 유지
    - str: 줄바꿈 또는 | 기준으로만 분리
    - 앞쪽의 목록기호/번호는 제거
    """
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        result = []
        for item in value:
            result.extend(as_qualification_list(item))
        return list(dict.fromkeys(result))

    if isinstance(value, dict):
        return as_qualification_list(
            value.get("name")
            or value.get("text")
            or value.get("value")
            or list(value.values())
        )

    raw = str(value).strip()
    if not raw:
        return []

    parts = re.split(r"[\r\n|]+", raw)
    result = []

    for part in parts:
        cleaned = clean_text(part)

        # "- ", "O ", "○ ", "① ", "1. " 같은 목록기호 제거
        cleaned = re.sub(
            r"^\s*(?:[-–—•·ㆍ※○O]+|\(?\d+(?:의\d+)?\)?[.)]?|[①-⑳])\s*",
            "",
            cleaned,
        ).strip()

        if cleaned:
            result.append(cleaned)

    return list(dict.fromkeys(result))


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
    "", "r", "im", "cs", "c/s", "i/b", "o/b", "ib", "ob",
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
    "프레젠테이션": "powerpoint",
    "프리젠테이션": "powerpoint",
    "word": "word",
    "워드": "word",
    "microsoft word": "word",
    "ms word": "word",
    "microsoft office": "microsoft office",
    "ms office": "microsoft office",
    "office": "microsoft office",
    "오피스": "microsoft office",
    "오피스프로그램": "microsoft office",
    "oa": "oa",
    "erp": "erp",
    "sap": "sap",
    "photoshop": "photoshop",
    "포토샵": "photoshop",
    "adobe 포토샵": "photoshop",
    "illustrator": "illustrator",
    "일러스트": "illustrator",
    "일러스트레이터": "illustrator",
    "figma": "figma",
    "피그마": "figma",
    "blender": "blender",
    "adobe xd": "adobe xd",
    "xd": "adobe xd",
    "tableau": "tableau",
    "power bi": "power bi",
    "spss": "spss",

    "python": "python",
    "파이썬": "python",
    "java": "java",
    "javascript": "javascript",
    "java script": "javascript",
    "js": "javascript",
    "자바스크립트": "javascript",
    "typescript": "typescript",
    "type script": "typescript",
    "ts": "typescript",
    "kotlin": "kotlin",
    "swift": "swift",
    "go": "go",
    "golang": "go",
    "php": "php",
    "ruby": "ruby",
    "c": "c",
    "c언어": "c",
    "c++": "c++",
    "cpp": "c++",
    "c#": "c#",
    "csharp": "c#",
    "sql": "sql",

    "react": "react",
    "react.js": "react",
    "reactjs": "react",
    "리액트": "react",
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
    "스프링": "spring",
    "스프링부트": "spring boot",
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
    "firebase": "firebase",
    "파이어베이스": "firebase",
    "aws": "aws",
    "gcp": "gcp",
    "azure": "azure",
    "docker": "docker",
    "도커": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "linux": "linux",
    "리눅스": "linux",
    "unix": "unix",
    "window server": "windows server",
    "windows server": "windows server",
    "windows 서버": "windows server",
    "윈도우 서버": "windows server",
    "server": "server",
    "서버": "server",
    "was": "was",
    "vmware": "vmware",
    "hyper-v": "hyper-v",
    "hyper v": "hyper-v",
    "nutanix": "nutanix",

    "tensorflow": "tensorflow",
    "텐서플로우": "tensorflow",
    "pytorch": "pytorch",
    "파이토치": "pytorch",
    "machine learning": "machine learning",
    "머신러닝": "machine learning",
    "deep learning": "deep learning",
    "딥러닝": "deep learning",
    "ai": "ai",
    "인공지능": "ai",
    "llm": "llm",
    "nlp": "nlp",
    "자연어처리": "nlp",
    "챗봇": "chatbot",
    "ai 챗봇": "chatbot",

    "hardware": "hardware",
    "hw": "hardware",
    "h/w": "hardware",
    "하드웨어": "hardware",
    "pc 하드웨어": "hardware",
    "software": "software",
    "sw": "software",
    "s/w": "software",
    "소프트웨어": "software",
    "센서": "sensor",
    "키오스크": "kiosk",
    "빔프로젝터": "projector",
    "전기": "electrical",
    "전자": "electrical",
    "통신": "telecommunication",

    "운전": "driving",
    "운전 가능": "driving",
    "운전가능": "driving",
    "차량소지": "driving",
    "지게차": "forklift",
    "지게차 운전": "forklift",
    "제과제빵보조": "bakery",
    "제과제빵": "bakery",
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


def get_dictionary_skill_tokens(text: Any) -> List[str]:
    features = extract_dictionary_features(clean_text(text))
    return unique_preserve_order(features.get("skills", []))


def get_dictionary_tokens(text: Any) -> List[str]:
    features = extract_dictionary_features(clean_text(text))
    tokens = []

    for key in ["skills", "certifications", "requirements", "categories", "tasks"]:
        tokens.extend(features.get(key, []))

    return unique_preserve_order(tokens)


def calculate_skill_score(job_skills: Dict[str, Any], resume_skills: List[str]) -> Tuple[float, int, int, bool, List[str]]:
    required_skills = flatten_skill_items(job_skills.get("required", [])) if isinstance(job_skills, dict) else flatten_skill_items(job_skills)
    resume_skill_set = set(flatten_skill_items(resume_skills))

    if not required_skills:
        return 0.0, 0, 0, False, []

    matched = []

    for required_skill in required_skills:
        required_tokens = set(get_dictionary_skill_tokens(required_skill))
        skill_matched = required_skill in resume_skill_set

        if not skill_matched and required_tokens:
            skill_matched = bool(required_tokens & resume_skill_set)

        if skill_matched:
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

    # 높은 학력부터 확인
    if "박사" in text_no_space:
        return "박사"

    if "석사" in text_no_space:
        return "석사"

    # 전문대학교에도 '대학교'가 포함될 수 있으므로 먼저 확인
    if "초대졸" in text_no_space or "전문대" in text_no_space:
        return "초대졸"

    if (
        "대졸" in text_no_space
        or "4년제" in text_no_space
        or "학사" in text_no_space
        or "대학교" in text_no_space
    ):
        return "대졸"

    if "고졸" in text_no_space or "고등학교" in text_no_space:
        return "고졸"

    return text


def education_level(value: Any) -> int:
    education = normalize_education(value)
    return EDU_LEVELS.get(education, EDU_LEVELS.get(clean_text(value), 0))


def calculate_education_score(job_edu: Any, resume_edu: Any) -> Tuple[float, bool, str, str]:
    job_normalized = normalize_education(job_edu)
    resume_normalized = normalize_education(resume_edu)

    if not job_normalized or job_normalized in ["무관", "학력무관"]:
        return 10.0, False, "무관", resume_normalized or ""

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
    text1 = prepare_semantic_text(text1)
    text2 = prepare_semantic_text(text2)

    if not text1 or not text2:
        return 0.0

    emb1 = get_text_embedding(text1)
    emb2 = get_text_embedding(text2)
    similarity = util.cos_sim(emb1, emb2).item()

    return max(0.0, min(1.0, float(similarity)))


def build_experience_relevance_text(job: Dict[str, Any]) -> str:
    parts = []
    parts.extend(as_list(job.get("responsibilities", [])))

    qualifications = job.get("qualifications", {}) or {}

    if isinstance(qualifications, dict):
        parts.extend(as_qualification_list(qualifications.get("required", [])))
        parts.extend(as_qualification_list(qualifications.get("preferred", [])))

    skills = job.get("skills", {}) or {}

    if isinstance(skills, dict):
        parts.extend(flatten_skill_items(skills.get("required", [])))
        parts.extend(flatten_skill_items(skills.get("preferred", [])))

    return clean_text(" ".join(unique_preserve_order(parts)))


def calculate_experience_score(job: Dict[str, Any], resume: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    min_years = extract_min_years(job.get("experience", {}))
    resume_exp = float(resume.get("experienceYears", 0) or 0)

    if min_years <= 0:
        return 0.0, {
            "min_exp": min_years,
            "resume_exp": resume_exp,
            "exp_raw_score": 0.0,
            "exp_raw_score_max": 0.0,
            "exp_year_score": 0.0,
            "exp_year_max": 0.0,
            "exp_relevance_score": 0.0,
            "exp_relevance_max": 0.0,
            "exp_relevance_sim": 0.0,
            "exp_relevance_used": False,
            "exp_condition_used": False,
        }

    year_max = 10.0
    relevance_max = 10.0
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

    return year_score, {
        "min_exp": min_years,
        "resume_exp": resume_exp,
        "exp_raw_score": year_score,
        "exp_raw_score_max": year_max,
        "exp_year_score": year_score,
        "exp_year_max": year_max,
        "exp_relevance_score": relevance_score,
        "exp_relevance_max": relevance_max,
        "exp_relevance_sim": similarity,
        "exp_relevance_used": relevance_used,
        "exp_condition_used": True,
    }


def normalize_cert_name(value: Any) -> str:
    text = clean_text(value).lower()
    features = extract_dictionary_features(text)
    certifications = features.get("certifications", [])

    if certifications:
        return certifications[0]

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
        if any(cert == owned_cert or cert in owned_cert or owned_cert in cert for owned_cert in owned):
            matched.append(cert)

    score = (len(matched) / len(required)) * 10

    return score, len(matched), len(required), True, matched


QUALIFICATION_NOISE_KEYWORDS = [
    "담당업무",
    "담당 업무",
    "담당직무",
    "담당 직무",
    "상담문의",
    "청약",
    "배정",
    "어드민",
    "챗팅상담",
    "채팅상담",
    "근무환경",
    "근무기간",
    "전형절차",
    "접수방법",
    "급여",
    "근무시간",
    "근무장소",
    "서류전형",
    "면접전형",
    "최종합격",
    "지도보기",
    "인근지하철",
    "복리후생",
]

# 공공기관 채용공고에 자주 포함되지만,
# 이력서의 기술/학력/경력/자격증과 직접 비교하기 어려운 공통 법적·행정 조건.
# 이런 문장은 공고 원문에는 보존하되 '필수 자격요건 룰 점수'에서는 제외한다.
PUBLIC_INSTITUTION_NON_SCORABLE_QUAL_KEYWORDS = [
    "결격사유",
    "인사규정",
    "임용취소",
    "임용될 수 없",
    "정년에 따른",
    "정년(",
    "피성년후견인",
    "피한정후견인",
    "파산선고",
    "복권되지",
    "금고 이상의 형",
    "집행유예",
    "선고유예",
    "자격이 상실 또는 정지",
    "징계에 의하여",
    "병역기피",
    "채용신체검사",
    "신체검사 불합격",
    "부패방지",
    "비위면직",
    "채용비리",
    "부정한 방법으로 채용",
    "채용이 취소",
    "가족과 친척을 부당하게 채용",
    "성폭력범죄",
    "아동·청소년대상 성범죄",
    "노인복지법",
    "장애인복지법",
    "취업제한",
    "공고문 참고",
    "자세한 사항은",
]

# 실제 이력서와 비교할 수 있는 조건을 적극적으로 남기기 위한 힌트.
SCORABLE_QUALIFICATION_HINTS = [
    "자격증", "면허", "소지자", "전문의", "자격인정증",
    "경력", "경험", "전공", "학위", "학력",
    "가능자", "가능한 자", "활용", "사용", "숙련",
    "운전", "외국어", "토익", "toeic", "컴퓨터",
    "오피스", "excel", "엑셀", "한글", "powerpoint", "ppt",
]


# ----------------------------------------------------------------------
# 사회형평/특수 지원자격(eligibility)
# ----------------------------------------------------------------------
# resume_postprocess.py에서 구조화한 eligibility를 그대로 사용한다.
# 이 정보는 일반 텍스트 유사도로 추측하지 않는다.
ELIGIBILITY_FIELDS = (
    "veteran",
    "disability",
    "employmentSupport",
    "selfRelianceYouth",
)

ELIGIBILITY_LABELS = {
    "veteran": "보훈대상",
    "disability": "장애인",
    "employmentSupport": "취업지원대상",
    "selfRelianceYouth": "자립준비청년",
}


def normalize_eligibility_value(value: Any):
    """eligibility 값을 True / False / None으로만 정규화한다."""
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value == 1:
            return True
        if value == 0:
            return False

    text = clean_text(value).lower()

    if not text or text in {"none", "null", "unknown", "확인불가", "미확인"}:
        return None

    true_values = {
        "true", "yes", "y", "1", "대상", "해당", "예",
        "등록", "등록됨", "해당함", "대상자",
    }
    false_values = {
        "false", "no", "n", "0", "비대상", "미해당",
        "해당없음", "해당 없음", "아니오", "비해당",
    }

    if text in true_values:
        return True
    if text in false_values:
        return False

    # 모호한 문자열은 억지로 True/False로 만들지 않는다.
    return None


def normalize_resume_eligibility(value: Any) -> Dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    return {
        field: normalize_eligibility_value(raw.get(field))
        for field in ELIGIBILITY_FIELDS
    }


def extract_eligibility_requirement_keys(value: Any) -> List[str]:
    """
    자격요건 문장에서 구조화된 eligibility로만 확인해야 하는 조건을 찾는다.

    단순히 '장애인복지법'이 등장하는 결격사유 문장까지 장애인 전형으로
    오인하지 않도록, 장애 항목은 긍정적인 지원자격 문맥을 함께 요구한다.
    """
    text = clean_text(value)
    lowered = text.lower()

    if not lowered:
        return []

    result = []

    if any(keyword in lowered for keyword in [
        "자립준비청년", "보호종료아동", "보호종료청년", "보호종료 청년",
    ]):
        result.append("selfRelianceYouth")

    disability_positive = bool(re.search(
        r"(?:장애인\s*(?:등록|전형|대상|해당|증명|채용)|"
        r"장애\s*(?:전형|대상|해당)|"
        r"사회형평.{0,40}장애|장애.{0,40}사회형평)",
        lowered,
    ))
    if disability_positive:
        result.append("disability")

    if any(keyword in lowered for keyword in [
        "보훈대상", "보훈 대상", "보훈전형", "보훈 전형",
        "국가유공자", "보훈대상자",
    ]) or bool(re.search(r"사회형평.{0,40}보훈|보훈.{0,40}사회형평", lowered)):
        result.append("veteran")

    if any(keyword in lowered for keyword in [
        "취업지원대상자", "취업지원 대상자", "취업보호대상자",
        "취업보호 대상자",
    ]):
        result.append("employmentSupport")

    return unique_preserve_order(result)


def eligibility_requirement_uses_or(value: Any) -> bool:
    text = clean_text(value).lower()
    return bool(re.search(
        r"또는|혹은|어느\s*하나|중\s*(?:하나|1)|택\s*1|"
        r"장애\s*[,/·]\s*보훈|보훈\s*[,/·]\s*장애",
        text,
    ))


def evaluate_eligibility_qualification(
    qualification: Any,
    resume: Dict[str, Any],
) -> Tuple[bool, str, List[str]]:
    """
    반환: (eligibility 조건 여부, 상태, 관련 필드)

    상태:
      matched   - 구조화 값으로 충족 확인
      unmatched - 구조화 값으로 미충족 확인
      unknown   - 이력서에 확인 가능한 정보가 없음
      none      - eligibility 조건이 아님
    """
    keys = extract_eligibility_requirement_keys(qualification)

    if not keys:
        return False, "none", []

    eligibility = normalize_resume_eligibility(resume.get("eligibility", {}))
    values = [eligibility.get(key) for key in keys]

    if eligibility_requirement_uses_or(qualification):
        if any(value is True for value in values):
            return True, "matched", keys
        if values and all(value is False for value in values):
            return True, "unmatched", keys
        return True, "unknown", keys

    # OR 표현이 없다면 여러 조건은 AND로 본다.
    if any(value is False for value in values):
        return True, "unmatched", keys
    if values and all(value is True for value in values):
        return True, "matched", keys
    return True, "unknown", keys


def is_valid_required_qualification(text: Any) -> bool:
    value = clean_text(text)

    if not value:
        return False
    if len(value) <= 2:
        return False
    if value in {"담당업무 및", "자격요건 및", "[자격요건 및 ]", "근무환경", "근무 조건"}:
        return False
    if re.fullmatch(r"[0-9○O]+명", value):
        return False

    # 특정 모집분야 제목은 필수 자격요건 점수에서 제외
    if re.fullmatch(
        r"\[[^\]]+\]",
        value,
    ):
        return False

    # 담당업무/담당직무 문장은 자격요건이 아님
    if re.match(
        r"^(?:담당업무|담당 업무|담당직무|담당 직무)\s*[:：]",
        value,
    ):
        return False

    if re.match(
        r"^(?:모집\s*분야|모집분야)"
        r"\s*[:：]",
        value,
    ):
        return False

    if re.match(
        r"^(?=.*(?:청년인턴|체험형인턴|채용형인턴|기간제|무기계약|계약직))"
        r".+/.+\s+[-–—]\s+.+$",
        value,
    ):
        return False

    if any(keyword in value for keyword in QUALIFICATION_NOISE_KEYWORDS):
        return False

    # 자립준비청년/장애/보훈/취업지원대상 등은 공통 법적 문구가 아니라
    # 실제 지원 가능 여부를 결정하는 조건이므로 반드시 구조화 값으로 평가한다.
    if extract_eligibility_requirement_keys(value):
        return True

    # 공공기관 공통 법적/행정 자격조건은 이력서 적합도 룰 점수에서 제외한다.
    lowered = value.lower()
    if any(keyword.lower() in lowered for keyword in PUBLIC_INSTITUTION_NON_SCORABLE_QUAL_KEYWORDS):
        return False

    return True


def is_scorable_required_qualification(text: Any) -> bool:
    """
    실제 이력서 내용과 비교해 점수화할 수 있는 자격요건인지 판단한다.

    1) 기존 노이즈/공공기관 공통 법적 조건 제거
    2) 사전에서 기술·자격·업무·카테고리 등의 신호가 잡히면 평가
    3) 사전 신호가 없어도 자격증/면허/경력/전공/활용 가능 등
       명시적 자격 힌트가 있으면 평가
    """
    value = clean_text(text)

    if not is_valid_required_qualification(value):
        return False

    if extract_eligibility_requirement_keys(value):
        return True

    features = extract_dictionary_features(value)
    feature_count = 0

    for key in ["skills", "certifications", "requirements", "categories", "tasks"]:
        feature_count += len(features.get(key, []))

    if feature_count > 0:
        return True

    lowered = value.lower()
    if any(hint.lower() in lowered for hint in SCORABLE_QUALIFICATION_HINTS):
        return True

    # 너무 포괄적이거나 추상적인 문장은 자동 룰 점수에는 넣지 않는다.
    return False


# ----------------------------------------------------------------------
# 필수 자격요건 매칭 보강
# ----------------------------------------------------------------------
# 기존에는 qualification_tokens와 resume_tokens가 하나라도 겹치면
# 전체 자격요건을 충족한 것으로 처리했다.
#
# 예:
#   "전문의 자격증 + 임상강사 1년 이상"
#   -> "의료", "경력" 같은 일반 토큰 하나만 겹쳐도 True가 될 수 있었음.
#
# 아래 로직에서는 자격/면허/학위/특정 역할 경력처럼
# 반드시 직접 확인해야 하는 "강한 조건"을 먼저 검사하고,
# 강한 조건이 없는 문장에만 일반 사전 토큰 매칭을 적용한다.
# ----------------------------------------------------------------------

HARD_QUALIFICATION_TERMS = [
    # 의료/보건
    "전문의",
    "임상강사",
    "군의관",
    "간호사",
    "간호조무사",
    "약사",
    "한약사",
    "치과의사",
    "한의사",
    "수의사",
    "물리치료사",
    "작업치료사",
    "방사선사",
    "임상병리사",
    "영양사",

    # 법률/회계/전문자격
    "공인노무사",
    "노무사",
    "변호사",
    "공인회계사",
    "회계사",
    "세무사",
    "법무사",
    "감정평가사",
    "건축사",
    "사회복지사",
]

HARD_ROLE_TERMS = [
    "임상강사",
    "군의관",
    "임상교수",
    "진료교수",
    "전담교수",
    "진료전담교수",
    "교수",
    "전공의",
]

GENERIC_CREDENTIAL_WORDS = {
    "해당",
    "관련",
    "필수",
    "우대",
    "소지",
    "소지자",
    "자격",
    "자격증",
    "면허",
    "면허증",
    "자격인정증",
    "진료과",
    "지원분야",
    "지원 분야",
    "직무",
    "분야",
}


def normalize_qualification_match_text(value: Any) -> str:
    """
    자격요건의 직접 문자열 비교용 정규화.

    예:
    - "간호사 면허" -> "간호사면허"
    - "공인 노무사" -> "공인노무사"
    """
    text = clean_text(value).lower()
    text = re.sub(r"[\s·ㆍ,;:()\[\]{}<>/+_\-]", "", text)
    return text


def extract_degree_requirement(qualification: Any) -> str:
    """
    자격요건 문장에 명시된 최소 학위를 반환한다.
    여러 학위가 동시에 잡히면 가장 높은 학위를 사용한다.
    """
    text = clean_text(qualification)

    if "박사" in text:
        return "박사"
    if "석사" in text:
        return "석사"
    if "학사" in text:
        return "학사"

    return ""


MAJOR_EXPLICIT_KEYS = {
    "major",
    "majorname",
    "major_name",
    "department",
    "departmentname",
    "department_name",
    "field",
    "fieldofstudy",
    "field_of_study",
    "specialization",
    "minor",
    "minorname",
    "minor_name",
    "doublemajor",
    "double_major",
    "secondmajor",
    "second_major",
    "submajor",
    "sub_major",
    "복수전공",
    "부전공",
    "전공",
    "학과",
}

MAJOR_GENERIC_TERMS = {
    "학",
    "대학",
    "전문대학",
    "대학교",
    "대학원",
    "학부",
    "학과",
    "전공",
    "관련학",
}


def normalize_major_name(value: Any) -> str:
    """전공명 비교용 정규화.

    핵심 원칙은 '부분문자열'이 아니라 전공명 자체를 비교하는 것이다.

    예:
      행정학과       -> 행정학
      보건행정학     -> 보건행정학
      의(료)공학     -> 의료공학
      사회(복지)학   -> 사회복지학
    """
    text = clean_text(value).lower()

    if not text:
        return ""

    # 의(료)공학, 사회(복지)학과 같은 표기를 하나의 전공명으로 만든다.
    text = re.sub(r"[()\[\]{}<>'\"‘’“”]", "", text)
    text = re.sub(r"[·ㆍ,;:/+_|\\\-]", "", text)
    text = re.sub(r"\s+", "", text)

    # 학과/학부/전공 표기는 비교에 필요 없는 후행 라벨이다.
    if text.endswith("학과"):
        text = text[:-1]  # 행정학과 -> 행정학
    elif text.endswith("학부"):
        text = text[:-2]
    elif text.endswith("전공"):
        text = text[:-2]

    return text.strip()


def extract_major_terms_from_text(value: Any) -> List[str]:
    """문장 안에서 실제 전공명으로 볼 수 있는 표현을 추출한다.

    보건행정학, 행정학과, 사회(복지)학, 의(료)공학 등을 잡되
    '대학교', '학사' 같은 학력 표현은 전공명으로 보지 않는다.
    """
    text = clean_text(value)

    if not text:
        return []

    result: List[str] = []

    # 일반적인 한국어 전공명: 행정학, 간호학, 컴퓨터공학, 행정학과 등.
    # 공백을 넘지 않게 잡아 학교명이나 앞 문장까지 함께 먹지 않도록 한다.
    pattern = r"[가-힣A-Za-z]+(?:\([가-힣A-Za-z]+\))?[가-힣A-Za-z]*(?:학과|학부|학)"

    for match in re.finditer(pattern, text):
        candidate = normalize_major_name(match.group(0))

        if not candidate:
            continue

        if candidate in MAJOR_GENERIC_TERMS:
            continue

        # '학사학위', '전문학사' 등의 학력 표현이 잘려 들어오는 경우 방지
        if candidate in {"학사학", "전문학", "전문학사학", "석사학", "박사학"}:
            continue

        result.append(candidate)

    return unique_preserve_order(result)


def extract_resume_major_names(education_items: Any) -> List[str]:
    """resumeData.education에서 전공/복수전공/부전공을 최대한 보존해 추출한다."""
    result: List[str] = []

    for item in as_list(education_items):
        # 구조화된 교육 객체라면 전공 계열 키를 우선 사용한다.
        if isinstance(item, dict):
            for key, value in item.items():
                normalized_key = str(key).replace(" ", "").lower()

                if normalized_key in MAJOR_EXPLICIT_KEYS:
                    for major_value in as_list(value):
                        major_text = clean_text(major_value)
                        if not major_text:
                            continue

                        extracted = extract_major_terms_from_text(major_text)

                        if extracted:
                            result.extend(extracted)
                        else:
                            normalized = normalize_major_name(major_text)
                            if normalized and normalized not in MAJOR_GENERIC_TERMS:
                                result.append(normalized)

            # 키 이름을 모르는 구조도 있으므로 객체 전체 텍스트에서 한 번 더 추출한다.
            result.extend(extract_major_terms_from_text(item))
        else:
            result.extend(extract_major_terms_from_text(item))

    return unique_preserve_order(result)


def extract_required_major_info(qualification: Any) -> Dict[str, Any]:
    """자격요건에서 필수 전공 정보를 추출한다.

    반환 예:
      '보건학, 행정학, 법학 학사학위 이상'
        -> exactMajors=['보건학', '행정학', '법학']

      '행정 관련 전공 학사 이상'
        -> relatedAnchors=['행정']

      '학사(전공무관)'
        -> used=False

    전공 나열은 통상 OR 조건으로 해석한다.
    """
    text = clean_text(qualification)
    compact = re.sub(r"\s+", "", text).lower()

    if not text:
        return {
            "used": False,
            "exactMajors": [],
            "relatedAnchors": [],
        }

    if any(term in compact for term in ["전공무관", "학과무관", "전공제한없음"]):
        return {
            "used": False,
            "exactMajors": [],
            "relatedAnchors": [],
        }

    # 전공/학위/졸업 맥락이 없는 문장에서 우연히 '~학' 단어가 나온 것은
    # 필수 전공으로 취급하지 않는다.
    major_context = any(
        keyword in text
        for keyword in [
            "전공",
            "학과",
            "학위",
            "졸업",
            "학사",
            "전문학사",
            "석사",
            "박사",
        ]
    )

    exact_majors = extract_major_terms_from_text(text) if major_context else []

    # '행정 관련 전공', '전기 관련 학과'처럼 '~학'으로 끝나지 않는
    # 포괄 분야 조건도 별도로 보존한다.
    related_anchors = []
    related_pattern = r"([가-힣A-Za-z0-9()]+)\s*관련\s*(?:전공|학과|분야)"

    for match in re.finditer(related_pattern, text):
        anchor = normalize_major_name(match.group(1))
        if anchor and anchor not in MAJOR_GENERIC_TERMS:
            related_anchors.append(anchor)

    exact_majors = unique_preserve_order(exact_majors)
    related_anchors = unique_preserve_order(related_anchors)

    return {
        "used": bool(exact_majors or related_anchors),
        "exactMajors": exact_majors,
        "relatedAnchors": related_anchors,
    }


def major_requirement_matches(
    qualification: Any,
    resume: Dict[str, Any],
) -> Tuple[bool, bool, Dict[str, Any]]:
    """필수 전공 조건을 이력서 전공과 비교한다.

    정확한 전공 나열은 '완전 일치'만 허용한다.
    따라서 행정학 != 보건행정학이다.

    단, '행정 관련 전공'처럼 명시적으로 '관련'이라고 적힌 조건은
    해당 분야명이 전공명에 독립적인 어근으로 포함되는 것을 허용한다.
    """
    info = extract_required_major_info(qualification)

    if not info.get("used"):
        return False, False, info

    resume_majors = unique_preserve_order([
        normalize_major_name(item)
        for item in as_list(resume.get("majors", []))
        if normalize_major_name(item)
    ])

    if not resume_majors:
        return True, False, info

    exact_required = set(info.get("exactMajors", []))
    resume_major_set = set(resume_majors)

    # 전공 나열은 OR. 정확한 정규화 이름이 하나라도 같아야 한다.
    if exact_required and (exact_required & resume_major_set):
        return True, True, info

    # '관련 전공/관련 학과/관련 분야'라고 명시된 경우에만 포괄 매칭 허용.
    for anchor in info.get("relatedAnchors", []):
        if not anchor:
            continue

        for resume_major in resume_majors:
            if (
                resume_major == anchor
                or resume_major.startswith(anchor)
                or anchor.startswith(resume_major)
            ):
                return True, True, info

    return True, False, info


def extract_hard_qualification_terms(qualification: Any) -> List[str]:
    """
    일반적인 토큰 유사도로 대체하면 안 되는 핵심 자격/직종명을 추출한다.

    1) 단어사전에서 자격증으로 잡힌 값
    2) 의료/전문직처럼 직종명 자체가 필수자격인 값
    3) '~기사', '~기능사', '~기술사'처럼 명칭 자체가 자격인 값
    """
    text = clean_text(qualification).lower()
    result = []

    features = extract_dictionary_features(text)

    # 기존 단어사전에 등록된 자격증은 그대로 강한 조건으로 사용
    result.extend(
        clean_text(item)
        for item in features.get("certifications", [])
        if clean_text(item)
    )

    # 명시적인 전문직/직종 자격
    for term in HARD_QUALIFICATION_TERMS:
        if term.lower() in text:
            result.append(term)

    # 기사/산업기사/기능사/기술사/관리사 등 자격 명칭
    suffix_pattern = (
        r"([가-힣A-Za-z0-9]+"
        r"(?:기사|산업기사|기능사|기술사|관리사|지도사))"
    )

    for match in re.finditer(suffix_pattern, text):
        term = clean_text(match.group(1))
        if term:
            result.append(term)

    # "OO 면허", "OO 자격증", "OO 자격인정증"에서 핵심 명칭 추출
    # 너무 긴 문장을 통째로 자격명으로 잡지 않도록 바로 앞 1~4개 단어만 본다.
    credential_phrase_pattern = (
        r"((?:[가-힣A-Za-z0-9]+\s+){0,3}"
        r"[가-힣A-Za-z0-9]+)"
        r"\s*(?:면허증?|자격증|자격인정증)"
    )

    for match in re.finditer(credential_phrase_pattern, text):
        phrase = clean_text(match.group(1))
        tokens = [
            token
            for token in re.findall(r"[가-힣A-Za-z0-9]+", phrase)
            if token not in GENERIC_CREDENTIAL_WORDS
        ]

        if not tokens:
            continue

        # "해당 진료과 전문의 자격증"처럼 앞부분이 일반 표현이면
        # 가장 핵심적인 뒤쪽 명칭을 남긴다.
        candidate = " ".join(tokens[-2:])

        if candidate:
            result.append(candidate)

    # 긴 표현과 짧은 표현이 동시에 잡힌 경우
    # 예: "해당 진료과 전문의", "전문의" -> "전문의"를 유지
    normalized = unique_preserve_order(result)

    cleaned = []
    for term in normalized:
        compact = normalize_qualification_match_text(term)

        if not compact:
            continue

        # 자격명이라고 보기 어려운 일반 표현은 제외
        if compact in {
            "관련",
            "해당",
            "필수",
            "자격",
            "자격증",
            "면허",
            "소지자",
        }:
            continue

        cleaned.append(term)

    return unique_preserve_order(cleaned)


def extract_hard_role_terms(qualification: Any) -> List[str]:
    """
    특정 역할/직급 경력이 반드시 필요한 조건을 추출한다.

    예:
    - 임상강사 1년 이상
    - 군의관/군복무 관련 임상강사 경력
    """
    text = clean_text(qualification).lower()

    return unique_preserve_order([
        term
        for term in HARD_ROLE_TERMS
        if term.lower() in text
    ])



EXPERIENCE_FIELD_GENERIC_WORDS = {
    "경력", "경험", "실무", "업무", "근무", "근무경력", "실무경력", "업무경력",
    "관련", "해당", "지원", "지원분야", "지원 분야", "분야", "직무", "담당",
    "이상", "이하", "내외", "년", "개월", "필수", "우대", "요건", "조건",
    "자격", "자격증", "면허", "면허증", "자격인정증", "소지", "소지자",
    "가능", "가능자", "등", "및", "또는", "혹은", "그리고",
}

EXPERIENCE_FIELD_COMPOUND_SUFFIXES = [
    "간호", "개발", "연구", "교육", "관리", "행정", "회계", "조리", "정비",
    "운전", "설계", "분석", "영업", "상담", "생산", "품질", "보안", "임상",
]


def _clean_experience_field_piece(value: Any) -> str:
    """경력 분야 비교에 불필요한 표현을 제거한다."""
    text = clean_text(value).lower()

    if not text:
        return ""

    # 기간 표현 제거
    text = re.sub(
        r"\d+(?:\.\d+)?\s*(?:년|개월)\s*(?:이상|이하|내외|초과|미만)?",
        " ",
        text,
    )

    # 경력 자체를 뜻하는 표현과 자격 표현 제거
    text = re.sub(
        r"(?:근무\s*)?(?:실무\s*)?(?:업무\s*)?(?:경력|경험)",
        " ",
        text,
    )
    text = re.sub(
        r"(?:자격인정증|자격증|면허증?|소지자|소지)",
        " ",
        text,
    )

    text = re.sub(r"\s+", " ", text).strip(" ,./;:()[]{}<>|\\\"'")
    return text


def extract_experience_field_groups(qualification: Any) -> List[List[str]]:
    """
    '특정 분야 + N년 이상' 조건을 AND/OR 그룹으로 분리한다.

    예:
      JSP PHP HTML 등 웹 개발 및 사업관리 경력 1년 이상
        -> [[JSP, PHP, HTML, 웹 개발], [사업관리]]

      교육 및 연구경력 4년 이상
        -> [[교육], [연구]]

      간호사 또는 간호조무사 경력 1년 이상
        -> [[간호사, 간호조무사]]

    바깥 리스트는 AND, 안쪽 리스트는 OR 의미로 사용한다.
    '관련 분야 경력'처럼 구체 분야를 알 수 없는 문장은 빈 리스트를 반환한다.
    """
    raw = clean_text(qualification).lower()

    if not raw:
        return []

    if extract_min_years(raw) <= 0 and not any(
        keyword in raw
        for keyword in ["경력", "경험"]
    ):
        return []

    working = _clean_experience_field_piece(raw)

    if not working:
        return []

    # '및', '+', '그리고'는 동시에 요구되는 그룹으로 본다.
    and_groups = re.split(
        r"\s*(?:및|그리고|\+)\s*",
        working,
    )

    result: List[List[str]] = []

    for group_text in and_groups:
        group_text = clean_text(group_text)

        if not group_text:
            continue

        # '또는', '/', ',', '등'은 같은 그룹 내 대안으로 본다.
        alternative_chunks = re.split(
            r"\s*(?:또는|혹은|/|,|;|\||등)\s*",
            group_text,
        )

        alternatives: List[str] = []

        for chunk in alternative_chunks:
            chunk = _clean_experience_field_piece(chunk)

            if not chunk:
                continue

            # 영어 기술명은 각각 독립 대안으로 분리한다.
            english_terms = re.findall(
                r"\b[a-z][a-z0-9+#.]{1,}\b",
                chunk,
            )

            for term in english_terms:
                if term not in {"and", "or", "etc"}:
                    alternatives.append(term)

            # 영어 토큰을 제거하고 남은 한국어/혼합 분야 표현을 보존한다.
            korean_part = re.sub(
                r"\b[a-z][a-z0-9+#.]{1,}\b",
                " ",
                chunk,
            )
            korean_part = re.sub(r"\s+", " ", korean_part).strip()

            # 앞뒤의 일반 표현 제거
            tokens = re.findall(r"[가-힣A-Za-z0-9+#.]+", korean_part)
            tokens = [
                token
                for token in tokens
                if token not in EXPERIENCE_FIELD_GENERIC_WORDS
            ]

            if tokens:
                phrase = " ".join(tokens)
                compact = normalize_qualification_match_text(phrase)

                if len(compact) >= 2:
                    alternatives.append(phrase)

        alternatives = unique_preserve_order(alternatives)

        # 구체적인 분야 신호가 없는 그룹은 평가에서 제외
        meaningful = []
        for term in alternatives:
            compact = normalize_qualification_match_text(term)
            if not compact:
                continue
            if compact in {
                normalize_qualification_match_text(x)
                for x in EXPERIENCE_FIELD_GENERIC_WORDS
            }:
                continue
            meaningful.append(term)

        meaningful = unique_preserve_order(meaningful)

        if meaningful:
            result.append(meaningful)

    return result


def experience_field_term_matches(
    term: str,
    resume_experience_text: str,
    resume_feature_tokens: set,
) -> bool:
    """하나의 경력 분야/기술 신호가 이력서의 실제 경험 내용에 존재하는지 확인한다."""
    term = clean_text(term).lower()

    if not term:
        return False

    normalized_term = normalize_qualification_match_text(term)
    normalized_resume = normalize_qualification_match_text(resume_experience_text)

    if not normalized_term or not normalized_resume:
        return False

    # 1) 직접 문자열 일치
    if normalized_term in normalized_resume:
        return True

    # 2) 단어사전 별칭/표준 토큰 일치
    term_features = extract_dictionary_features(term)
    term_feature_tokens = set()

    for key in ["skills", "requirements", "categories", "tasks"]:
        term_feature_tokens.update(term_features.get(key, []))

    if term_feature_tokens and (term_feature_tokens & resume_feature_tokens):
        return True

    # 3) '웹 개발'처럼 공백이 있는 표현은 구성 단어를 모두 확인
    phrase_tokens = [
        token
        for token in re.findall(r"[가-힣A-Za-z0-9+#.]+", term)
        if token not in EXPERIENCE_FIELD_GENERIC_WORDS
    ]

    if len(phrase_tokens) >= 2:
        if all(
            normalize_qualification_match_text(token) in normalized_resume
            for token in phrase_tokens
        ):
            return True

    # 4) '외래간호'처럼 붙어 있는 한국어 복합어는
    #    핵심 접미어와 앞부분이 모두 경험 텍스트에 있는지 확인한다.
    if re.fullmatch(r"[가-힣]{3,}", term):
        for suffix in EXPERIENCE_FIELD_COMPOUND_SUFFIXES:
            if term.endswith(suffix) and len(term) > len(suffix):
                prefix = term[:-len(suffix)]
                if (
                    normalize_qualification_match_text(prefix) in normalized_resume
                    and normalize_qualification_match_text(suffix) in normalized_resume
                ):
                    return True

    return False


def experience_field_groups_match(
    qualification: str,
    resume: Dict[str, Any],
) -> Tuple[bool, bool, List[List[str]]]:
    """
    특정 분야 경력 조건을 실제 경험 내용과 비교한다.

    반환:
      (field_condition_used, field_condition_matched, groups)

    그룹 간에는 AND, 한 그룹 안에서는 OR로 평가한다.
    """
    groups = extract_experience_field_groups(qualification)

    if not groups:
        return False, False, []

    resume_experience_text = clean_text(
        " ".join(
            as_list(
                resume.get(
                    "projects",
                    [],
                )
            )
        )
    ).lower()

    if not resume_experience_text:
        return True, False, groups

    resume_features = extract_dictionary_features(resume_experience_text)
    resume_feature_tokens = set()

    for key in ["skills", "requirements", "categories", "tasks"]:
        resume_feature_tokens.update(resume_features.get(key, []))

    # 모든 AND 그룹에서 최소 하나의 대안이 실제 경력 내용과 일치해야 한다.
    for group in groups:
        if not any(
            experience_field_term_matches(
                term,
                resume_experience_text,
                resume_feature_tokens,
            )
            for term in group
        ):
            return True, False, groups

    return True, True, groups


def qualification_term_in_resume(term: str, resume_text: str, resume_certs: List[Any]) -> bool:
    """
    강한 자격/직종명이 실제 이력서에 직접 존재하는지 검사한다.
    일반 사전 토큰 교집합은 사용하지 않는다.
    """
    normalized_term = normalize_qualification_match_text(term)

    if not normalized_term:
        return False

    normalized_resume = normalize_qualification_match_text(resume_text)

    if normalized_term in normalized_resume:
        return True

    for cert in as_list(resume_certs):
        normalized_cert = normalize_qualification_match_text(cert)

        if not normalized_cert:
            continue

        if (
            normalized_term == normalized_cert
            or normalized_term in normalized_cert
            or normalized_cert in normalized_term
        ):
            return True

    return False


def check_hard_qualification(
    qualification: str,
    resume: Dict[str, Any],
    resume_text: str,
) -> Tuple[bool, bool]:
    """
    자격요건 안에 강한 필수조건이 있는 경우 직접 검증한다.

    반환:
        (hard_condition_used, hard_condition_matched)

    hard_condition_used=True인 문장은 이후 일반 토큰 매칭으로
    우회해서 통과시키지 않는다.
    """
    hard_used = False

    # --------------------------------------------------
    # 1. 자격증 / 면허 / 전문직 자격
    # --------------------------------------------------
    hard_terms = extract_hard_qualification_terms(
        qualification
    )

    if hard_terms:
        hard_used = True

        # 복합 필수조건은 모두 충족해야 한다.
        for term in hard_terms:
            if not qualification_term_in_resume(
                term,
                resume_text,
                resume.get("certifications", []),
            ):
                return True, False

    # --------------------------------------------------
    # 2. 학위 + 필수 전공
    # --------------------------------------------------
    required_degree = extract_degree_requirement(
        qualification
    )

    if required_degree:
        hard_used = True

        if education_level(
            resume.get("education", "")
        ) < education_level(
            required_degree
        ):
            return True, False

    # 학위 수준만 충족했다고 전공까지 충족한 것으로 보지 않는다.
    # 예: 행정학 학사 != 보건행정학 학사
    major_used, major_matched, _ = major_requirement_matches(
        qualification,
        resume,
    )

    if major_used:
        hard_used = True

        if not major_matched:
            return True, False

    # --------------------------------------------------
    # 3. 최소 경력연수 + 경력 분야
    # --------------------------------------------------
    min_years = extract_min_years(
        qualification
    )

    if min_years > 0:
        hard_used = True

        try:
            resume_years = float(
                resume.get(
                    "experienceYears",
                    0,
                )
                or 0
            )
        except Exception:
            resume_years = 0.0

        # 먼저 총 경력연수가 최소 연수를 충족해야 한다.
        if resume_years < min_years:
            return True, False

        # '웹 개발 경력 1년', '교육 및 연구경력 4년'처럼
        # 특정 분야가 함께 명시되어 있으면 총 경력만으로 통과시키지 않는다.
        field_used, field_matched, _ = experience_field_groups_match(
            qualification,
            resume,
        )

        if field_used and not field_matched:
            return True, False

    # --------------------------------------------------
    # 4. 특정 역할/직급 경력
    # --------------------------------------------------
    role_terms = extract_hard_role_terms(
        qualification
    )

    if role_terms:
        hard_used = True

        resume_experience_text = clean_text(
            " ".join(
                as_list(
                    resume.get(
                        "projects",
                        [],
                    )
                )
            )
        ).lower()

        # 복합조건으로 적힌 역할은 모두 직접 확인한다.
        # 예: "전문의 + 임상강사"에서 간호 경력만으로 통과 불가
        for role in role_terms:
            if (
                normalize_qualification_match_text(
                    role
                )
                not in
                normalize_qualification_match_text(
                    resume_experience_text
                )
            ):
                return True, False

    if hard_used:
        return True, True

    return False, False


def calculate_qualification_rule_score_detailed(
    required_quals: List[Any],
    resume: Dict[str, Any],
) -> Tuple[float, List[str], int, bool, Dict[str, Any]]:
    # 자격요건은 쉼표로 분리하지 않고 줄 단위로 유지하며,
    # 실제 이력서와 비교 가능한 조건만 룰 점수에 사용한다.
    required = [
        clean_text(item)
        for item
        in as_qualification_list(
            required_quals
        )
    ]

    required = [
        remove_stopwords(item)
        for item
        in required
    ]

    required = [
        item
        for item
        in required
        if is_scorable_required_qualification(
            item
        )
    ]

    required = unique_preserve_order(
        required
    )

    empty_detail = {
        "eligibility_matched": [],
        "eligibility_unmatched": [],
        "eligibility_unknown": [],
        "eligibility_fields": {},
    }

    if not required:
        return 0.0, [], 0, False, empty_detail

    resume_text = clean_text(
        " ".join([
            safe_str(
                resume.get(
                    "skills",
                    [],
                )
            ),
            safe_str(
                resume.get(
                    "certifications",
                    [],
                )
            ),
            safe_str(
                resume.get(
                    "projects",
                    [],
                )
            ),
            safe_str(
                resume.get(
                    "education",
                    "",
                )
            ),
            safe_str(
                resume.get(
                    "majors",
                    [],
                )
            ),
            safe_str(
                resume.get(
                    "educationDetails",
                    [],
                )
            ),
        ])
    ).lower()

    resume_features = (
        extract_dictionary_features(
            resume_text
        )
    )

    resume_tokens = set()

    for key in [
        "skills",
        "certifications",
        "requirements",
        "categories",
        "tasks",
    ]:
        resume_tokens.update(
            resume_features.get(
                key,
                [],
            )
        )

    matched = []
    eligibility_matched = []
    eligibility_unmatched = []
    eligibility_unknown = []
    eligibility_fields = {}

    for qualification in required:
        key = clean_text(
            qualification
        ).lower()

        # ==================================================
        # 0. 사회형평/특수 지원자격
        # ==================================================
        eligibility_used, eligibility_state, eligibility_keys = (
            evaluate_eligibility_qualification(
                qualification,
                resume,
            )
        )

        if eligibility_used:
            eligibility_fields[qualification] = eligibility_keys

            if eligibility_state == "matched":
                eligibility_matched.append(qualification)
                matched.append(qualification)
            elif eligibility_state == "unmatched":
                eligibility_unmatched.append(qualification)
            else:
                eligibility_unknown.append(qualification)

            # eligibility 조건은 일반 토큰 유사도로 우회 통과시키지 않는다.
            continue

        # ==================================================
        # 1. 강한 필수조건 우선 검사
        # ==================================================
        hard_used, hard_matched = (
            check_hard_qualification(
                qualification,
                resume,
                resume_text,
            )
        )

        if hard_used:
            if hard_matched:
                matched.append(
                    qualification
                )

            # 강한 조건이 하나라도 있는 문장은
            # 일반 토큰 교집합으로 우회하여 통과시키지 않는다.
            continue

        # ==================================================
        # 2. 일반 조건
        # ==================================================
        qualification_features = (
            extract_dictionary_features(
                key
            )
        )

        qualification_tokens = set()

        for feature_key in [
            "skills",
            "certifications",
            "requirements",
            "categories",
            "tasks",
        ]:
            qualification_tokens.update(
                qualification_features.get(
                    feature_key,
                    [],
                )
            )

        is_matched = False

        # 하나만 겹쳐도 전체 조건이 True가 되는 문제를 제거한다.
        if (
            qualification_tokens
            and resume_tokens
        ):
            overlap = (
                qualification_tokens
                & resume_tokens
            )

            if len(
                qualification_tokens
            ) == 1:
                is_matched = bool(
                    overlap
                )
            else:
                overlap_ratio = (
                    len(overlap)
                    / len(
                        qualification_tokens
                    )
                )

                is_matched = (
                    len(overlap) >= 2
                    and overlap_ratio >= 0.60
                )

        if (
            not is_matched
            and key
            and key in resume_text
        ):
            is_matched = True

        if is_matched:
            matched.append(
                qualification
            )

    score = (
        len(matched)
        / len(required)
    ) * 10

    detail = {
        "eligibility_matched": unique_preserve_order(eligibility_matched),
        "eligibility_unmatched": unique_preserve_order(eligibility_unmatched),
        "eligibility_unknown": unique_preserve_order(eligibility_unknown),
        "eligibility_fields": eligibility_fields,
    }

    return (
        score,
        matched,
        len(required),
        True,
        detail,
    )


def calculate_qualification_rule_score(
    required_quals: List[Any],
    resume: Dict[str, Any],
) -> Tuple[float, List[str], int, bool]:
    """기존 호출부와 호환되는 4개 반환값 wrapper."""
    score, matched, total, used, _ = calculate_qualification_rule_score_detailed(
        required_quals,
        resume,
    )
    return score, matched, total, used


def calculate_semantic_score(resume_text: str, job_text: str, max_score: float) -> Tuple[float, float]:
    similarity = calculate_text_similarity(resume_text, job_text)
    return similarity, similarity * max_score


def calculate_required_condition_ratio(
    skill_used: bool,
    skill_match_count: int,
    skill_total_count: int,
    cert_used: bool,
    cert_match_count: int,
    cert_total_count: int,
    qual_used: bool,
    qual_rule_score_raw: float,
    qual_total_count: int,
) -> float:
    ratios = []

    if skill_used and skill_total_count > 0:
        ratios.append(skill_match_count / skill_total_count)

    if cert_used and cert_total_count > 0:
        ratios.append(cert_match_count / cert_total_count)

    if qual_used and qual_total_count > 0:
        ratios.append(get_score_ratio(qual_rule_score_raw, 10))

    if not ratios:
        return 1.0

    return round(max(0.0, min(sum(ratios) / len(ratios), 1.0)), 4)


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

    education_list = data.get("education", []) or []
    education_candidates = []
    education_details = []

    for education_item in as_list(education_list):
        normalized_education = normalize_education(education_item)

        if normalized_education:
            education_candidates.append(normalized_education)

        raw_education_text = clean_text(education_item)
        if raw_education_text:
            education_details.append(raw_education_text)

    education = ""

    if education_candidates:
        education = max(
            education_candidates,
            key=education_level,
        )

    # 기존에는 normalize_education() 결과(대졸/석사 등)만 남겨
    # 실제 전공명이 사라졌다. 필수전공 검증을 위해 별도로 보존한다.
    majors = extract_resume_major_names(education_list)

    # 일부 분석 결과는 전공을 education이 아닌 별도 필드에 저장할 수 있으므로
    # 흔한 전공 필드도 보조적으로 확인한다.
    for extra_major_source in [
        data.get("major", []),
        data.get("majors", []),
        data.get("fieldOfStudy", []),
        data.get("doubleMajor", []),
        data.get("minor", []),
    ]:
        for major_value in as_list(extra_major_source):
            extracted = extract_major_terms_from_text(major_value)
            if extracted:
                majors.extend(extracted)
            else:
                normalized_major = normalize_major_name(major_value)
                if normalized_major and normalized_major not in MAJOR_GENERIC_TERMS:
                    majors.append(normalized_major)

    majors = unique_preserve_order(majors)

    exp_summary = data.get("experienceSummary", {}) or {}
    experience_years = float(exp_summary.get("yearsFloat", 0) or exp_summary.get("years", 0) or 0)

    # 구조화 단계에서 만든 지원자격 정보는 일반 텍스트로 합치지 않고
    # 별도 구조로 보존하여 필수 지원자격 판정에만 사용한다.
    eligibility = normalize_resume_eligibility(data.get("eligibility", {}))

    certifications = []

    for cert in as_list(data.get("certifications", [])):
        if isinstance(cert, dict):
            certifications.append(cert.get("name", ""))
        else:
            certifications.append(cert)

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

    resume_text_for_dictionary = clean_text(" ".join([
        safe_str(skills),
        safe_str(certifications),
        safe_str(projects),
        safe_str(education),
        safe_str(majors),
        safe_str(education_details),
    ]))

    dictionary_features = extract_dictionary_features(resume_text_for_dictionary)

    skills = unique_preserve_order(flatten_skill_items(skills))

    certifications = unique_preserve_order([
        *certifications,
        *dictionary_features.get("certifications", []),
    ])

    return {
        "skills": skills,
        "education": normalize_education(education),
        "educationDetails": unique_preserve_order(education_details),
        "majors": majors,
        "experienceYears": experience_years,
        "certifications": certifications,
        "eligibility": eligibility,
        "projects": unique_preserve_order(projects),
        "dictionaryFeatures": dictionary_features,
    }


def extract_job_category(
    firebase_job_doc: Dict[str, Any],
    job: Dict[str, Any],
    job_text: str,
) -> str:
    """
    공고의 대표 JOBPICK 카테고리를 하나만 반환한다.

    기존처럼 여러 source 값을 문자열로 모두 이어붙이지 않는다.
    """

    values = []

    for source in [
        firebase_job_doc,
        job,
        (
            firebase_job_doc.get(
                "meta",
                {},
            )
            if isinstance(
                firebase_job_doc.get(
                    "meta",
                    {},
                ),
                dict,
            )
            else {}
        ),
        (
            firebase_job_doc.get(
                "legacyJobPosting",
                {},
            )
            if isinstance(
                firebase_job_doc.get(
                    "legacyJobPosting",
                    {},
                ),
                dict,
            )
            else {}
        ),
        (
            job.get(
                "job",
                {},
            )
            if isinstance(
                job.get(
                    "job",
                    {},
                ),
                dict,
            )
            else {}
        ),
    ]:
        if not isinstance(
            source,
            dict,
        ):
            continue

        values.extend([
            source.get(
                "category",
                "",
            ),
            source.get(
                "jobCategory",
                "",
            ),
            source.get(
                "department",
                "",
            ),
            source.get(
                "field",
                "",
            ),
        ])

    values = unique_preserve_order(
        values
    )

    known_categories = {
        "IT/개발",
        "의료/바이오",
        "디자인",
        "마케팅",
        "영업·고객상담",
        "교육",
        "운전/운송/배송",
        "건축/시설",
        "사무·총무",
        "기타",
    }

    # 이미 JOBPICK 표준 카테고리가 있으면 그대로 사용
    for value in values:
        cleaned = clean_text(
            value
        )

        if cleaned in known_categories:
            return cleaned

    # 기타 원본 카테고리 값이 하나라도 있으면 첫 번째 사용
    if values:
        return clean_text(
            values[0]
        )

    # 마지막 fallback
    features = (
        extract_dictionary_features(
            job_text
        )
    )

    categories = (
        unique_preserve_order(
            features.get(
                "categories",
                [],
            )
        )
    )

    for category in categories:
        if (
            category
            in known_categories
        ):
            return category

    return (
        clean_text(
            categories[0]
        )
        if categories
        else ""
    )


def infer_ncs_category_from_job(category: str, job_text: str) -> str:
    category_text = clean_text(category).lower()
    full_text = clean_text(f"{category} {job_text}").lower()

    exclude_keywords = [
        "하드웨어",
        "설치",
        "설치as",
        "a/s",
        "as 담당",
        "장비",
        "점검",
        "유지보수",
        "키오스크",
        "빔프로젝터",
        "센서",
        "전기",
        "전자",
        "통신",
        "현장",
        "운전",
        "차량",
        "납품",
        "출장",
        "고객 방문",
        "방문 설치",
    ]

    if any(keyword in full_text for keyword in exclude_keywords):
        return ""

    direct_development_keywords = [
        "웹개발",
        "웹 개발",
        "프론트엔드",
        "프론트 개발",
        "백엔드",
        "서버개발",
        "서버 개발",
        "api 개발",
        "소프트웨어 개발",
        "sw 개발",
        "응용sw",
        "응용 sw",
        "응용소프트웨어",
        "응용 소프트웨어",
        "프로그래머",
        "개발자",
        "개발 직무",
        "개발 업무",
        "프로그램 개발",
        "애플리케이션 개발",
        "어플리케이션 개발",
    ]

    if any(keyword in full_text for keyword in direct_development_keywords):
        return "IT/개발"

    tech_stack_keywords = [
        "python",
        "java",
        "javascript",
        "typescript",
        "react",
        "next.js",
        "nextjs",
        "node.js",
        "nodejs",
        "spring",
        "spring boot",
        "django",
        "flask",
        "sql",
        "mysql",
        "postgresql",
        "oracle",
        "firebase",
        "프로그래밍",
        "코딩",
        "소스코드",
        "소스 코드",
        "github",
        "git",
    ]

    if any(keyword in full_text for keyword in tech_stack_keywords):
        return "IT/개발"

    if "서버/인프라" in category_text:
        return ""

    if "하드웨어/설치as" in category_text:
        return ""

    return ""


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
    explicit_certifications = unique_preserve_order(
        requirements.get("certifications", []) or []
    )

    # [기존 방식]
    # required_quals = as_list(requirements.get("requiredQualifications", []))
    # preferred_quals = as_list(requirements.get("preferredQualifications", []))

    # [새 방식]
    # 공공기관 API 자격요건 문장의 쉼표를 조건 구분자로 오인하지 않는다.
    required_quals = as_qualification_list(requirements.get("requiredQualifications", []))
    preferred_quals = as_qualification_list(requirements.get("preferredQualifications", []))

    responsibilities = unique_preserve_order(job.get("responsibilities", []))

    job_text_for_dictionary = clean_text(" ".join([
        safe_str(job.get("title", "")),
        safe_str(job.get("job", {})),
        safe_str(required_skills),
        safe_str(preferred_skills),
        safe_str(required_quals),
        safe_str(preferred_quals),
        safe_str(explicit_certifications),
        safe_str(responsibilities),
        safe_str(job.get("embeddingText", {})),
    ]))

    dictionary_features = extract_dictionary_features(job_text_for_dictionary)

    required_skills = unique_preserve_order(required_skills)

    # 사전에서 발견된 자격증명은 의미 분석/디버깅용 신호일 뿐이다.
    # 여러 직종의 문장을 합친 공고에서는 다른 직종의 자격증까지 잡힐 수 있으므로
    # 이를 자동으로 '필수 자격증' 목록에 승격하지 않는다.
    inferred_certifications = unique_preserve_order(
        dictionary_features.get("certifications", [])
    )
    certifications = explicit_certifications

    job_category = extract_job_category(firebase_job_doc, job, job_text_for_dictionary)
    ncs_category = infer_ncs_category_from_job(job_category, job_text_for_dictionary)
    ncs_info = job.get("ncs", {}) or {}

    return {
        # 복수 직종 공고 분리에서 제목을 함께 사용해야 하므로 보존한다.
        "title": clean_text(job.get("title", "")),
        "skills": {
            "required": required_skills,
            "preferred": preferred_skills,
        },
        "responsibilities": responsibilities,
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
        "inferredCertifications": inferred_certifications,
        "dictionaryFeatures": dictionary_features,
        "category": job_category,
        "ncsCategory": ncs_category,
        "ncsCodes": as_list(ncs_info.get("codes", [])),
        "ncsNames": as_list(ncs_info.get("names", [])),
    }


def get_resume_embedding_text(firebase_resume_doc: Dict[str, Any]) -> str:
    resume_root = firebase_resume_doc.get("resume", firebase_resume_doc) or {}
    data = resume_root.get("resumeData", resume_root) or {}
    embedding = data.get("embeddingText", {}) or {}

    if embedding.get("fullForEmbedding"):
        return prepare_semantic_text(embedding.get("fullForEmbedding"))

    flat = flatten_resume(firebase_resume_doc)

    return prepare_semantic_text(" / ".join([
        safe_str(flat.get("education", "")),
        safe_str(flat.get("skills", [])),
        safe_str(flat.get("certifications", [])),
        safe_str(flat.get("projects", [])),
    ]))


def get_job_embedding_text(firebase_job_doc: Dict[str, Any]) -> str:
    job = firebase_job_doc.get("jobPosting", firebase_job_doc) or {}
    embedding = job.get("embeddingText", {}) or {}

    if embedding.get("fullForEmbedding"):
        return prepare_semantic_text(embedding.get("fullForEmbedding"))

    flat = flatten_job(firebase_job_doc)

    return prepare_semantic_text(" / ".join([
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
    return prepare_semantic_text(" / ".join([
        safe_str(resume.get("education", "")),
        safe_str(resume.get("skills", [])),
        safe_str(resume.get("certifications", [])),
        safe_str(resume.get("projects", [])),
    ]))


def build_job_full_text(job: Dict[str, Any]) -> str:
    return prepare_semantic_text(" / ".join([
        safe_str(job.get("education", "")),
        safe_str(job.get("experience", {})),
        safe_str(job.get("skills", {})),
        safe_str(job.get("responsibilities", [])),
        safe_str(job.get("qualifications", {})),
        safe_str(job.get("certifications", [])),
    ]))



# ------------------------------------------------------------------
# 복수 직종 통합공고의 자격요건을 지원자에게 가장 관련 있는 직종으로 한정
# ------------------------------------------------------------------
ROLE_SCOPE_LABEL_NOISE = {
    "정규직", "계약직", "비정규직", "기간제", "무기계약직",
    "상근직", "비상근직", "상근", "비상근", "신입", "경력",
    "육아휴직대체", "휴직대체", "대체", "대체인력",
    "직원", "채용", "모집", "공개채용", "분야", "직종", "직무",
    "일반", "지원", "지원분야", "지원 분야",
}

ROLE_SCOPE_GENERIC_LABELS = {
    "지원자격", "응시자격", "자격요건", "필수자격", "필수자격요건",
    "필수요건", "필수조건", "공통자격", "공통자격요건", "공통요건",
    "우대사항", "우대요건", "기타", "공통", "자격", "요건",
}

ROLE_SCOPE_ROOT_TERMS = {
    "간호", "간호사", "간호직", "간호조무사", "보험심사", "조리", "조리사",
    "취사", "취사원", "사무", "사무보조", "사무보조원", "행정",
    "전산", "전산행정", "운전", "운전원", "기술", "기술직",
    "연구", "연구원", "연구직", "교육", "강사", "교수",
    "임상", "임상병리사", "방사선사", "물리치료사", "작업치료사",
    "영양사", "약사", "의사", "치과의사", "한의사", "수의사",
    "시설", "정비", "보안", "회계", "세무", "영업", "상담",
    "개발", "개발자", "디자인", "마케팅", "생산", "품질",
}

ROLE_SCOPE_OCCUPATION_SUFFIXES = (
    "사", "원", "직", "교수", "강사", "의사", "약사", "기사",
    "기능사", "기술사", "연구원", "보조원", "운전원", "조리원",
)

# 제목의 직종명과 자격요건의 표현이 조금 달라도 같은 직종으로 묶기 위한 별칭.
# 서로 혼동되기 쉬운 '간호사'와 '간호조무사'는 일반 '간호'를 공유하지 않는다.
ROLE_SCOPE_MATCH_ALIASES = {
    "간호사": ["간호사", "간호직"],
    "간호직": ["간호직", "간호사"],
    "간호조무사": ["간호조무사", "조무사"],
    "보험심사": ["보험심사", "보험심사간호사"],
    "조리사": ["조리사", "조리", "한식조리", "양식조리"],
    "조리": ["조리", "조리사"],
    "취사원": ["취사원", "취사"],
    "취사": ["취사", "취사원"],
    "사무보조원": ["사무보조원", "사무보조"],
    "사무보조": ["사무보조", "사무보조원"],
    "운전원": ["운전원", "운전", "운전면허"],
    "운전": ["운전", "운전원", "운전면허"],
    "임상병리사": ["임상병리사"],
    "방사선사": ["방사선사"],
    "물리치료사": ["물리치료사"],
    "작업치료사": ["작업치료사"],
    "연구원": ["연구원", "연구직"],
    "연구직": ["연구직", "연구원"],
    "전산행정": ["전산행정", "전산", "정보"],
}

ROLE_SCOPE_REQUIREMENT_HINTS = {
    "자격", "자격증", "면허", "면허증", "소지", "소지자", "학위", "학사",
    "석사", "박사", "전공", "졸업", "경력", "경험", "이상", "이하",
    "필수", "우대", "가능", "요건", "조건",
}


def get_role_label_terms(label: Any) -> List[str]:
    """직종 라벨에서 고용형태 같은 표현을 제거하고 실제 직종 단어만 남긴다."""
    text = clean_text(label).lower()

    if not text:
        return []

    text = re.sub(r"[()\[\]{}_/\\]+", " ", text)
    tokens = re.findall(r"[가-힣A-Za-z0-9+#.]+", text)

    result = []

    for token in tokens:
        token = clean_text(token).lower()

        if not token or token in ROLE_SCOPE_LABEL_NOISE:
            continue

        if len(normalize_qualification_match_text(token)) < 2:
            continue

        result.append(token)

    return unique_preserve_order(result)


def get_role_match_aliases(role: Any) -> List[str]:
    role_text = clean_text(role).lower()
    aliases = [role_text]

    aliases.extend(ROLE_SCOPE_MATCH_ALIASES.get(role_text, []))

    # '정규직 간호사' 같이 들어온 라벨에서도 실제 직종 토큰의 별칭을 합친다.
    for term in get_role_label_terms(role_text):
        aliases.append(term)
        aliases.extend(ROLE_SCOPE_MATCH_ALIASES.get(term, []))

    return unique_preserve_order([
        alias for alias in aliases
        if normalize_qualification_match_text(alias)
    ])


def extract_known_role_terms(text: Any) -> List[str]:
    """문장 안에서 알려진 직종 표현을 긴 표현 우선으로 찾는다."""
    normalized = normalize_qualification_match_text(text)

    if not normalized:
        return []

    found = []

    for term in sorted(ROLE_SCOPE_ROOT_TERMS, key=len, reverse=True):
        term_normalized = normalize_qualification_match_text(term)

        if not term_normalized or term_normalized not in normalized:
            continue

        # 이미 더 긴 직종명이 잡혔으면 그 안에 포함되는 짧은 표현은 제거한다.
        if any(term_normalized in normalize_qualification_match_text(existing) for existing in found):
            continue

        found.append(term)

    return found


def is_role_like_label(label: Any) -> bool:
    """'지원자격:' 같은 일반 제목이 아니라 실제 모집 직종 라벨인지 판단한다."""
    text = clean_text(label).lower()
    compact = normalize_qualification_match_text(text)

    if not text or not compact:
        return False

    generic_compacts = {
        normalize_qualification_match_text(item)
        for item in ROLE_SCOPE_GENERIC_LABELS
    }

    if compact in generic_compacts:
        return False

    # 연구원A / 연구원B처럼 문자 suffix가 붙은 라벨도 직종으로 인정한다.
    if extract_known_role_terms(text):
        return True

    terms = get_role_label_terms(text)

    if not terms:
        return False

    for term in terms:
        if term in ROLE_SCOPE_ROOT_TERMS:
            return True

        if any(term.endswith(suffix) for suffix in ROLE_SCOPE_OCCUPATION_SUFFIXES):
            return True

        if any(hard.lower() in term for hard in HARD_QUALIFICATION_TERMS):
            return True

        if any(role.lower() in term for role in HARD_ROLE_TERMS):
            return True

    return False


def split_role_labeled_qualification(value: Any) -> Tuple[str, str, str]:
    """
    자격요건을 (직종 key, 원래 라벨, 조건 본문)으로 분리한다.

    예:
      '정규직 간호사 : 간호사 면허증 소지자'
        -> ('간호사', '정규직 간호사', '간호사 면허증 소지자')
    """
    text = clean_text(value)

    if not text:
        return "", "", ""

    match = re.match(
        r"^(.{1,60}?)\s*(?:[:：]|\s[-–—]\s)\s*(.+)$",
        text,
    )

    if not match:
        return "", "", text

    label = clean_text(match.group(1))
    body = clean_text(match.group(2))

    if not label or not body or not is_role_like_label(label):
        return "", "", text

    known_terms = extract_known_role_terms(label)
    terms = known_terms or get_role_label_terms(label)

    if not terms:
        return "", "", text

    key = "|".join(
        normalize_qualification_match_text(term)
        for term in terms
        if normalize_qualification_match_text(term)
    )

    return key, label, body


def is_standalone_role_header(value: Any) -> bool:
    """
    '계약직 연구원A(인력지원교육팀'처럼 조건이 아니라 모집분야 제목만
    별도 줄로 들어온 값을 감지한다. 이런 줄은 자격요건 자체로 점수화하지 않는다.
    """
    text = clean_text(value)

    if not text or len(text) > 100:
        return False

    if not extract_known_role_terms(text):
        return False

    normalized = normalize_qualification_match_text(text)

    # 실제 조건 문장은 header가 아니다.
    if any(normalize_qualification_match_text(hint) in normalized for hint in ROLE_SCOPE_REQUIREMENT_HINTS):
        return False

    # 팀/센터/부서 또는 고용형태가 같이 있으면 standalone 모집분야일 가능성이 높다.
    header_markers = [
        "팀", "센터", "부서", "실", "본부",
        "정규직", "계약직", "비정규직", "기간제", "직원",
    ]

    return any(marker in text for marker in header_markers)


def make_standalone_role_header_key(value: Any) -> Tuple[str, str]:
    text = clean_text(value)

    if not is_standalone_role_header(text):
        return "", ""

    return f"header:{normalize_qualification_match_text(text)}", text


def extract_title_role_candidates(title: Any) -> List[str]:
    """
    통합공고 제목에서 서로 다른 모집 직종 후보를 추출한다.

    짧은 상위개념('사무', '조리', '간호')보다 제목에 실제로 등장한
    구체 직종('사무보조원', '조리사', '간호사')을 우선한다.
    """
    title_text = clean_text(title)

    if not title_text:
        return []

    candidates = extract_known_role_terms(title_text)

    # 너무 일반적인 루트는 구체 직종이 함께 있으면 제외한다.
    generic_roots = {"간호", "조리", "취사", "사무", "운전", "기술", "연구", "임상", "개발"}
    result = []

    for candidate in candidates:
        candidate_norm = normalize_qualification_match_text(candidate)

        if candidate in generic_roots:
            if any(
                candidate_norm in normalize_qualification_match_text(other)
                and candidate_norm != normalize_qualification_match_text(other)
                for other in candidates
            ):
                continue

        result.append(candidate)

    return unique_preserve_order(result)


def qualification_role_match_score(qualification: Any, role: Any) -> float:
    """자격요건 한 문장이 특정 직종에 얼마나 직접 연결되는지 계산한다."""
    q_norm = normalize_qualification_match_text(qualification)

    if not q_norm:
        return 0.0

    score = 0.0

    for alias in get_role_match_aliases(role):
        alias_norm = normalize_qualification_match_text(alias)

        if alias_norm and alias_norm in q_norm:
            score = max(score, 10.0 + min(len(alias_norm), 8) * 0.1)

    # 자격/면허 명칭이 직종명과 일치하는 경우 추가 근거.
    hard_terms = extract_hard_qualification_terms(qualification)
    role_norm = normalize_qualification_match_text(role)

    for hard_term in hard_terms:
        hard_norm = normalize_qualification_match_text(hard_term)
        if hard_norm and (
            hard_norm == role_norm
            or hard_norm in role_norm
            or role_norm in hard_norm
        ):
            score += 6.0

    return score


def build_resume_role_scope_text(resume: Dict[str, Any]) -> str:
    return clean_text(" ".join([
        safe_str(resume.get("certifications", [])),
        safe_str(resume.get("projects", [])),
        safe_str(resume.get("skills", [])),
        safe_str(resume.get("education", "")),
    ])).lower()


def score_role_group_for_resume(
    role_label: str,
    qualifications: List[str],
    resume: Dict[str, Any],
) -> float:
    """직종 그룹과 이력서 사이의 직접적인 근거 강도를 계산한다."""
    resume_text = build_resume_role_scope_text(resume)
    normalized_resume = normalize_qualification_match_text(resume_text)
    score = 0.0

    # 1) 직종 라벨 자체/별칭이 이력서에 직접 존재하는지 확인
    for alias in get_role_match_aliases(role_label):
        normalized_alias = normalize_qualification_match_text(alias)

        if normalized_alias and normalized_alias in normalized_resume:
            score += 6.0

    # 2) 직종 라벨의 사전 토큰과 이력서 토큰의 교집합
    label_features = extract_dictionary_features(role_label)
    resume_features = extract_dictionary_features(resume_text)

    label_tokens = set()
    resume_tokens = set()

    for feature_key in ["skills", "certifications", "requirements", "categories", "tasks"]:
        label_tokens.update(label_features.get(feature_key, []))
        resume_tokens.update(resume_features.get(feature_key, []))

    score += min(len(label_tokens & resume_tokens), 3) * 2.0

    # 3) 해당 직종의 필수 자격/면허가 실제 이력서에 있는지 확인
    for qualification in qualifications:
        hard_terms = extract_hard_qualification_terms(qualification)

        for hard_term in hard_terms:
            if qualification_term_in_resume(
                hard_term,
                resume_text,
                resume.get("certifications", []),
            ):
                score += 8.0

        field_used, field_matched, _ = experience_field_groups_match(
            qualification,
            resume,
        )

        if field_used and field_matched:
            score += 3.0

        # 4) '간호학', '보험심사', '전산'처럼 자격요건 본문에 있는 직종 루트가
        # 이력서에도 직접 나타나는지 본다. 연구원 A/B처럼 라벨 자체가 비슷한 경우에 유용하다.
        q_norm = normalize_qualification_match_text(qualification)
        for root in extract_known_role_terms(qualification):
            root_norm = normalize_qualification_match_text(root)
            if root_norm and root_norm in normalized_resume and root_norm in q_norm:
                score += 4.0

    return score


def is_explicit_common_qualification(value: Any) -> bool:
    text = clean_text(value)
    normalized = normalize_qualification_match_text(text)

    common_markers = [
        "공통", "공통자격", "공통요건", "공통자격요건",
        "전직종", "전 직종", "모든직종", "모든 직종",
    ]

    return any(normalize_qualification_match_text(marker) in normalized for marker in common_markers)


def build_sequential_role_groups(required: List[str]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """라벨형 조건과 standalone 모집분야 header를 이용해 순서 기반 그룹을 만든다."""
    groups: Dict[str, Dict[str, Any]] = {}
    common = []
    current_header_key = ""

    for qualification in required:
        if is_explicit_common_qualification(qualification):
            common.append(qualification)
            continue

        key, label, _ = split_role_labeled_qualification(qualification)

        if key:
            group = groups.setdefault(key, {
                "key": key,
                "label": label,
                "qualifications": [],
                "source": "labeled_qualification",
            })
            group["qualifications"].append(qualification)
            current_header_key = key
            continue

        header_key, header_label = make_standalone_role_header_key(qualification)

        if header_key:
            groups.setdefault(header_key, {
                "key": header_key,
                "label": header_label,
                "qualifications": [],
                "source": "standalone_header",
            })
            current_header_key = header_key
            # header 자체는 자격요건이 아니므로 점수화 목록에는 넣지 않는다.
            continue

        if current_header_key and current_header_key in groups:
            groups[current_header_key]["qualifications"].append(qualification)

    # 실제 조건이 하나도 없는 빈 header 그룹은 제거한다.
    groups = {
        key: group for key, group in groups.items()
        if group.get("qualifications")
    }

    return groups, unique_preserve_order(common)


def build_title_role_groups(
    required: List[str],
    title: str,
) -> Tuple[Dict[str, Dict[str, Any]], List[str], List[str]]:
    """
    라벨 구조가 없는 통합공고(영주적십자병원 유형)를 위해 제목의 직종 후보를
    기준으로 자격요건을 귀속시킨다.
    """
    candidates = extract_title_role_candidates(title)
    groups: Dict[str, Dict[str, Any]] = {
        f"title:{normalize_qualification_match_text(role)}": {
            "key": f"title:{normalize_qualification_match_text(role)}",
            "label": role,
            "qualifications": [],
            "source": "title_inference",
        }
        for role in candidates
    }
    common = []
    unassigned = []

    if len(candidates) < 2:
        return {}, common, required

    for qualification in required:
        if is_standalone_role_header(qualification):
            # 제목 기반 fallback에서는 header 문장을 자격조건으로 쓰지 않는다.
            continue

        if is_explicit_common_qualification(qualification):
            common.append(qualification)
            continue

        scored = []
        for role in candidates:
            score = qualification_role_match_score(qualification, role)
            scored.append((score, role))

        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_role = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else -1.0

        # 직종명이 직접 드러나는 경우에만 귀속한다. 애매한 문장은 억지로 배정하지 않는다.
        if best_score >= 10.0 and best_score > second_score:
            key = f"title:{normalize_qualification_match_text(best_role)}"
            groups[key]["qualifications"].append(qualification)
        else:
            unassigned.append(qualification)

    groups = {
        key: group for key, group in groups.items()
        if group.get("qualifications")
    }

    return groups, unique_preserve_order(common), unique_preserve_order(unassigned)


def filter_certifications_for_scoped_qualifications(
    certifications: List[Any],
    scoped_required_quals: List[str],
) -> List[str]:
    """선택 직종의 자격요건에 실제 등장하는 자격증만 전역 자격증 목록에서 남긴다."""
    selected_text = normalize_qualification_match_text(" ".join(scoped_required_quals))

    if not selected_text:
        return []

    result = []

    for cert in as_list(certifications):
        cert_text = clean_text(cert)
        cert_normalized = normalize_qualification_match_text(cert_text)

        if cert_normalized and cert_normalized in selected_text:
            result.append(cert_text)
            continue

        # '간호사 면허증' vs '간호사'처럼 표현 차이가 있는 경우 hard term으로 확인한다.
        for qualification in scoped_required_quals:
            hard_terms = extract_hard_qualification_terms(qualification)
            if any(
                normalize_qualification_match_text(term)
                and normalize_qualification_match_text(term) in cert_normalized
                for term in hard_terms
            ):
                result.append(cert_text)
                break

    return unique_preserve_order(result)


def job_has_multi_role_signals(job: Dict[str, Any]) -> bool:
    """제목/자격요건에 서로 다른 모집직종이 둘 이상 섞였는지 보수적으로 확인한다."""
    title = clean_text(job.get("title", ""))
    required = as_qualification_list((job.get("qualifications", {}) or {}).get("required", []))

    role_signals = []
    role_signals.extend(extract_title_role_candidates(title))

    for qualification in required:
        role_signals.extend(extract_known_role_terms(qualification))
        key, label, _ = split_role_labeled_qualification(qualification)
        if key:
            role_signals.append(label or key)

    normalized = unique_preserve_order([
        normalize_qualification_match_text(item)
        for item in role_signals
        if normalize_qualification_match_text(item)
    ])

    return len(normalized) >= 2


def scope_certifications_for_scoring(
    job: Dict[str, Any],
    role_scope_info: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    필수 자격증을 실제로 어느 직종에 적용할 수 있는지 확인한다.

    - 직종이 성공적으로 선택된 경우: 이미 선택 직종 자격요건에 등장하는 자격증만 남김
    - 단일 직종 공고: 명시적 certifications를 그대로 사용
    - 복수 직종인데 직종 귀속을 못 한 경우: 다른 직종 자격증으로 오판하지 않도록
      명시적 공통 자격증만 남기고, 공통 여부도 확인할 수 없으면 자격증 룰 점수를 보류
    """
    result_job = dict(job)
    certifications = unique_preserve_order(as_list(job.get("certifications", [])))
    required = as_qualification_list((job.get("qualifications", {}) or {}).get("required", []))

    info = {
        "originalCount": len(certifications),
        "scopedCount": len(certifications),
        "skippedAmbiguous": False,
        "reason": "",
    }

    if not certifications:
        info["reason"] = "명시적으로 구조화된 필수 자격증이 없습니다."
        return result_job, info

    if role_scope_info.get("applied"):
        # scope_job_to_resume_role()에서 이미 선택 직종 조건에 맞춰 필터링됨.
        scoped = unique_preserve_order(as_list(result_job.get("certifications", [])))
        info["scopedCount"] = len(scoped)
        info["reason"] = "선택된 모집직종의 자격요건에 직접 연결되는 자격증만 평가합니다."
        return result_job, info

    if not job_has_multi_role_signals(job):
        info["reason"] = "단일 직종 공고로 판단되어 명시적 필수 자격증을 그대로 평가합니다."
        return result_job, info

    common_required = [
        qualification
        for qualification in required
        if is_explicit_common_qualification(qualification)
    ]
    common_certs = filter_certifications_for_scoped_qualifications(
        certifications,
        common_required,
    )

    if common_certs:
        result_job["certifications"] = common_certs
        info["scopedCount"] = len(common_certs)
        info["reason"] = "복수 직종 공고에서 명시적 공통 자격요건에 연결되는 자격증만 평가합니다."
        return result_job, info

    # 어느 직종의 자격증인지 확인할 수 없으면 '모두 필수'로 간주하지 않는다.
    result_job["certifications"] = []
    info["scopedCount"] = 0
    info["skippedAmbiguous"] = True
    info["reason"] = (
        "복수 직종 공고의 자격증이 어느 모집직종에 속하는지 확인할 수 없어 "
        "필수 자격증 점수에서 제외했습니다."
    )
    return result_job, info


def scope_job_to_resume_role(
    job: Dict[str, Any],
    resume: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    복수 직종 통합공고에서 지원자의 이력서와 가장 직접적으로 연결되는 한 직종의
    조건만 평가한다.

    처리 순서:
    1) '간호사 : ...' 또는 standalone 모집분야 header로 그룹화
    2) 위 구조가 부족하면 공고 제목의 여러 직종을 이용해 자격요건을 귀속
    3) 지원자와 직접 연결되는 근거가 가장 강한 그룹 하나만 선택

    안전장치:
    - 그룹이 2개 미만이면 적용하지 않음
    - 최고 점수가 0이면 적용하지 않음
    - 최고 점수가 동점이면 임의 선택하지 않음
    - 제목 기반 추론에서 직종 귀속이 안 된 문장은 자동으로 다른 직종 조건에 넣지 않음
    """
    qualifications = job.get("qualifications", {}) or {}
    required = as_qualification_list(qualifications.get("required", []))
    preferred = as_qualification_list(qualifications.get("preferred", []))
    title = clean_text(job.get("title", ""))

    groups, common_required = build_sequential_role_groups(required)
    source = "qualification_structure"
    unassigned_required = []

    # 라벨/헤더 구조만으로 두 직종 이상이 안 잡히면 제목을 사용한다.
    if len(groups) < 2:
        title_groups, title_common, title_unassigned = build_title_role_groups(required, title)

        if len(title_groups) >= 2:
            groups = title_groups
            common_required = title_common
            unassigned_required = title_unassigned
            source = "title_inference"

    info = {
        "applied": False,
        "source": source,
        "title": title,
        "selectedRole": "",
        "selectedRoleKey": "",
        "candidateRoleCount": len(groups),
        "originalQualificationCount": len(required),
        "scopedQualificationCount": len(required),
        "originalCertificationCount": len(as_list(job.get("certifications", []))),
        "scopedCertificationCount": len(as_list(job.get("certifications", []))),
        "unassignedQualificationCount": len(unassigned_required),
        "reason": "",
    }

    if len(groups) < 2:
        if title and len(extract_title_role_candidates(title)) >= 2:
            info["reason"] = "제목에는 복수 직종이 있으나 직종별 자격요건을 두 그룹 이상 연결하지 못했습니다."
        else:
            info["reason"] = "직종별로 분리 가능한 자격요건이 2개 이상 확인되지 않았습니다."
        return job, info

    scored_groups = []

    for key, group in groups.items():
        group_score = score_role_group_for_resume(
            group["label"],
            group["qualifications"],
            resume,
        )
        scored_groups.append((group_score, key, group))

    scored_groups.sort(key=lambda item: item[0], reverse=True)

    best_score, best_key, best_group = scored_groups[0]
    second_score = scored_groups[1][0] if len(scored_groups) > 1 else -1.0

    if best_score <= 0:
        info["reason"] = "이력서와 직접 연결되는 직종 근거를 찾지 못했습니다."
        return job, info

    if abs(best_score - second_score) < 1e-9:
        info["reason"] = "복수 직종의 관련도 점수가 같아 임의로 직종을 선택하지 않았습니다."
        return job, info

    scoped_required = unique_preserve_order([
        *best_group.get("qualifications", []),
        *common_required,
    ])

    if not scoped_required:
        info["reason"] = "선택 직종의 필수 자격요건을 분리하지 못했습니다."
        return job, info

    # preferred는 선택 직종명이 직접 나타나는 것 + 명시적 공통 우대만 남긴다.
    scoped_preferred = []
    for item in preferred:
        if is_explicit_common_qualification(item):
            scoped_preferred.append(clean_text(item))
            continue

        if qualification_role_match_score(item, best_group["label"]) >= 10.0:
            scoped_preferred.append(clean_text(item))

    scoped_job = dict(job)
    scoped_job["qualifications"] = {
        **qualifications,
        "required": scoped_required,
        "preferred": unique_preserve_order(scoped_preferred),
    }

    scoped_certs = filter_certifications_for_scoped_qualifications(
        job.get("certifications", []),
        scoped_required,
    )
    scoped_job["certifications"] = scoped_certs

    info.update({
        "applied": True,
        "selectedRole": best_group["label"],
        "selectedRoleKey": best_key,
        "scopedQualificationCount": len(scoped_required),
        "scopedCertificationCount": len(scoped_certs),
        "reason": (
            "공고 제목과 자격요건 구조를 함께 사용해 복수 직종 중 "
            "이력서와 가장 관련 있는 직종의 조건만 평가했습니다."
        ),
    })

    return scoped_job, info


def prepare_job_score_context(
    job: Dict[str, Any],
    resume: Dict[str, Any],
) -> Dict[str, Any]:
    """
    calculate_full_score()에서 실제 사용하는 공고 상태를 한 번만 준비한다.

    기존 calculate_full_score()의 순서와 동일하게:
    1) 복수 직종 scope
    2) 자격증 scope
    3) scope 완료된 공고 기준 semantic text 생성

    반환된 context는 preload와 calculate_full_score()가 함께 재사용한다.
    점수 공식이나 조건 판정 방식은 변경하지 않는다.
    """
    total_start = time.perf_counter()

    original_required_quals = (
        (job.get("qualifications", {}) or {}).get("required", [])
    )

    role_start = time.perf_counter()
    scoped_job, role_scope_info = scope_job_to_resume_role(
        job,
        resume,
    )
    role_scope_elapsed = time.perf_counter() - role_start

    cert_start = time.perf_counter()
    scoped_job, certification_scope_info = scope_certifications_for_scoring(
        scoped_job,
        role_scope_info,
    )
    certification_scope_elapsed = time.perf_counter() - cert_start

    role_scope_info = dict(role_scope_info or {})
    certification_scope_info = dict(certification_scope_info or {})
    role_scope_info["certificationScope"] = certification_scope_info

    semantic_start = time.perf_counter()
    semantic_texts = get_score_semantic_texts(
        scoped_job,
        resume,
    )
    semantic_text_elapsed = time.perf_counter() - semantic_start

    return {
        "job": scoped_job,
        "original_required_quals": original_required_quals,
        "role_scope_info": role_scope_info,
        "certification_scope_info": certification_scope_info,
        "semantic_texts": semantic_texts,
        "timings": {
            "role_scope": role_scope_elapsed,
            "certification_scope": certification_scope_elapsed,
            "semantic_text_prepare": semantic_text_elapsed,
            "total": time.perf_counter() - total_start,
        },
    }


def preload_prepared_score_embeddings(
    prepared_contexts: List[Dict[str, Any]],
    batch_size: int = 32,
    extra_similarity_texts: List[str] | None = None,
):
    """
    prepare_job_score_context()에서 만든 '실제 최종 비교 텍스트'만 preload한다.

    기존 preload_score_embeddings()는 scope 이전 공고 텍스트를 기준으로
    preload할 수 있어, 실제 calculate_full_score()에서 다시 encode가 발생할 수 있었다.

    이 함수는 실제 점수 계산에서 쓰일 semantic_texts를 그대로 사용하므로
    preload와 정밀 계산의 입력을 일치시킨다.
    """
    texts = []
    seen = set()

    def collect_similarity_text(text):
        cache_key = get_similarity_cache_key(text)

        if not cache_key:
            return

        if cache_key in seen or cache_key in _embedding_cache:
            return

        if get_vector(cache_key) is not None:
            return

        seen.add(cache_key)
        texts.append(cache_key)

    for context in prepared_contexts or []:
        semantic_texts = context.get("semantic_texts", ()) or ()

        for text in semantic_texts:
            collect_similarity_text(text)

    for text in extra_similarity_texts or []:
        collect_similarity_text(text)

    if not texts:
        return {
            "encodedCount": 0,
            "cacheCount": len(_embedding_cache),
        }

    embeddings = get_model().encode(
        texts,
        convert_to_tensor=True,
        batch_size=batch_size,
        show_progress_bar=False,
    )

    for text, embedding in zip(texts, embeddings):
        _embedding_cache[text] = embedding

    while len(_embedding_cache) > EMBEDDING_CACHE_LIMIT:
        _embedding_cache.popitem(last=False)

    return {
        "encodedCount": len(texts),
        "cacheCount": len(_embedding_cache),
    }

def calculate_accessibility_score(
    skill_used: bool,
    skill_match_count: int,
    skill_total_count: int,
    edu_used: bool,
    edu_score_raw: float,
    exp_detail: Dict[str, Any],
    cert_used: bool,
    cert_match_count: int,
    cert_total_count: int,
    qual_used: bool,
    qual_rule_score_raw: float,
) -> float:
    """
    지원 가능성은 '공고에서 실제로 확인된 필수조건'만 기준으로 계산한다.

    기존 방식은 조건이 없을 때도 해당 항목의 배점을 자동으로 모두 더해
    룰 근거가 하나도 없는 공고가 accessibility=100이 되는 문제가 있었다.

    새 방식:
    - 실제 존재하는 조건만 분모/분자에 포함
    - 확인 가능한 필수조건이 하나도 없으면 100이 아니라 중립값 50 반환
    - 따라서 '조건을 찾지 못함'과 '조건을 모두 충족함'을 구분
    """
    weighted_scores = []

    # 경력: 30
    if exp_detail.get("exp_condition_used", False):
        min_exp = float(exp_detail.get("min_exp", 0) or 0)
        resume_exp = float(exp_detail.get("resume_exp", 0) or 0)

        if min_exp > 0:
            ratio = max(0.0, min(resume_exp / min_exp, 1.0))
            weighted_scores.append((30.0, ratio))

    # 학력: 20
    if edu_used:
        weighted_scores.append((20.0, 1.0 if edu_score_raw >= 10 else 0.0))

    # 필수 기술: 20
    if skill_used and skill_total_count > 0:
        ratio = max(0.0, min(skill_match_count / skill_total_count, 1.0))
        weighted_scores.append((20.0, ratio))

    # 필수 자격증: 15
    if cert_used and cert_total_count > 0:
        ratio = max(0.0, min(cert_match_count / cert_total_count, 1.0))
        weighted_scores.append((15.0, ratio))

    # 필수 자격요건: 15
    if qual_used:
        weighted_scores.append((15.0, get_score_ratio(qual_rule_score_raw, 10)))

    # 확인할 수 있는 필수조건이 하나도 없으면 '모두 충족'이 아니라 '판단 보류'.
    if not weighted_scores:
        return 50.0

    total_weight = sum(weight for weight, _ in weighted_scores)
    earned = sum(weight * ratio for weight, ratio in weighted_scores)

    if total_weight <= 0:
        return 50.0

    return round(max(0.0, min((earned / total_weight) * 100.0, 100.0)), 2)


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


def count_rule_evidence_groups(
    skill_used: bool,
    skill_total_count: int,
    edu_used: bool,
    exp_detail: Dict[str, Any],
    cert_used: bool,
    cert_total_count: int,
    qual_used: bool,
    qual_total_count: int,
) -> int:
    count = 0

    if skill_used and skill_total_count > 0:
        count += 1

    if edu_used:
        count += 1

    if exp_detail.get("exp_condition_used", False):
        count += 1

    if cert_used and cert_total_count > 0:
        count += 1

    if qual_used and qual_total_count > 0:
        count += 1

    return count


def should_try_ncs_score(rule_evidence_count: int) -> bool:
    return rule_evidence_count < 2

NCS_SAFE_CATEGORIES = {
    "IT/개발",
    "의료/바이오",
    "디자인",
    "마케팅",
    "영업·고객상담",
    "교육",
    "운전/운송/배송",
    "건축/시설",
    "사무·총무",
}


def get_safe_ncs_category(
    job: Dict[str, Any],
) -> str:
    """
    NCS 보완 평가에 사용할 카테고리.

    '기타'처럼 직무 범위가 불명확한 공고에서는
    NCS 전체 후보 중 우연히 비슷한 능력단위를 고르는 것을 막는다.
    """

    inferred_category = clean_text(
        job.get(
            "ncsCategory",
            "",
        )
    )

    if (
        inferred_category
        in NCS_SAFE_CATEGORIES
    ):
        return inferred_category

    job_category = clean_text(
        job.get(
            "category",
            "",
        )
    )

    if (
        job_category
        in NCS_SAFE_CATEGORIES
    ):
        return job_category

    return ""


def build_ncs_not_applied_result(reason: str) -> Dict[str, Any]:
    return {
        "ncs_used": False,
        "ncs_category": "",
        "ncs_score": 0.0,
        "ncs_score_max": 0.0,
        "ncs_similarity": 0.0,
        "matched_duty_cd": "",
        "matched_duty_name": "",
        "matched_unit_cd": "",
        "matched_unit_name": "",
        "reason": reason,
    }


def get_rule_component_weights(
    rule_total_max: float,
    skill_used: bool,
    edu_used: bool,
    exp_used: bool,
    cert_used: bool,
    qual_used: bool,
) -> Dict[str, float]:
    """
    공고에 실제로 존재하는 룰 항목만 대상으로 rule_total_max를 재분배한다.

    기본 중요도는 다음 비율을 유지한다.
    - 기술 스택: 40%
    - 학력: 10%
    - 경력: 20%
    - 자격증: 10%
    - 필수 자격요건: 20%

    예:
    - 필수 자격요건만 존재 + rule_total_max=15
      -> qual 15점
    - 기술/경력/필수 자격요건 존재 + rule_total_max=30
      -> 40:20:20 = 15:7.5:7.5점

    조건이 없는 항목은 최대 배점도 0점으로 처리한다.
    """
    base_ratios = {
        "skill": RULE_SKILL_RATIO,
        "edu": RULE_EDU_RATIO,
        "exp": RULE_EXP_RATIO,
        "cert": RULE_CERT_RATIO,
        "qual": RULE_QUAL_RATIO,
    }

    used_map = {
        "skill": bool(skill_used),
        "edu": bool(edu_used),
        "exp": bool(exp_used),
        "cert": bool(cert_used),
        "qual": bool(qual_used),
    }

    active_ratio_sum = sum(
        base_ratios[key]
        for key, is_used in used_map.items()
        if is_used
    )

    if rule_total_max <= 0 or active_ratio_sum <= 0:
        return {
            "skill": 0.0,
            "edu": 0.0,
            "exp": 0.0,
            "cert": 0.0,
            "qual": 0.0,
        }

    return {
        key: (
            rule_total_max * (base_ratios[key] / active_ratio_sum)
            if used_map[key]
            else 0.0
        )
        for key in base_ratios
    }


def has_meaningful_responsibilities(job: Dict[str, Any]) -> bool:
    """
    담당업무가 실제 직무 설명으로서 의미 있는지 판단한다.

    JOB-ALIO API 공고의 경우 별도 담당업무가 없어
    responsibilities에 NCS 대분류명만 들어갈 수 있다.
    이 경우에는 '담당업무 의미 유사도' 평가에서 제외한다.
    """
    responsibilities = unique_preserve_order(as_list(job.get("responsibilities", [])))

    if not responsibilities:
        return False

    ncs_names = {
        clean_text(name).lower()
        for name in as_list(job.get("ncsNames", []))
        if clean_text(name)
    }

    category = clean_text(job.get("category", "")).lower()

    meaningful_items = []

    for item in responsibilities:
        normalized = clean_text(item).lower()

        if not normalized:
            continue

        # JOB-ALIO의 NCS 대분류명만 responsibilities에 들어간 경우
        # 실제 담당업무 설명으로 보지 않는다.
        if normalized in ncs_names:
            continue

        # 카테고리명 하나만 담당업무처럼 들어간 경우도 제외한다.
        if category and normalized == category:
            continue

        meaningful_items.append(normalized)

    return bool(meaningful_items)


def get_semantic_component_weights(
    semantic_total_max: float,
    full_used: bool,
    resp_used: bool,
    qual_used: bool,
) -> Dict[str, float]:
    """
    실제 사용할 수 있는 의미 기반 항목끼리 semantic_total_max를 재분배한다.

    기본 중요도:
    - 공고 전체 ↔ 이력서 전체: 50%
    - 담당업무 ↔ 경험: 30%
    - 자격요건 ↔ 경험: 20%

    예:
    - 전체 + 담당업무 + 자격요건 모두 존재
      -> 35 / 21 / 14 (총 70)
    - 담당업무 없음, 전체 + 자격요건만 존재
      -> 50 / 20 (총 70)
    - 자격요건 없음, 전체 + 담당업무만 존재
      -> 43.75 / 26.25 (총 70)
    """
    base_ratios = {
        "full": FULL_SEMANTIC_RATIO,
        "resp": RESPONSIBILITY_SEMANTIC_RATIO,
        "qual": QUALIFICATION_SEMANTIC_RATIO,
    }

    used_map = {
        "full": bool(full_used),
        "resp": bool(resp_used),
        "qual": bool(qual_used),
    }

    active_ratio_sum = sum(
        base_ratios[key]
        for key, is_used in used_map.items()
        if is_used
    )

    if semantic_total_max <= 0 or active_ratio_sum <= 0:
        return {
            "full": 0.0,
            "resp": 0.0,
            "qual": 0.0,
        }

    return {
        key: (
            semantic_total_max * (base_ratios[key] / active_ratio_sum)
            if used_map[key]
            else 0.0
        )
        for key in base_ratios
    }


def get_match_badges(
    fit_score: float,
    accessibility_score: float,
    confidence_score: float,
    has_blocking_unmet: bool = False,
    has_blocking_unknown: bool = False,
    rule_evidence_count: int = 0,
    ncs_used: bool = False,
) -> List[str]:
    """
    매칭 결과에 표시할 배지를 결정한다.

    AI 적합:
    - 적합도 70점 이상
    - 판단 근거 충분도 45점 이상
    - 룰 기반 근거가 1개 이상이거나 신뢰 가능한 NCS가 사용됨

    즉, 의미 유사도만으로 70점을 넘긴 경우에는
    AI 적합 배지를 부여하지 않는다.
    """

    if has_blocking_unmet:
        return ["부적합"]

    # 필수 지원자격이 False가 아니라 None(확인 불가)인 경우에는
    # 부적합으로 단정하지 않고 정보 부족으로 표시한다.
    if has_blocking_unknown:
        return ["정보 부족"]

    if confidence_score < 40:
        return ["정보 부족"]

    # 기존 부적합 기준
    if (
        fit_score < 40
        or accessibility_score < 60
    ):
        return ["부적합"]

    badges = []

    # 객관적인 판단 근거 존재 여부
    has_objective_evidence = (
        rule_evidence_count > 0
        or ncs_used
    )

    # 의미 유사도만 높은 경우에는 AI 적합으로 올리지 않는다.
    if (
        fit_score >= 70
        and confidence_score >= 45
        and has_objective_evidence
    ):
        badges.append("AI 적합")

    if accessibility_score >= 75:
        badges.append("지원 가능")

    if not badges:
        badges.append("보통")

    return badges


def get_recommend_type(
    fit_score: float,
    accessibility_score: float,
    confidence_score: float,
    has_blocking_unmet: bool = False,
    has_blocking_unknown: bool = False,
    rule_evidence_count: int = 0,
    ncs_used: bool = False,
) -> str:
    if has_blocking_unmet:
        return "부적합"

    if has_blocking_unknown:
        return "정보 부족"

    if confidence_score < 40:
        return "정보 부족"

    badges = get_match_badges(
        fit_score=fit_score,
        accessibility_score=accessibility_score,
        confidence_score=confidence_score,
        has_blocking_unmet=has_blocking_unmet,
        has_blocking_unknown=has_blocking_unknown,
        rule_evidence_count=rule_evidence_count,
        ncs_used=ncs_used,
    )

    if "AI 적합" in badges:
        return "AI 적합"

    if "지원 가능" in badges:
        return "지원 가능"

    if "부적합" in badges:
        return "부적합"

    return "보통"


def calculate_full_score(
    job: Dict[str, Any],
    resume: Dict[str, Any],
    label: str = "매칭",
    prepared_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    full_score_total_start = time.perf_counter()

    _FULL_SCORE_PERF_STATS["calls"] = int(
        _FULL_SCORE_PERF_STATS.get("calls", 0)
    ) + 1

    print(f"\n=== {label} 계산 과정 ===")

    # 복수 직종/자격증 scope가 이미 준비되어 있으면 그대로 재사용한다.
    # prepared_context가 없을 때는 기존 경로를 그대로 실행한다.
    if prepared_context:
        job = prepared_context.get("job", job)
        original_required_quals = prepared_context.get(
            "original_required_quals",
            (job.get("qualifications", {}) or {}).get("required", []),
        )
        role_scope_info = dict(
            prepared_context.get("role_scope_info", {})
            or {}
        )
        certification_scope_info = dict(
            prepared_context.get("certification_scope_info", {})
            or {}
        )

        # 실제 scope 시간은 main_matching.py의 준비 단계에서 별도 측정한다.
        _record_full_score_perf("role_scope", 0.0)
        _record_full_score_perf("certification_scope", 0.0)
    else:
        # 복수 직종 통합공고라면 지원자의 이력서와 가장 관련 있는 직종 조건만 사용한다.
        stage_start = time.perf_counter()

        original_required_quals = (
            (job.get("qualifications", {}) or {}).get("required", [])
        )
        job, role_scope_info = scope_job_to_resume_role(job, resume)

        _record_full_score_perf(
            "role_scope",
            time.perf_counter() - stage_start,
        )

        # 필수 자격증은 사전 추출값을 자동 필수로 쓰지 않고,
        # 복수 직종 공고에서는 직종 귀속이 확인되는 경우에만 평가한다.
        stage_start = time.perf_counter()

        job, certification_scope_info = scope_certifications_for_scoring(
            job,
            role_scope_info,
        )
        role_scope_info["certificationScope"] = certification_scope_info

        _record_full_score_perf(
            "certification_scope",
            time.perf_counter() - stage_start,
        )

    if role_scope_info.get("applied"):
        print(
            f"[복수 직종 분리] 선택 직종: {role_scope_info.get('selectedRole', '')} "
            f"(자격요건 {role_scope_info.get('originalQualificationCount', 0)}개 → "
            f"{role_scope_info.get('scopedQualificationCount', 0)}개)"
        )

    stage_start = time.perf_counter()

    skill_score_raw, skill_match_count, skill_total_count, skill_used, matched_skills = calculate_skill_score(
        job.get("skills", {}), resume.get("skills", [])
    )

    _record_full_score_perf(
        "rule_skill",
        time.perf_counter() - stage_start,
    )

    stage_start = time.perf_counter()

    edu_score_raw, edu_used, job_edu_level, resume_edu_level = calculate_education_score(
        job.get("education", ""), resume.get("education", "")
    )

    _record_full_score_perf(
        "rule_education",
        time.perf_counter() - stage_start,
    )

    stage_start = time.perf_counter()

    exp_score_raw, exp_detail = calculate_experience_score(job, resume)
    exp_used = bool(exp_detail.get("exp_condition_used", True))

    _record_full_score_perf(
        "rule_experience",
        time.perf_counter() - stage_start,
    )

    stage_start = time.perf_counter()

    cert_score_raw, cert_match_count, cert_total_count, cert_used, matched_certs = calculate_certification_score(
        job.get("certifications", []), resume.get("certifications", [])
    )

    _record_full_score_perf(
        "rule_certification",
        time.perf_counter() - stage_start,
    )

    required_quals = (job.get("qualifications", {}) or {}).get("required", [])
    qual_original_count = len(as_qualification_list(original_required_quals))
    qual_scoped_count = len(as_qualification_list(required_quals))

    stage_start = time.perf_counter()

    (
        qual_rule_score_raw,
        matched_quals,
        qual_total_count,
        qual_used,
        qual_detail,
    ) = calculate_qualification_rule_score_detailed(
        required_quals, resume
    )

    _record_full_score_perf(
        "rule_qualification",
        time.perf_counter() - stage_start,
    )

    stage_start = time.perf_counter()

    eligibility_unknown = as_list(qual_detail.get("eligibility_unknown", []))
    eligibility_unmatched = as_list(qual_detail.get("eligibility_unmatched", []))

    # 확인 불가(None)는 미충족(False)과 구분한다. 지원 가능성 계산에서는
    # 확인 불가 조건을 0점이 아니라 중립(50%)으로 반영한다.
    if qual_used and qual_total_count > 0:
        qual_accessibility_score_raw = (
            (len(matched_quals) + 0.5 * len(eligibility_unknown))
            / qual_total_count
        ) * 10
    else:
        qual_accessibility_score_raw = 0.0

    unmet_conditions = []

    if skill_used and skill_match_count < skill_total_count:
        unmet_conditions.append("필수 기술 미충족")
    if edu_used and edu_score_raw < 10:
        unmet_conditions.append("학력 조건 미충족")
    if exp_detail.get("exp_condition_used", False) and exp_detail.get("resume_exp", 0) < exp_detail.get("min_exp", 0):
        unmet_conditions.append("경력 연수 미충족")
    if cert_used and cert_match_count < cert_total_count:
        unmet_conditions.append("필수 자격증 미충족")

    certification_scope_unknown = bool(
        certification_scope_info.get("skippedAmbiguous", False)
    )
    if certification_scope_unknown:
        unmet_conditions.append("필수 자격증 직종 확인 필요")

    if eligibility_unmatched:
        unmet_conditions.append("필수 지원자격 미충족")
    if eligibility_unknown:
        unmet_conditions.append("필수 지원자격 확인 필요")

    general_unmatched_qual_count = max(
        0,
        qual_total_count
        - len(matched_quals)
        - len(eligibility_unmatched)
        - len(eligibility_unknown),
    )
    if qual_used and general_unmatched_qual_count > 0:
        unmet_conditions.append("필수 자격요건 미충족")

    blocking_unmet_labels = {
        "필수 기술 미충족",
        "학력 조건 미충족",
        "경력 연수 미충족",
        "필수 자격증 미충족",
        "필수 지원자격 미충족",
        "필수 자격요건 미충족",
    }
    has_blocking_unmet = any(
        item in blocking_unmet_labels
        for item in unmet_conditions
    )
    has_blocking_unknown = bool(
        eligibility_unknown
        or certification_scope_unknown
    ) and not has_blocking_unmet

    _record_full_score_perf(
        "condition_processing",
        time.perf_counter() - stage_start,
    )

    stage_start = time.perf_counter()

    raw_resume_full_text = clean_text(" / ".join([
        safe_str(resume.get("education", "")),
        safe_str(resume.get("skills", [])),
        safe_str(resume.get("certifications", [])),
        safe_str(resume.get("projects", [])),
    ]))

    raw_job_full_text = clean_text(" / ".join([
        safe_str(job.get("category", "")),
        safe_str(job.get("education", "")),
        safe_str(job.get("experience", {})),
        safe_str(job.get("skills", {})),
        safe_str(job.get("responsibilities", [])),
        safe_str(job.get("qualifications", {})),
        safe_str(job.get("certifications", [])),
    ]))

    prepared_semantic_texts = (
        prepared_context.get("semantic_texts")
        if prepared_context
        else None
    )

    if prepared_semantic_texts:
        (
            resume_full_text,
            job_full_text,
            resume_exp_text,
            job_resp_text,
            job_qual_text,
        ) = prepared_semantic_texts
    else:
        (
            resume_full_text,
            job_full_text,
            resume_exp_text,
            job_resp_text,
            job_qual_text,
        ) = get_score_semantic_texts(job, resume)

    _record_full_score_perf(
        "semantic_text_prepare",
        time.perf_counter() - stage_start,
    )

    # ------------------------------------------------------------------
    # [기존 방식 - 고정 35/21/14 배점]
    # 실제 정보 존재 여부와 관계없이 의미 기반 70점을
    # 전체 35점 / 담당업무 21점 / 자격요건 14점으로 고정 배분했다.
    #
    # raw_full_sim, raw_full_score = calculate_semantic_score(
    #     resume_full_text,
    #     job_full_text,
    #     FULL_SEMANTIC_WEIGHT
    # ) if resume_full_text and job_full_text else (0.0, 0.0)
    #
    # raw_resp_sim, raw_resp_score = calculate_semantic_score(
    #     resume_exp_text,
    #     job_resp_text,
    #     RESPONSIBILITY_SEMANTIC_WEIGHT
    # ) if resume_exp_text and job_resp_text else (0.0, 0.0)
    #
    # raw_qual_sim, raw_qual_score = calculate_semantic_score(
    #     resume_exp_text,
    #     job_qual_text,
    #     QUALIFICATION_SEMANTIC_WEIGHT
    # ) if resume_exp_text and job_qual_text else (0.0, 0.0)
    # ------------------------------------------------------------------

    # [새 방식]
    # 먼저 각 텍스트 쌍의 순수 유사도만 계산하고,
    # 실제 배점은 scoring_mode 결정 후 사용 가능한 항목끼리 재분배한다.
    stage_start = time.perf_counter()

    raw_full_sim = (
        calculate_text_similarity(resume_full_text, job_full_text)
        if resume_full_text and job_full_text
        else 0.0
    )

    _record_full_score_perf(
        "semantic_similarity_full",
        time.perf_counter() - stage_start,
    )

    stage_start = time.perf_counter()

    raw_resp_sim = (
        calculate_text_similarity(resume_exp_text, job_resp_text)
        if resume_exp_text and job_resp_text
        else 0.0
    )

    _record_full_score_perf(
        "semantic_similarity_responsibility",
        time.perf_counter() - stage_start,
    )

    stage_start = time.perf_counter()

    raw_qual_sim = (
        calculate_text_similarity(resume_exp_text, job_qual_text)
        if resume_exp_text and job_qual_text
        else 0.0
    )

    _record_full_score_perf(
        "semantic_similarity_qualification",
        time.perf_counter() - stage_start,
    )

    stage_start = time.perf_counter()

    # 기존 응답 구조와 디버깅 값 호환을 위해
    # 고정 배점 기준의 raw score도 별도로 유지한다.
    raw_full_score = raw_full_sim * FULL_SEMANTIC_WEIGHT
    raw_resp_score = raw_resp_sim * RESPONSIBILITY_SEMANTIC_WEIGHT
    raw_qual_score = raw_qual_sim * QUALIFICATION_SEMANTIC_WEIGHT

    required_condition_ratio = calculate_required_condition_ratio(
        skill_used=skill_used,
        skill_match_count=skill_match_count,
        skill_total_count=skill_total_count,
        cert_used=cert_used,
        cert_match_count=cert_match_count,
        cert_total_count=cert_total_count,
        qual_used=qual_used,
        qual_rule_score_raw=qual_accessibility_score_raw,
        qual_total_count=qual_total_count,
    )

    semantic_adjust_ratio = 1.0

    full_sim = raw_full_sim
    resp_sim = raw_resp_sim
    qual_sim = raw_qual_sim

    # ------------------------------------------------------------------
    # [기존 방식 - 고정 배점]
    # full_score = raw_full_score
    # resp_score = raw_resp_score
    # qual_score = raw_qual_score
    # semantic_before_adjust = full_score + resp_score + qual_score
    # semantic_total = semantic_before_adjust
    # ------------------------------------------------------------------

    # [새 방식]
    # scoring_mode에서 semantic_total_max가 결정된 뒤
    # 실제 사용 가능한 항목만 대상으로 배점을 재분배한다.
    full_score = 0.0
    resp_score = 0.0
    qual_score = 0.0
    semantic_before_adjust = 0.0
    semantic_total = 0.0

    rule_evidence_count = count_rule_evidence_groups(
        skill_used=skill_used,
        skill_total_count=skill_total_count,
        edu_used=edu_used,
        exp_detail=exp_detail,
        cert_used=cert_used,
        cert_total_count=cert_total_count,
        qual_used=qual_used,
        qual_total_count=qual_total_count,
    )

    safe_ncs_category = (
    get_safe_ncs_category(
        job
        )
    )

    _record_full_score_perf(
        "score_setup",
        time.perf_counter() - stage_start,
    )

    stage_start = time.perf_counter()

    if should_try_ncs_score(
        rule_evidence_count
    ):
        if safe_ncs_category:
            ncs_result = (
                calculate_ncs_score(
                    resume_text=
                        resume_full_text,

                    job_text=
                        job_full_text,

                    category=
                        safe_ncs_category,

                    ncs_codes=
                        job.get(
                            "ncsCodes",
                            [],
                        ),

                    ncs_names=
                        job.get(
                            "ncsNames",
                            [],
                        ),

                    model=
                        get_model(),

                    util_module=
                        util,
                )
            )
        else:
            ncs_result = (
                build_ncs_not_applied_result(
                    "공고의 직무 카테고리가 명확하지 않아 "
                    "NCS 보완 점수를 적용하지 않았습니다."
                )
            )

    else:
        ncs_result = (
            build_ncs_not_applied_result(
                "공고에 명시된 룰 기반 판단 지표가 충분하여 "
                "NCS 보완 점수를 적용하지 않았습니다."
            )
        )

    _record_full_score_perf(
        "ncs",
        time.perf_counter() - stage_start,
    )

    stage_start = time.perf_counter()

    ncs_used = bool(ncs_result.get("ncs_used", False))

    if ncs_used and rule_evidence_count == 0:
        # 룰 근거 없음 + NCS 사용
        rule_total_max = 0.0
        semantic_total_max = 70.0
        ncs_total_max = 30.0
        scoring_mode = "SEMANTIC_70_NCS_30"

    elif ncs_used:
        # 룰 근거 있음 + NCS 사용
        rule_total_max = 15.0
        semantic_total_max = 70.0
        ncs_total_max = 15.0
        scoring_mode = "RULE_15_SEMANTIC_70_NCS_15"

    elif rule_evidence_count == 0:
        # 룰 근거 없음 + 신뢰 가능한 NCS도 없음
        # 사용 가능한 의미 유사도만 100점 기준으로 정규화
        rule_total_max = 0.0
        semantic_total_max = 100.0
        ncs_total_max = 0.0
        scoring_mode = "SEMANTIC_100"

    else:
        # 룰 근거 있음 + NCS 없음
        rule_total_max = 30.0
        semantic_total_max = 70.0
        ncs_total_max = 0.0
        scoring_mode = "RULE_30_SEMANTIC_70"

    # ------------------------------------------------------------------
    # 의미 기반 항목 사용 여부 판단
    # ------------------------------------------------------------------
    full_semantic_used = bool(resume_full_text and job_full_text)

    # 단순히 responsibilities가 존재하는지만 보지 않고,
    # NCS 대분류명/카테고리명만 들어간 경우는 실제 담당업무가 없는 것으로 처리한다.
    resp_semantic_used = bool(
        resume_exp_text
        and job_resp_text
        and has_meaningful_responsibilities(job)
    )

    # 자격요건 의미 유사도는 '필수 자격요건' 텍스트가 실제 존재할 때만 사용한다.
    qual_semantic_used = bool(resume_exp_text and job_qual_text)

    semantic_weights = get_semantic_component_weights(
        semantic_total_max=semantic_total_max,
        full_used=full_semantic_used,
        resp_used=resp_semantic_used,
        qual_used=qual_semantic_used,
    )

    # ------------------------------------------------------------------
    # [기존 방식 - 고정 35/21/14 배점]
    # full_score = raw_full_sim * FULL_SEMANTIC_WEIGHT
    # resp_score = raw_resp_sim * RESPONSIBILITY_SEMANTIC_WEIGHT
    # qual_score = raw_qual_sim * QUALIFICATION_SEMANTIC_WEIGHT
    # ------------------------------------------------------------------

    # [새 방식 - 실제 존재하는 항목끼리 재분배]
    full_score = (
        full_sim * semantic_weights["full"]
        if full_semantic_used
        else 0.0
    )
    resp_score = (
        resp_sim * semantic_weights["resp"]
        if resp_semantic_used
        else 0.0
    )
    qual_score = (
        qual_sim * semantic_weights["qual"]
        if qual_semantic_used
        else 0.0
    )

    semantic_before_adjust = full_score + resp_score + qual_score
    semantic_total = semantic_before_adjust

    rule_weights = get_rule_component_weights(
        rule_total_max=rule_total_max,
        skill_used=skill_used,
        edu_used=edu_used,
        exp_used=exp_used,
        cert_used=cert_used,
        qual_used=qual_used,
    )
    skill_score = get_score_ratio(skill_score_raw, 30) * rule_weights["skill"] if skill_used else 0.0
    edu_score = get_score_ratio(edu_score_raw, 10) * rule_weights["edu"] if edu_used else 0.0

    if exp_used:
        exp_score = get_score_ratio(
            exp_detail.get("exp_year_score", 0),
            exp_detail.get("exp_year_max", 10)
        ) * rule_weights["exp"]
    else:
        exp_score = 0.0

    cert_score = get_score_ratio(cert_score_raw, 10) * rule_weights["cert"] if cert_used else 0.0
    qual_rule_score = get_score_ratio(qual_rule_score_raw, 10) * rule_weights["qual"] if qual_used else 0.0
    rule_total = skill_score + edu_score + exp_score + cert_score + qual_rule_score
    ncs_score = (ncs_result.get("ncs_similarity", 0.0) or 0.0) * ncs_total_max if ncs_used else 0.0

    fit_score = round(min(rule_total + semantic_total + ncs_score, 100.0), 2)

    accessibility_score = calculate_accessibility_score(
        skill_used=skill_used,
        skill_match_count=skill_match_count,
        skill_total_count=skill_total_count,
        edu_used=edu_used,
        edu_score_raw=edu_score_raw,
        exp_detail=exp_detail,
        cert_used=cert_used,
        cert_match_count=cert_match_count,
        cert_total_count=cert_total_count,
        qual_used=qual_used,
        qual_rule_score_raw=qual_accessibility_score_raw,
    )

    confidence_score = calculate_confidence_score(job)

    match_badges = get_match_badges(
        fit_score=fit_score,
        accessibility_score=accessibility_score,
        confidence_score=confidence_score,
        has_blocking_unmet=has_blocking_unmet,
        has_blocking_unknown=has_blocking_unknown,
        rule_evidence_count=rule_evidence_count,
        ncs_used=ncs_used,
    )

    recommend_type = get_recommend_type(
        fit_score=fit_score,
        accessibility_score=accessibility_score,
        confidence_score=confidence_score,
        has_blocking_unmet=has_blocking_unmet,
        has_blocking_unknown=has_blocking_unknown,
        rule_evidence_count=rule_evidence_count,
        ncs_used=ncs_used,
    )

    _record_full_score_perf(
        "score_finalize",
        time.perf_counter() - stage_start,
    )

    stage_start = time.perf_counter()

    resume_dictionary_features = extract_dictionary_features(raw_resume_full_text)
    job_dictionary_features = extract_dictionary_features(raw_job_full_text)
    category_info = get_category_overlap(raw_resume_full_text, raw_job_full_text)

    _record_full_score_perf(
        "dictionary_features",
        time.perf_counter() - stage_start,
    )

    debug_print_start = time.perf_counter()

    print("[단어사전 기반]")
    print(f"- 이력서 직무 카테고리: {category_info.get('resumeCategories', [])}")
    print(f"- 공고 직무 카테고리: {category_info.get('jobCategories', [])}")
    print(f"- 일치 직무 카테고리: {category_info.get('matchedCategories', [])}")

    print("[룰 기반]")

    if skill_used:
        print(
            f"- 기술 스택 일치도: {skill_score:.2f}/{rule_weights['skill']:.1f} "
            f"(일치 {skill_match_count}/{skill_total_count}, 매칭: {matched_skills})"
        )
    else:
        print("- 기술 스택: 요구 조건 없음, 평가 제외")

    if edu_used:
        print(
            f"- 학력 조건: {edu_score:.2f}/{rule_weights['edu']:.1f} "
            f"(공고: {job_edu_level or '무관'}, 이력서: {resume_edu_level or '미확인'})"
        )
    else:
        print("- 학력: 학력 조건 없음, 평가 제외")

    if exp_used:
        print(
            f"- 경력 조건: {exp_score:.2f}/{rule_weights['exp']:.1f} "
            f"(지원자 {exp_detail.get('resume_exp', 0)}년 / 요구 {exp_detail.get('min_exp', 0)}년)"
        )
    else:
        print("- 경력: 경력 조건 없음, 평가 제외")

    if cert_used:
        print(
            f"- 자격증: {cert_score:.2f}/{rule_weights['cert']:.1f} "
            f"(일치 {cert_match_count}/{cert_total_count})"
        )
    else:
        print("- 자격증: 요구 조건 없음, 평가 제외")

    if qual_used:
        print(
            f"- 필수 자격요건: {qual_rule_score:.2f}/{rule_weights['qual']:.1f} "
            f"(일치 {len(matched_quals)}/{qual_total_count}, "
            f"원문 {qual_original_count}개 / 직종선별 {qual_scoped_count}개 / "
            f"평가대상 {qual_total_count}개)"
        )
    elif qual_original_count > 0:
        print(
            f"- 필수 자격요건: 원문 {qual_original_count}개 존재, "
            "이력서로 점수화 가능한 조건 없음 → 평가 제외"
        )
    else:
        print("- 필수 자격요건: 요구 조건 없음, 평가 제외")

    print(f"룰 기반 점수 합계: {rule_total:.2f}/{rule_total_max:.0f}")

    print("[의미 기반]")
    print(f"- 필수조건 충족률: {required_condition_ratio:.4f}")
    print(f"- 의미 기반 보정 비율: {semantic_adjust_ratio:.4f}")

    # ------------------------------------------------------------------
    # [기존 방식 - 고정 최대점수 출력]
    # print(f"- 이력서 전체와 공고 전체 유사도: {full_score:.2f}/{FULL_SEMANTIC_WEIGHT:.0f} (유사도 {full_sim:.4f})")
    # print(f"- 자기소개서·경험과 담당업무 유사도: {resp_score:.2f}/{RESPONSIBILITY_SEMANTIC_WEIGHT:.0f} (유사도 {resp_sim:.4f})")
    # print(f"- 자기소개서·경험과 자격요건 유사도: {qual_score:.2f}/{QUALIFICATION_SEMANTIC_WEIGHT:.0f} (유사도 {qual_sim:.4f})")
    # ------------------------------------------------------------------

    if full_semantic_used:
        print(
            f"- 이력서 전체와 공고 전체 유사도: "
            f"{full_score:.2f}/{semantic_weights['full']:.2f} "
            f"(유사도 {full_sim:.4f})"
        )
    else:
        print("- 이력서 전체와 공고 전체 유사도: 비교 정보 없음, 평가 제외")

    if resp_semantic_used:
        print(
            f"- 자기소개서·경험과 담당업무 유사도: "
            f"{resp_score:.2f}/{semantic_weights['resp']:.2f} "
            f"(유사도 {resp_sim:.4f})"
        )
    else:
        print("- 자기소개서·경험과 담당업무 유사도: 담당업무 정보 없음, 평가 제외")

    if qual_semantic_used:
        print(
            f"- 자기소개서·경험과 자격요건 유사도: "
            f"{qual_score:.2f}/{semantic_weights['qual']:.2f} "
            f"(유사도 {qual_sim:.4f})"
        )
    else:
        print("- 자기소개서·경험과 자격요건 유사도: 자격요건 정보 없음, 평가 제외")

    print(f"의미 기반 점수 합계: {semantic_total:.2f}/{semantic_total_max:.0f}")

    print("[NCS 직무역량]")
    print(f"- NCS 적용 여부: {ncs_result.get('ncs_used', False)}")
    print(f"- NCS 분야: {ncs_result.get('ncs_category', '') or '미적용'}")
    print(f"- 매칭 직무: {ncs_result.get('matched_duty_name', '') or '없음'}")
    print(f"- 매칭 능력단위: {ncs_result.get('matched_unit_name', '') or '없음'}")
    print(f"- NCS 유사도: {ncs_result.get('ncs_similarity', 0):.4f}")
    print(f"- NCS 점수: {ncs_score:.2f}/{ncs_total_max:.0f}")
    print(f"- 점수 계산 방식: {scoring_mode}")

    print("[최종 점수]")
    print(f"- 적합도 점수: {fit_score:.2f}/100")
    print(f"- 자격 통과 가능성 점수: {accessibility_score:.2f}/100")
    print(f"- 판단 근거 충분도 점수: {confidence_score:.2f}/100")
    print(f"- 추천 유형: {recommend_type}")
    print(f"- 배지: {match_badges}")

    print("[미충족 조건]")

    if unmet_conditions:
        for condition in unmet_conditions:
            print(f"- {condition}")
    else:
        print("- 없음")

    _record_full_score_perf(
        "debug_output",
        time.perf_counter() - debug_print_start,
    )

    result_build_start = time.perf_counter()

    final_result = {
        "final_score": fit_score,
        "fit_score": fit_score,
        "accessibility_score": accessibility_score,
        "confidence_score": confidence_score,
        "recommend_type": recommend_type,
        "match_badges": match_badges,
        "rule_total": round(rule_total, 2),
        "rule_total_max": rule_total_max,
        "semantic_total": round(semantic_total, 2),
        "semantic_total_max": semantic_total_max,
        "ncs_total": round(ncs_score, 2),
        "ncs_total_max": ncs_total_max,
        "ncs_details": ncs_result,
        "scoring_mode": scoring_mode,
        "rule_evidence_count": rule_evidence_count,
        "unmet_conditions": unmet_conditions,
        "rule_details": {
            "skill_score": round(skill_score, 2),
            "skill_score_max": rule_weights["skill"],
            "skill_raw_score": round(skill_score_raw, 2),
            "skill_raw_score_max": 30,
            "skill_match_count": skill_match_count,
            "skill_total_count": skill_total_count,
            "skill_used": skill_used,
            "matched_skills": matched_skills,

            "edu_score": round(edu_score, 2),
            "edu_score_max": rule_weights["edu"],
            "edu_raw_score": edu_score_raw,
            "edu_raw_score_max": 10,
            "job_edu_level": job_edu_level,
            "resume_edu_level": resume_edu_level,
            "resume_majors": as_list(resume.get("majors", [])),
            "education_details": as_list(resume.get("educationDetails", [])),
            "edu_used": edu_used,

            **exp_detail,
            "exp_score": round(exp_score, 2),
            "exp_score_max": rule_weights["exp"],
            "exp_raw_score": round(exp_detail.get("exp_raw_score", 0), 2),
            "exp_raw_score_max": exp_detail.get("exp_raw_score_max", 0),
            "min_exp": exp_detail.get("min_exp", 0),
            "resume_exp": exp_detail.get("resume_exp", 0),
            "exp_used": exp_used,

            "cert_score": round(cert_score, 2),
            "cert_score_max": rule_weights["cert"],
            "cert_raw_score": round(cert_score_raw, 2),
            "cert_raw_score_max": 10,
            "cert_match_count": cert_match_count,
            "cert_total_count": cert_total_count,
            "cert_used": cert_used,
            "matched_certs": matched_certs,
            "certification_scope": certification_scope_info,

            "qual_rule_score": round(qual_rule_score, 2),
            "qual_rule_score_max": rule_weights["qual"],
            "qual_raw_score": round(qual_rule_score_raw, 2),
            "qual_raw_score_max": 10,
            "qual_accessibility_raw_score": round(qual_accessibility_score_raw, 2),
            "matched_quals": matched_quals,
            "qual_total_count": qual_total_count,
            "qual_original_count": qual_original_count,
            "qual_scoped_count": qual_scoped_count,
            "qual_used": qual_used,
            "resume_eligibility": resume.get("eligibility", {}),
            "eligibility_matched_quals": as_list(qual_detail.get("eligibility_matched", [])),
            "eligibility_unmatched_quals": eligibility_unmatched,
            "eligibility_unknown_quals": eligibility_unknown,
            "eligibility_fields": qual_detail.get("eligibility_fields", {}),
        },
        "semantic_details": {
            "full_sim": full_sim,
            "full_score": round(full_score, 2),
            # [기존 방식] "full_score_max": FULL_SEMANTIC_WEIGHT,
            "full_score_max": round(semantic_weights["full"], 2),
            "full_score_raw": round(raw_full_score, 2),
            "full_semantic_used": full_semantic_used,

            "resp_sim": resp_sim,
            "resp_score": round(resp_score, 2),
            # [기존 방식] "resp_score_max": RESPONSIBILITY_SEMANTIC_WEIGHT,
            "resp_score_max": round(semantic_weights["resp"], 2),
            "resp_score_raw": round(raw_resp_score, 2),
            "resp_semantic_used": resp_semantic_used,

            "qual_sim": qual_sim,
            "qual_score": round(qual_score, 2),
            # [기존 방식] "qual_score_max": QUALIFICATION_SEMANTIC_WEIGHT,
            "qual_score_max": round(semantic_weights["qual"], 2),
            "qual_score_raw": round(raw_qual_score, 2),
            "qual_semantic_used": qual_semantic_used,

            "semantic_total_max": semantic_total_max,
            "semantic_before_adjust": round(semantic_before_adjust, 2),
            "semantic_adjust_ratio": semantic_adjust_ratio,
            "required_condition_ratio": required_condition_ratio,
        },
        "dictionary_details": {
            "resume_features": resume_dictionary_features,
            "job_features": job_dictionary_features,
            "category_info": category_info,
            "standardized_resume_text": resume_full_text,
            "standardized_job_text": job_full_text,
        },
        "role_scope": role_scope_info,
        "score_details": {
            "fit_score": fit_score,
            "fit_score_max": 100,
            "accessibility_score": accessibility_score,
            "accessibility_score_max": 100,
            "confidence_score": confidence_score,
            "confidence_score_max": 100,
            "ncs_score": round(ncs_score, 2),
            "ncs_score_max": ncs_total_max,
            "recommend_type": recommend_type,
            "match_badges": match_badges,
        },
    }

    _record_full_score_perf(
        "result_build",
        time.perf_counter() - result_build_start,
    )

    _record_full_score_perf(
        "total",
        time.perf_counter() - full_score_total_start,
    )

    return final_result
