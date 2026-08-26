import json
import re
from pathlib import Path
from typing import Any, Dict, List

from matching.vector_store import get_vectors


ROOT_DIR = Path(__file__).resolve().parents[1]
NCS_DICTIONARY_PATH = ROOT_DIR / "data" / "ncs_dictionary_by_category.json"
NCS_UNIT_PATH = ROOT_DIR / "data" / "ncs_units.json"

NCS_WEIGHT = 25.0
NCS_MODEL_CANDIDATE_LIMIT = 40

# 공고와 NCS 능력단위 자체의 의미 유사도가 이 값보다 낮으면
# 억지로 가장 높은 후보를 선택하지 않고 NCS를 미적용한다.
NCS_JOB_MATCH_MIN_SIMILARITY = 0.45
# 임베딩 모델을 사용할 수 없는 fallback 상황의 키워드 유사도 기준
NCS_JOB_KEYWORD_MIN_SIMILARITY = 0.05

# NCS 분류코드는 2/4/6/8자리처럼 상위-하위 분류가 섞여 들어올 수 있다.
# 너무 짧은 코드로 prefix 검색을 하면 후보군이 지나치게 넓어지므로,
# 최소 4자리(중분류 수준 이상)부터 후보 필터링에 사용한다.
NCS_CODE_MIN_PREFIX_LENGTH = 4

_ncs_unit_cache_path = None
_ncs_unit_cache_mtime = None
_ncs_unit_cache = []


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def load_ncs_dictionary() -> Dict[str, Any]:
    if not NCS_DICTIONARY_PATH.exists():
        return {}

    with NCS_DICTIONARY_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_ncs_units() -> List[Dict[str, Any]]:
    global _ncs_unit_cache_path, _ncs_unit_cache_mtime, _ncs_unit_cache
    if not NCS_UNIT_PATH.exists():
        return []
    try:
        resolved_path = NCS_UNIT_PATH.resolve()
        modified_at = NCS_UNIT_PATH.stat().st_mtime_ns
        if _ncs_unit_cache_path == resolved_path and _ncs_unit_cache_mtime == modified_at:
            return _ncs_unit_cache
        with NCS_UNIT_PATH.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        units = payload.get("units", []) if isinstance(payload, dict) else []
        _ncs_unit_cache_path = resolved_path
        _ncs_unit_cache_mtime = modified_at
        _ncs_unit_cache = units
        return units
    except (OSError, json.JSONDecodeError):
        return []


def infer_ncs_category(text: Any) -> str:
    value = clean_text(text).lower()

    it_keywords = [
        "it/개발",
        "it",
        "개발",
        "웹",
        "프론트엔드",
        "백엔드",
        "서버",
        "소프트웨어",
        "sw",
        "응용sw",
        "프로그래밍",
        "java",
        "python",
        "javascript",
        "typescript",
        "react",
        "next",
        "node",
        "spring",
        "sql",
        "database",
        "db",
        "api",
        "firebase",
    ]

    for keyword in it_keywords:
        if keyword in value:
            return "IT/개발"

    return ""


def normalize_ncs_code(value: Any) -> str:
    return re.sub(r"\D", "", clean_text(value))


