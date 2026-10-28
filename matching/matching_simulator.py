from copy import deepcopy
import math

from matching.matchtest import (
    calculate_accessibility_score,
    calculate_certification_score,
    calculate_qualification_rule_score_detailed,
    calculate_skill_score,
    flatten_resume,
    get_recommend_type,
    normalize_cert_name,
)


def number(value, default=0.0):
    try:
        result = float(value)

        if not math.isfinite(result):
            return default

        return result

    except (TypeError, ValueError):
        return default


def text_set(values):
    return {
        str(value).strip()
        for value in (values or [])
        if str(value).strip()
    }


def qualification_matches(required, resume):
    if not required:
        return set()

    _, matched, _, _, _ = (
        calculate_qualification_rule_score_detailed(
            required,
            resume,
        )
    )

    return text_set(matched)


def calculate_saved_accessibility(detail):
    skills = detail.get("skills") or {}
    certs = detail.get("certifications") or {}
    education = detail.get("education") or {}
    experience = detail.get("experience") or {}
    qualifications = detail.get("qualifications") or {}

    return calculate_accessibility_score(
        skill_used=bool(skills.get("used")),
        skill_match_count=int(number(skills.get("matchCount"))),
        skill_total_count=int(number(skills.get("totalCount"))),
        edu_used=bool(education.get("used")),
        edu_score_raw=number(education.get("rawScore")),
        exp_detail={
            "exp_condition_used": bool(
                experience.get("conditionUsed")
            ),
            "min_exp": number(experience.get("minExp")),
            "resume_exp": number(experience.get("resumeExp")),
        },
        cert_used=bool(certs.get("used")),
        cert_match_count=int(number(certs.get("matchCount"))),
        cert_total_count=int(number(certs.get("totalCount"))),
        qual_used=bool(qualifications.get("used")),
        qual_rule_score_raw=number(
            qualifications.get("rawScore")
        ),
    )


