from typing import Any, Dict, List

from matching.keyword_dictionary import extract_dictionary_features


def build_improvement_candidates(
    match_result: Dict[str, Any]
) -> List[Dict[str, Any]]:

    detail = match_result.get("matchDetail", {}) or {}

    skills = detail.get("skills", {}) or {}
    certifications = detail.get("certifications", {}) or {}
    qualifications = detail.get("qualifications", {}) or {}
    education = detail.get("education", {}) or {}
    experience = detail.get("experience", {}) or {}

    candidates = []
    seen_ids = set()

    def add_candidate(candidate: Dict[str, Any]):
        candidate_id = str(candidate.get("id", "")).strip()

        if not candidate_id:
            return

        if candidate_id in seen_ids:
            return

        seen_ids.add(candidate_id)
        candidates.append(candidate)

    # =========================================================
    # 1. 기술
    # =========================================================
    for skill in skills.get("missingSkills", []) or []:
        skill = str(skill).strip()

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

    # =========================================================
    # 2. 명시적으로 추출된 자격증
    # =========================================================
    for cert in certifications.get("missingCerts", []) or []:
        cert = str(cert).strip()

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

    # =========================================================
    # 3. missingQuals 분석
    #
    # 자격요건 문장 안에 실제 자격증명이 있으면
    # keyword_dictionary를 이용해 certificate 후보로 분리
    #
    # 예:
    # "사회조사분석사(2급 이상), ADP,
    #  빅데이터분석기사 중 1개 이상 소지자"
    # =========================================================
    for qual in qualifications.get("missingQuals", []) or []:
        qual = str(qual).strip()

        if not qual:
            continue

        features = extract_dictionary_features(qual) or {}

        detected_certs = (
            features.get("certifications", [])
            or []
        )

        detected_certs = [
            str(cert).strip()
            for cert in detected_certs
            if str(cert).strip()
        ]

        # 자격증이 발견된 경우
        if detected_certs:
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

            continue

        # 자격증이 아닌 일반 지원자격은
        # 사용자가 직접 확인하도록 유지
        add_candidate({
            "id": f"qualification:{qual}",
            "type": "qualification",
            "label": f"필수 자격요건 확인: {qual}",
            "value": qual,
            "applyMode": "review_only",
            "canApplyToResume": False,
            "source": "missingQuals",
        })

    # =========================================================
    # 4. 학력
    # 실제 학력을 임의로 변경하지 않음
    # =========================================================
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
                "label": f"학력 조건 확인: {job_level}",
                "value": job_level,
                "currentValue": resume_level,
                "applyMode": "review_only",
                "canApplyToResume": False,
                "source": "education",
            })

    # =========================================================
    # 5. 경력
    # 실제 경력을 임의로 생성하지 않음
    # =========================================================
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
                "label": f"경력 조건 확인: 최소 {min_exp:g}년",
                "value": min_exp,
                "currentValue": resume_exp,
                "applyMode": "review_only",
                "canApplyToResume": False,
                "source": "experience",
            })

    return candidates