def get_ncs_units(category: str, ncs_codes=None, ncs_names=None) -> List[Dict[str, Any]]:
    """
    공고에서 제공된 NCS 코드/명칭을 우선 사용해 후보 능력단위를 제한한다.

    주의:
    - 너무 짧은 분류코드는 후보가 과도하게 넓어질 수 있으므로
      NCS_CODE_MIN_PREFIX_LENGTH 미만이면 코드 필터링에 사용하지 않는다.
    - 코드가 있으면 코드 일치 후보를 최우선으로 사용한다.
    - 코드 후보가 없을 때만 명칭 일치 후보를 사용한다.
    """
    synced_units = load_ncs_units()

    if synced_units:
        raw_codes = [
            normalize_ncs_code(code)
            for code in (ncs_codes or [])
            if clean_text(code)
        ]
        codes = [
            code
            for code in raw_codes
            if len(code) >= NCS_CODE_MIN_PREFIX_LENGTH
        ]
        names = [
            clean_text(name).lower()
            for name in (ncs_names or [])
            if clean_text(name)
        ]

        code_selected = []
        name_selected = []

        for unit in synced_units:
            duty_code = normalize_ncs_code(unit.get("classificationCode", ""))
            hierarchy_values = [
                clean_text(unit.get("majorName", "")),
                clean_text(unit.get("middleName", "")),
                clean_text(unit.get("minorName", "")),
                clean_text(unit.get("subName", "")),
            ]
            hierarchy_text = clean_text(" ".join(hierarchy_values)).lower()

            code_match = any(
                duty_code.startswith(code) or code.startswith(duty_code)
                for code in codes
                if code and duty_code
            )

            # NCS 명칭은 공고에서 주어진 명칭이 실제 계층 명칭 안에 포함되는 경우만 허용한다.
            # 기존의 hierarchy_text in name 역방향 비교는 광범위한 오매칭을 유발할 수 있어 제거한다.
            name_match = any(
                name in hierarchy_text
                for name in names
                if name
            )

            if not (code_match or name_match):
                continue

            normalized = {
                "dutyCd": unit.get("classificationCode", ""),
                "dutyName": unit.get("subName", "") or unit.get("minorName", ""),
                "unitCd": unit.get("unitCode", ""),
                "unitName": unit.get("unitName", ""),
                "majorName": unit.get("majorName", ""),
                "middleName": unit.get("middleName", ""),
                "minorName": unit.get("minorName", ""),
                "subName": unit.get("subName", ""),
                "matchText": clean_text(unit.get("matchText", "")),
            }

            if code_match:
                code_selected.append(normalized)
            elif name_match:
                name_selected.append(normalized)

        if code_selected:
            return code_selected

        if name_selected:
            return name_selected

    # API 분류로 후보를 만들지 못한 경우 기존 카테고리 사전을 fallback으로 사용한다.
    dictionary = load_ncs_dictionary()

    if category not in dictionary:
        return []

    units = []
    duties = dictionary.get(category, {}).get("duties", {}) or {}

    for duty in duties.values():
        for unit in duty.get("units", []) or []:
            match_text = clean_text(unit.get("matchText", ""))

            if not match_text:
                continue

            units.append({
                "dutyCd": duty.get("dutyCd", ""),
                "dutyName": duty.get("dutyName", ""),
                "unitCd": unit.get("unitCd", ""),
                "unitName": unit.get("unitName", ""),
                "majorName": "",
                "middleName": "",
                "minorName": "",
                "subName": duty.get("dutyName", ""),
                "matchText": match_text,
            })

    return units

def keyword_similarity(source_text: str, target_text: str) -> float:
    source_tokens = set(re.findall(r"[가-힣A-Za-z0-9+#.]+", source_text.lower()))
    target_tokens = set(re.findall(r"[가-힣A-Za-z0-9+#.]+", target_text.lower()))

    if not source_tokens or not target_tokens:
        return 0.0

    overlap = source_tokens & target_tokens

    return len(overlap) / max(len(target_tokens), 1)


def _empty_ncs_result(
    reason: str,
    ncs_category: str = "",
    job_match_similarity: float = 0.0,
) -> Dict[str, Any]:
    return {
        "ncs_used": False,
        "ncs_category": ncs_category,
        "ncs_score": 0.0,
        "ncs_score_max": NCS_WEIGHT,
        "ncs_similarity": 0.0,
        "job_ncs_similarity": round(job_match_similarity, 4),
        "matched_duty_cd": "",
        "matched_duty_name": "",
        "matched_unit_cd": "",
        "matched_unit_name": "",
        "matched_major_name": "",
        "matched_middle_name": "",
        "matched_minor_name": "",
        "matched_sub_name": "",
        "reason": reason,
    }