def simulate_matching(saved_match, selected, resume_doc):
    """
    저장된 배점과 AI·NCS 점수를 유지하는 시뮬레이션.

    구체적인 보완 항목은 이력서 복사본에 반영하고,
    기존 규칙 판정 함수로 추가 충족 여부를 검사한다.

    qualification 선택은 해당 문장 전체의 충족 가정이다.
    실제 이력서와 저장된 매칭 결과는 수정하지 않는다.
    """
    if not isinstance(selected, list):
        raise ValueError("selected는 배열이어야 합니다.")

    if any(not isinstance(item, dict) for item in selected):
        raise ValueError("보완 항목의 형식이 올바르지 않습니다.")

    supported_types = {
        "skill",
        "certificate",
        "education",
        "experience",
        "qualification",
    }

    for item in selected:
        if item.get("type") not in supported_types:
            raise ValueError(
                f"지원하지 않는 보완 유형입니다: "
                f"{item.get('type')}"
            )

    detail = deepcopy(saved_match.get("matchDetail") or {})

    if not detail:
        raise ValueError("저장된 세부 평가 결과가 없습니다.")

    # 누락된 평가 항목도 같은 detail 안에서 관리한다.
    component_keys = (
        "skills",
        "certifications",
        "education",
        "experience",
        "qualifications",
    )

    for key in component_keys:
        if not isinstance(detail.get(key), dict):
            detail[key] = {}

    before = deepcopy(detail)

    skills = detail["skills"]
    certs = detail["certifications"]
    education = detail["education"]
    experience = detail["experience"]
    qualifications = detail["qualifications"]

    warnings = []

    original_resume = flatten_resume(resume_doc)
    simulated_resume = deepcopy(original_resume)

    simulated_resume["skills"] = list(
        simulated_resume.get("skills") or []
    )
    simulated_resume["certifications"] = list(
        simulated_resume.get("certifications") or []
    )

    selected_types = {
        item.get("type")
        for item in selected
    }

    selected_certificates = set()

    # ------------------------------------------------------
    # 1. 이력서 복사본에 구체적인 보완 내용 반영
    # ------------------------------------------------------
    for item in selected:
        item_type = item.get("type")
        value = item.get("value")

        if item_type == "certificate":
            certificate = str(value or "").strip()

            if certificate:
                simulated_resume["certifications"].append(
                    certificate
                )
                selected_certificates.add(
                    normalize_cert_name(certificate)
                )

        elif item_type == "skill":
            skill = str(value or "").strip()

            if skill:
                simulated_resume["skills"].append(skill)

        elif item_type == "education":
            if education.get("used"):
                simulated_resume["education"] = (
                    education.get("jobLevel")
                    or simulated_resume.get("education", "")
                )

        elif item_type == "experience":
            if experience.get("conditionUsed"):
                simulated_resume["experienceYears"] = max(
                    number(
                        simulated_resume.get("experienceYears")
                    ),
                    number(experience.get("minExp")),
                )

    # ------------------------------------------------------
    # 2. 기술·자격증 추가 충족 여부 검사
    # 기존 판정 함수를 사용하되 저장된 배점을 유지한다.
    # ------------------------------------------------------
    def update_count_component(
        component,
        required_key,
        matched_key,
        missing_key,
        checked_before,
        checked_after,
    ):
        required = component.get(required_key) or []
        total = int(number(component.get("totalCount")))

        if not component.get("used") or total <= 0:
            return

        # 원래 이력서에서도 충족하던 항목을
        # 이번 선택으로 새로 충족한 것으로 계산하지 않는다.
        additions = (
            text_set(checked_after)
            - text_set(checked_before)
            - text_set(component.get(matched_key))
        )

        if not additions:
            return

        old_count = int(number(component.get("matchCount")))
        new_count = min(total, old_count + len(additions))

        if new_count <= old_count:
            return

        matched = (
            text_set(component.get(matched_key))
            | additions
        )

        component["matchCount"] = new_count
        component["score"] = (
            number(component.get("maxScore"))
            * new_count
            / total
        )
        component["rawScore"] = (
            number(component.get("rawMaxScore"))
            * new_count
            / total
        )
        component[matched_key] = sorted(matched)

        component[missing_key] = [
            value
            for value in required
            if str(value).strip() not in matched
        ]

    if "skill" in selected_types:
        job_skills = {
            "required": skills.get("requiredSkills") or []
        }

        skill_before = calculate_skill_score(
            job_skills,
            original_resume.get("skills") or [],
        )
        skill_after = calculate_skill_score(
            job_skills,
            simulated_resume.get("skills") or [],
        )

        update_count_component(
            skills,
            "requiredSkills",
            "matchedSkills",
            "missingSkills",
            skill_before[4],
            skill_after[4],
        )

    if "certificate" in selected_types:
        required_certificates = (
            certs.get("requiredCerts") or []
        )

        cert_before = calculate_certification_score(
            required_certificates,
            original_resume.get("certifications") or [],
        )
        cert_after = calculate_certification_score(
            required_certificates,
            simulated_resume.get("certifications") or [],
        )

        update_count_component(
            certs,
            "requiredCerts",
            "matchedCerts",
            "missingCerts",
            cert_before[4],
            cert_after[4],
        )

    # ------------------------------------------------------
    # 3. 학력·총 경력 연수 가정 반영
    # ------------------------------------------------------
    if (
        "education" in selected_types
        and education.get("used")
    ):
        education["score"] = number(
            education.get("maxScore")
        )
        education["rawScore"] = number(
            education.get("rawMaxScore"),
            10,
        )
        education["resumeLevel"] = (
            education.get("jobLevel") or ""
        )

    if (
        "experience" in selected_types
        and experience.get("conditionUsed")
    ):
        experience["resumeExp"] = number(
            simulated_resume.get("experienceYears")
        )
        experience["score"] = number(
            experience.get("maxScore")
        )
        experience["yearScore"] = number(
            experience.get("yearMax"),
            10,
        )
        experience["rawScore"] = experience["yearScore"]

    # ------------------------------------------------------
    # 4. 필수 자격요건 추가 충족 여부 검사
    # 자격증이 별도 배점에 없어도 여기에서 반영될 수 있다.
    # ------------------------------------------------------
    required_qualifications = (
        qualifications.get("requiredQuals") or []
    )
    matched_qualifications = text_set(
        qualifications.get("matchedQuals")
    )
    missing_qualifications = text_set(
        qualifications.get("missingQuals")
    )

    selected_qualifications = {
        str(item.get("value", "")).strip()
        for item in selected
        if item.get("type") == "qualification"
    }

    # 문장 전체를 충족한다고 직접 선택한 항목
    assumed_qualifications = (
        selected_qualifications & missing_qualifications
    )

    automatically_matched = set()

    has_concrete_changes = bool(
        selected_types & {
            "skill",
            "certificate",
            "education",
            "experience",
        }
    )

    if (
        has_concrete_changes
        and qualifications.get("used")
        and required_qualifications
    ):
        matched_before = qualification_matches(
            required_qualifications,
            original_resume,
        )
        matched_after = qualification_matches(
            required_qualifications,
            simulated_resume,
        )

        automatically_matched = (
            (matched_after - matched_before)
            & missing_qualifications
        )

    newly_matched_qualifications = (
        assumed_qualifications
        | automatically_matched
    ) - matched_qualifications

    matched_qualifications.update(
        newly_matched_qualifications
    )

    qualification_total = int(
        number(qualifications.get("totalCount"))
    )

    if (
        newly_matched_qualifications
        and qualifications.get("used")
        and qualification_total > 0
    ):
        matched_count = min(
            len(matched_qualifications),
            qualification_total,
        )
        matched_ratio = matched_count / qualification_total

        qualifications["score"] = (
            number(qualifications.get("maxScore"))
            * matched_ratio
        )
        qualifications["rawScore"] = (
            number(qualifications.get("rawMaxScore"), 10)
            * matched_ratio
        )
        qualifications["matchedQuals"] = sorted(
            matched_qualifications
        )
        qualifications["missingQuals"] = sorted(
            missing_qualifications
            - matched_qualifications
        )

    for qualification in (
        selected_qualifications - assumed_qualifications
    ):
        warnings.append(
            f"'{qualification}'은 저장된 미충족 "
            "자격요건과 연결되지 않아 반영하지 않았습니다."
        )

    # 별도 자격증 배점에 없는 항목도 자격요건 검사에는 사용된다.
    required_cert_names = {
        normalize_cert_name(value)
        for value in (certs.get("requiredCerts") or [])
    }

    for certificate in sorted(
        selected_certificates - required_cert_names
    ):
        warnings.append(
            f"'{certificate}'은 별도 자격증 배점 항목이 없어 "
            "필수 자격요건 검사에만 사용했습니다."
        )

    # ------------------------------------------------------
    # 5. 저장된 총점에 규칙 점수 변화량만 반영
    # ------------------------------------------------------
    delta = sum(
        number(detail[key].get("score"))
        - number(before[key].get("score"))
        for key in component_keys
    )

    original_score = number(
        saved_match.get("fitScore")
        if saved_match.get("fitScore") is not None
        else saved_match.get("finalScore")
    )

    predicted_score = round(
        max(
            0.0,
            min(100.0, original_score + delta),
        ),
        2,
    )

    # 저장된 지원 가능성에 규칙 충족 변화량만 반영한다.
    # 저장되지 않은 '확인 불가' 항목의 중립 점수를
    # 불필요하게 제거하지 않도록 기존 점수를 기준으로 삼는다.
    accessibility_before = calculate_saved_accessibility(
        before
    )
    accessibility_after = calculate_saved_accessibility(
        detail
    )

    original_accessibility = number(
        saved_match.get("accessibilityScore"),
        accessibility_before,
    )

    accessibility = round(
        max(
            0.0,
            min(
                100.0,
                original_accessibility
                + accessibility_after
                - accessibility_before,
            ),
        ),
        2,
    )

    # ------------------------------------------------------
    # 6. 해소된 미충족 조건 반영
    # ------------------------------------------------------
    unmet = set(
        saved_match.get("unmetConditions") or []
    )

    if (
        newly_matched_qualifications
        and qualification_total > 0
        and len(matched_qualifications)
        >= qualification_total
    ):
        unmet.discard("필수 자격요건 미충족")

    if (
        skills.get("used")
        and number(skills.get("totalCount")) > 0
        and number(skills.get("matchCount"))
        >= number(skills.get("totalCount"))
    ):
        unmet.discard("필수 기술 미충족")

    if (
        certs.get("used")
        and number(certs.get("totalCount")) > 0
        and number(certs.get("matchCount"))
        >= number(certs.get("totalCount"))
    ):
        unmet.discard("필수 자격증 미충족")

    if (
        education.get("used")
        and number(education.get("rawScore")) >= 10
    ):
        unmet.discard("학력 조건 미충족")

    if (
        experience.get("conditionUsed")
        and number(experience.get("resumeExp"))
        >= number(experience.get("minExp"))
    ):
        unmet.discard("경력 연수 미충족")

    blocking_labels = {
        "필수 기술 미충족",
        "학력 조건 미충족",
        "경력 연수 미충족",
        "필수 자격증 미충족",
        "필수 지원자격 미충족",
        "필수 자격요건 미충족",
    }

    blocking = bool(unmet & blocking_labels)

    unknown = bool(
        unmet & {
            "필수 지원자격 확인 필요",
            "필수 자격증 직종 확인 필요",
        }
    )

    # ------------------------------------------------------
    # 7. 기존 추천 유형 판정 함수 사용
    # ------------------------------------------------------
    predicted_type = get_recommend_type(
        fit_score=predicted_score,
        accessibility_score=accessibility,
        confidence_score=number(
            saved_match.get("confidenceScore")
        ),
        has_blocking_unmet=blocking,
        has_blocking_unknown=unknown,
        rule_evidence_count=int(
            number(saved_match.get("ruleEvidenceCount"))
        ),
        ncs_used=bool(
            (detail.get("ncs") or {}).get("used")
        ),
    )

    notice = (
        "기존 AI·NCS 점수와 평가 배점은 유지하고, "
        "선택한 보완 내용에 따른 규칙 점수 변화만 "
        "반영한 예상치입니다. "
        "필수 자격요건 충족 가정은 해당 문장 전체를 "
        "충족하는 것으로 처리합니다. "
        "실제 이력서 재분석 결과와 다를 수 있습니다."
    )

    if warnings:
        notice += " " + " ".join(warnings)

    print(
        "[시뮬레이션] 자동 충족 자격요건:",
        sorted(automatically_matched),
    )
    print(
        "[시뮬레이션] 직접 충족 가정:",
        sorted(assumed_qualifications),
    )
    print(
        "[시뮬레이션] 규칙 점수 변화:",
        round(delta, 4),
    )
    print(
        "[시뮬레이션] 남은 미충족 조건:",
        sorted(unmet),
    )

    return {
        "original": {
            "score": round(original_score, 2),
            "recommendType": saved_match.get(
                "recommendType",
                "",
            ),
        },
        "simulated": {
            "score": predicted_score,
            "recommendType": predicted_type,
            "accessibilityScore": accessibility,
        },
        "scoreChange": round(
            predicted_score - round(original_score, 2),
            2,
        ),
        "notice": notice,
    }