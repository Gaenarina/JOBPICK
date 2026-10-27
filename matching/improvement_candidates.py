from typing import Any, Dict, List

from matching.keyword_dictionary import (
    extract_dictionary_features,
)
from matching.matchtest import (
    flatten_resume,
    normalize_cert_name,
)


def build_improvement_candidates(
    match_result: Dict[str, Any],
    resume_doc: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    저장된 미충족 평가 항목으로 보완 후보를 생성한다.

    - 이미 보유한 자격증은 자격증 보완 후보에서 제외한다.
    - 자격증이 포함된 미충족 문장도 전체 충족 가정 항목으로 남긴다.
    - 실제 이력서는 수정하지 않는다.
    """
    resume_flat = flatten_resume(resume_doc)

    owned_certificates = set()

    for cert in resume_flat.get("certifications", []) or []:
        normalized = normalize_cert_name(cert)

        if normalized:
            owned_certificates.add(normalized)

    detail = match_result.get("matchDetail", {}) or {}

    skills = detail.get("skills", {}) or {}
    certifications = detail.get("certifications", {}) or {}
    qualifications = detail.get("qualifications", {}) or {}
    education = detail.get("education", {}) or {}
    experience = detail.get("experience", {}) or {}

    candidates: List[Dict[str, Any]] = []
    seen_ids = set()

    def add_candidate(candidate: Dict[str, Any]):
        candidate_id = str(
            candidate.get("id", "")
        ).strip()

        if not candidate_id:
            return

        if candidate.get("type") == "certificate":
            cert_name = normalize_cert_name(
                candidate.get("value", "")
            )

            # 보유한 자격증은 추천하지 않는다.
            if (
                not cert_name
                or cert_name in owned_certificates
            ):
                return

            # 표기가 달라도 정규화한 자격증명이 같으면 중복 제거
            candidate_id = f"certificate:{cert_name}"
            candidate["id"] = candidate_id

        if candidate_id in seen_ids:
            return

        seen_ids.add(candidate_id)
        candidates.append(candidate)

    # =====================================================
    # 1. 미충족 기술
    # =====================================================
    for skill in skills.get("missingSkills", []) or []:
        skill = str(skill or "").strip()

        if not skill:
            continue

        add_candidate({
            "id": f"skill:{skill}",
            "type": "skill",
            "label": f"기술 보완: {skill}",
            "value": skill,
            "applyMode": "prefill",
            "canApplyToResume": True,
            "source": "missingSkills",
        })

    # =====================================================
    # 2. 명시적으로 평가된 미충족 자격증
    # =====================================================
    for cert in certifications.get("missingCerts", []) or []:
        cert = str(cert or "").strip()

        if not cert:
            continue

        add_candidate({
            "id": f"certificate:{cert}",
            "type": "certificate",
            "label": f"자격증 보완: {cert}",
            "value": cert,
            "applyMode": "prefill",
            "canApplyToResume": True,
            "source": "missingCerts",
        })

    # =====================================================
    # 3. 미충족 필수 자격요건
    #
    # 문장에서 자격증을 추출해 개별 후보를 생성한다.
    # 이미 보유한 자격증은 add_candidate()에서 제외한다.
    #
    # 자격증 추출 여부와 관계없이 문장 전체의
    # 충족 가정 항목도 유지한다.
    # =====================================================
    for qual in qualifications.get("missingQuals", []) or []:
        qual = str(qual or "").strip()

        if not qual:
            continue

        features = extract_dictionary_features(qual) or {}

        detected_certs = [
            str(cert).strip()
            for cert in (
                features.get("certifications", []) or []
            )
            if cert is not None and str(cert).strip()
        ]

        for cert in detected_certs:
            add_candidate({
                "id": f"certificate:{cert}",
                "type": "certificate",
                "label": f"자격증 보완: {cert}",
                "value": cert,
                "applyMode": "prefill",
                "canApplyToResume": True,
                "source": "missingQuals",
                "relatedQualification": qual,
            })

        # continue를 사용하지 않는다.
        # 자격증 외의 경력·전공 등 복합 조건이 남을 수 있으므로
        # 문장 전체를 충족한다고 가정하는 선택지도 제공한다.
        add_candidate({
            "id": f"qualification:{qual}",
            "type": "qualification",
            "label": f"필수 자격요건 충족 가정: {qual}",
            "value": qual,
            "applyMode": "review_only",
            "canApplyToResume": False,
            "source": "missingQuals",
        })

    # =====================================================
    # 4. 학력 조건
    # 실제 학력 변경이 아닌 충족 가정용 항목
    # =====================================================
    if education.get("used", False):
        job_level = education.get("jobLevel", "")
        resume_level = education.get("resumeLevel", "")

        raw_score = float(
            education.get("rawScore", 0) or 0
        )

        if raw_score < 10:
            add_candidate({
                "id": "education:minimum",
                "type": "education",
                "label": (
                    f"학력 조건 충족 가정: {job_level}"
                ),
                "value": job_level,
                "currentValue": resume_level,
                "applyMode": "review_only",
                "canApplyToResume": False,
                "source": "education",
            })

    # =====================================================
    # 5. 경력 연수 조건
    # 실제 경력 생성이 아닌 최소 연수 충족 가정용 항목
    # =====================================================
    if experience.get("conditionUsed", False):
        min_exp = float(
            experience.get("minExp", 0) or 0
        )
        resume_exp = float(
            experience.get("resumeExp", 0) or 0
        )

        if min_exp > resume_exp:
            add_candidate({
                "id": "experience:years",
                "type": "experience",
                "label": (
                    f"경력 연수 충족 가정: 최소 {min_exp:g}년"
                ),
                "value": min_exp,
                "currentValue": resume_exp,
                "applyMode": "review_only",
                "canApplyToResume": False,
                "source": "experience",
            })

    return candidates