def _semantic_similarity(
    source_text: str,
    target_text: str,
    model=None,
    util_module=None,
) -> float:
    source_text = clean_text(source_text)
    target_text = clean_text(target_text)

    if not source_text or not target_text:
        return 0.0

    if model is None or util_module is None:
        return keyword_similarity(source_text, target_text)

    source_embedding = model.encode(source_text, convert_to_tensor=True)
    stored_vectors = get_vectors([target_text])

    if stored_vectors is not None:
        import torch
        target_embedding = torch.from_numpy(stored_vectors.copy())
    else:
        target_embedding = model.encode(
            [target_text],
            convert_to_tensor=True,
            show_progress_bar=False,
        )

    similarity = util_module.cos_sim(source_embedding, target_embedding)[0][0].item()
    return max(0.0, min(1.0, float(similarity)))


def calculate_ncs_score(
    resume_text: Any,
    job_text: Any,
    category: str = "",
    model=None,
    util_module=None,
    ncs_codes=None,
    ncs_names=None,
) -> Dict[str, Any]:
    """
    NCS 점수 계산을 두 단계로 분리한다.

    1) 공고(job_text)만 사용해 가장 적절한 NCS 능력단위를 선택한다.
       - 이력서 내용은 NCS 직무 선택에 절대 사용하지 않는다.
       - 공고-NCS 유사도가 기준 미만이면 NCS를 미적용한다.

    2) 1단계에서 선택된 NCS 능력단위와 이력서(resume_text)를 비교해
       지원자의 NCS 직무역량 유사도 점수를 계산한다.
    """
    job_compare_text = clean_text(job_text)
    resume_compare_text = clean_text(resume_text)
    category_text = clean_text(f"{category} {job_text}")

    has_api_classification = bool(ncs_codes or ncs_names)
    ncs_category = category if has_api_classification else infer_ncs_category(category_text)

    if not ncs_category:
        return _empty_ncs_result("NCS 적용 대상 분야가 아닙니다.")

    units = get_ncs_units(
        ncs_category,
        ncs_codes=ncs_codes,
        ncs_names=ncs_names,
    )

    if not units:
        broad_codes = [
            normalize_ncs_code(code)
            for code in (ncs_codes or [])
            if clean_text(code)
            and len(normalize_ncs_code(code)) < NCS_CODE_MIN_PREFIX_LENGTH
        ]

        if broad_codes and not (ncs_names or []):
            return _empty_ncs_result(
                "공고의 NCS 분류코드가 너무 넓어 안전하게 능력단위를 특정할 수 없습니다.",
                ncs_category=ncs_category,
            )

        return _empty_ncs_result(
            "해당 분야에서 비교할 수 있는 NCS 능력단위를 찾지 못했습니다.",
            ncs_category=ncs_category,
        )

    # 공고 본문이 비어 있으면 분류명/공고 NCS 명칭을 보조 텍스트로 사용한다.
    if not job_compare_text:
        job_compare_text = clean_text(
            " ".join([
                clean_text(category),
                *[clean_text(name) for name in (ncs_names or []) if clean_text(name)],
            ])
        )

    if not job_compare_text:
        return _empty_ncs_result(
            "공고 직무 설명이 부족하여 NCS 능력단위를 선택할 수 없습니다.",
            ncs_category=ncs_category,
        )

    # 후보가 많을 때도 이력서는 사용하지 않고 '공고 ↔ NCS' 키워드 유사도로만 1차 축소한다.
    if len(units) > NCS_MODEL_CANDIDATE_LIMIT:
        units = sorted(
            units,
            key=lambda unit: keyword_similarity(job_compare_text, unit["matchText"]),
            reverse=True,
        )[:NCS_MODEL_CANDIDATE_LIMIT]

    best_job_similarity = 0.0
    best_unit = None

    # 1단계: 공고 ↔ NCS 능력단위 매칭
    if model is not None and util_module is not None:
        job_embedding = model.encode(job_compare_text, convert_to_tensor=True)
        unit_texts = [unit["matchText"] for unit in units]

        stored_vectors = get_vectors(unit_texts)
        if stored_vectors is not None:
            import torch
            unit_embeddings = torch.from_numpy(stored_vectors.copy())
        else:
            unit_embeddings = model.encode(
                unit_texts,
                convert_to_tensor=True,
                batch_size=min(32, len(units)),
                show_progress_bar=False,
            )

        similarities = util_module.cos_sim(job_embedding, unit_embeddings)[0]
        best_index = int(similarities.argmax().item())
        best_job_similarity = max(
            0.0,
            min(1.0, float(similarities[best_index]))
        )
        best_unit = units[best_index]
    else:
        for unit in units:
            similarity = keyword_similarity(job_compare_text, unit["matchText"])

            if similarity > best_job_similarity:
                best_job_similarity = similarity
                best_unit = unit

    if best_unit is None:
        return _empty_ncs_result(
            "유사한 NCS 능력단위를 찾지 못했습니다.",
            ncs_category=ncs_category,
        )

    # 최고 후보라도 공고 자체와 충분히 유사하지 않으면 강제 매칭하지 않는다.
    job_match_threshold = (
        NCS_JOB_MATCH_MIN_SIMILARITY
        if model is not None and util_module is not None
        else NCS_JOB_KEYWORD_MIN_SIMILARITY
    )

    if best_job_similarity < job_match_threshold:
        return _empty_ncs_result(
            (
                "공고와 가장 가까운 NCS 능력단위의 유사도가 "
                f"{best_job_similarity:.4f}로 기준 "
                f"{job_match_threshold:.2f} 미만이어서 NCS를 적용하지 않았습니다."
            ),
            ncs_category=ncs_category,
            job_match_similarity=best_job_similarity,
        )

    # 2단계: 선택된 NCS 능력단위 ↔ 이력서 비교
    # 이 값이 실제 지원자의 NCS 점수에 사용된다.
    resume_similarity = _semantic_similarity(
        resume_compare_text,
        best_unit["matchText"],
        model=model,
        util_module=util_module,
    )

    ncs_score = round(resume_similarity * NCS_WEIGHT, 2)

    return {
        "ncs_used": True,
        "ncs_category": ncs_category,
        "ncs_score": ncs_score,
        "ncs_score_max": NCS_WEIGHT,

        # 기존 calculate_full_score()가 이 값을 사용하므로
        # 이제는 '이력서 ↔ 선택된 NCS 능력단위' 유사도를 반환한다.
        "ncs_similarity": round(resume_similarity, 4),

        # 디버깅용: 공고가 해당 NCS 능력단위와 얼마나 잘 맞았는지도 별도로 반환한다.
        "job_ncs_similarity": round(best_job_similarity, 4),

        "matched_duty_cd": best_unit.get("dutyCd", ""),
        "matched_duty_name": best_unit.get("dutyName", ""),
        "matched_unit_cd": best_unit.get("unitCd", ""),
        "matched_unit_name": best_unit.get("unitName", ""),
        "matched_major_name": best_unit.get("majorName", ""),
        "matched_middle_name": best_unit.get("middleName", ""),
        "matched_minor_name": best_unit.get("minorName", ""),
        "matched_sub_name": best_unit.get("subName", ""),
        "reason": (
            f"공고와 {best_unit.get('dutyName', '')}의 "
            f"{best_unit.get('unitName', '')} 능력단위가 "
            f"{best_job_similarity:.4f}의 유사도로 매칭되었고, "
            f"이력서와 해당 능력단위의 유사도는 {resume_similarity:.4f}입니다."
        ),
    }

