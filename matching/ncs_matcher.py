import json
import re
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]
NCS_DICTIONARY_PATH = ROOT_DIR / "data" / "ncs_dictionary_by_category.json"

NCS_WEIGHT = 25.0


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


def get_ncs_units(category: str) -> List[Dict[str, Any]]:
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


def calculate_ncs_score(
    resume_text: Any,
    job_text: Any,
    category: str = "",
    model=None,
    util_module=None,
) -> Dict[str, Any]:
    compare_text = clean_text(f"{resume_text} {job_text}")
    category_text = clean_text(f"{category} {job_text}")

    ncs_category = category if category == "IT/개발" else infer_ncs_category(category_text)

    if not ncs_category:
        return {
            "ncs_used": False,
            "ncs_category": "",
            "ncs_score": 0.0,
            "ncs_score_max": NCS_WEIGHT,
            "ncs_similarity": 0.0,
            "matched_duty_cd": "",
            "matched_duty_name": "",
            "matched_unit_cd": "",
            "matched_unit_name": "",
            "reason": "NCS 적용 대상 분야가 아닙니다.",
        }

    units = get_ncs_units(ncs_category)

    if not units:
        return {
            "ncs_used": False,
            "ncs_category": ncs_category,
            "ncs_score": 0.0,
            "ncs_score_max": NCS_WEIGHT,
            "ncs_similarity": 0.0,
            "matched_duty_cd": "",
            "matched_duty_name": "",
            "matched_unit_cd": "",
            "matched_unit_name": "",
            "reason": "해당 분야의 NCS 사전이 없습니다.",
        }

    best_similarity = 0.0
    best_unit = None

    if model is not None and util_module is not None:
        compare_embedding = model.encode(compare_text, convert_to_tensor=True)

        for unit in units:
            ncs_embedding = model.encode(unit["matchText"], convert_to_tensor=True)
            similarity = float(util_module.cos_sim(compare_embedding, ncs_embedding)[0][0])
            similarity = max(0.0, min(1.0, similarity))

            if similarity > best_similarity:
                best_similarity = similarity
                best_unit = unit
    else:
        for unit in units:
            similarity = keyword_similarity(compare_text, unit["matchText"])

            if similarity > best_similarity:
                best_similarity = similarity
                best_unit = unit

    if best_unit is None:
        return {
            "ncs_used": True,
            "ncs_category": ncs_category,
            "ncs_score": 0.0,
            "ncs_score_max": NCS_WEIGHT,
            "ncs_similarity": 0.0,
            "matched_duty_cd": "",
            "matched_duty_name": "",
            "matched_unit_cd": "",
            "matched_unit_name": "",
            "reason": "유사한 NCS 능력단위를 찾지 못했습니다.",
        }

    ncs_score = round(best_similarity * NCS_WEIGHT, 2)

    return {
        "ncs_used": True,
        "ncs_category": ncs_category,
        "ncs_score": ncs_score,
        "ncs_score_max": NCS_WEIGHT,
        "ncs_similarity": round(best_similarity, 4),
        "matched_duty_cd": best_unit.get("dutyCd", ""),
        "matched_duty_name": best_unit.get("dutyName", ""),
        "matched_unit_cd": best_unit.get("unitCd", ""),
        "matched_unit_name": best_unit.get("unitName", ""),
        "reason": f"{best_unit.get('dutyName', '')}의 {best_unit.get('unitName', '')} 능력단위와 가장 유사합니다.",
    }