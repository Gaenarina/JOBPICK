from copy import deepcopy
from typing import Any, Dict, List

from matching.matchtest import (
    flatten_resume,
    flatten_job,
    calculate_full_score,
)


def apply_simulation_items(
    resume_flat: Dict[str, Any],
    selected: List[Dict[str, Any]],
) -> Dict[str, Any]:

    simulated = deepcopy(resume_flat)

    simulated.setdefault("skills", [])
    simulated.setdefault("certifications", [])

    for item in selected or []:
        item_type = str(item.get("type", "")).strip()
        value = str(item.get("value", "")).strip()

        if not value:
            continue

        # 실제 이력서 저장이 아니라
        # 시뮬레이션 복사본에만 임시 반영
        if item_type == "skill":
            if value not in simulated["skills"]:
                simulated["skills"].append(value)

        elif item_type == "certificate":
            if value not in simulated["certifications"]:
                simulated["certifications"].append(value)

        # qualification / education / experience 등은
        # 지금 단계에서는 임의 생성하지 않음

    return simulated


def simulate_matching(
    resume_doc: Dict[str, Any],
    job_doc: Dict[str, Any],
    selected: List[Dict[str, Any]],
) -> Dict[str, Any]:

    resume_flat = flatten_resume(resume_doc)
    job_flat = flatten_job(job_doc)

    simulated_resume = apply_simulation_items(
        resume_flat,
        selected,
    )

    # 기존 매칭 로직 그대로 다시 사용
    # simulated_resume 기준으로 context도 새로 계산되게 함
    result = calculate_full_score(
        job_flat,
        simulated_resume,
        label="simulation",
    )

    return {
        "simulatedResume": simulated_resume,
        "scoreResult": result,
    }