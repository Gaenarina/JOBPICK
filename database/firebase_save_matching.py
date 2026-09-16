from datetime import datetime

from firebase_admin import firestore


def make_json_safe(value):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, list):
        return [make_json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [make_json_safe(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(val)
            for key, val in value.items()
        }

    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except Exception:
            pass

    return str(value)


def save_matching_result(
    db,
    resume_id,
    user_id=None,
    matches=None,
    top_fit_matches=None,
    top_accessible_matches=None,
    top_confidence_matches=None,
    match_preferences=None,
    total_job_count=None,
    filtered_job_count=None,
    ai_summary=None,

    # 추가: 이 매칭 결과가 어떤 이력서 분석본을 기준으로 생성됐는지 저장
    analysis_source="original",        # "original" 또는 "edited"
    resume_analysis_version=1,         # 이력서 분석 버전
    is_analysis_edited=False,          # 사용자가 분석 내용을 수정했는지 여부
):
    safe_matches = make_json_safe(matches or [])
    safe_top_fit = make_json_safe(top_fit_matches or [])
    safe_top_accessible = make_json_safe(top_accessible_matches or [])
    safe_top_confidence = make_json_safe(top_confidence_matches or [])

    save_data = {
        "resumeId": str(resume_id),
        "userId": str(user_id or ""),

        "matches": safe_matches,
        "topFitMatches": safe_top_fit,
        "topAccessibleMatches": safe_top_accessible,
        "topConfidenceMatches": safe_top_confidence,

        "matchCount": len(safe_matches),
        "topFitCount": len(safe_top_fit),
        "topAccessibleCount": len(safe_top_accessible),
        "topConfidenceCount": len(safe_top_confidence),
        "matchPreferences": make_json_safe(match_preferences or {}),
        "totalJobCount": total_job_count,
        "filteredJobCount": filtered_job_count,
        "aiSummary": make_json_safe(ai_summary or {}),

        # 추가: 매칭 결과가 어떤 분석 데이터를 기준으로 만들어졌는지 기록
        "analysisSource": str(analysis_source or "original"),
        "resumeAnalysisVersion": int(resume_analysis_version or 1),
        "isAnalysisEdited": bool(is_analysis_edited),

        "status": "DONE",
        "updatedAt": datetime.utcnow().isoformat(),
    }

    db.collection("matching_results").document(str(resume_id)).set(
        save_data,
        merge=True
    )

    return str(resume_id)


def create_matching_complete_notification(db, user_id, resume_id):
    uid = str(user_id or "").strip()
    rid = str(resume_id or "").strip()

    if not uid or not rid:
        return False

    notification_id = f"ai-matching-{rid}"
    notif_ref = (
        db.collection("users")
        .document(uid)
        .collection("notifications")
        .document(notification_id)
    )

    if notif_ref.get().exists:
        return False

    notif_ref.set({
        "title": "AI 매칭 분석 완료",
        "content": "이력서 AI 매칭 분석이 완료되었습니다. 새로운 매칭 공고를 확인해보세요.",
        "category": "company",
        "icon": "sparkles",
        "read": False,
        "resumeId": rid,
        "createdAt": firestore.SERVER_TIMESTAMP,
    })

    return True


def get_matching_result(db, resume_id):
    doc_ref = db.collection("matching_results").document(str(resume_id))
    doc = doc_ref.get()

    if not doc.exists:
        return None

    data = doc.to_dict() or {}

    matches = data.get("matches", [])
    top_fit_matches = data.get("topFitMatches", [])
    top_accessible_matches = data.get("topAccessibleMatches", [])
    top_confidence_matches = data.get("topConfidenceMatches", [])
    manual_matches = data.get("manualMatches", [])

    return {
        "resumeId": data.get("resumeId", str(resume_id)),
        "userId": data.get("userId", ""),

        "matches": matches,
        "topFitMatches": top_fit_matches,
        "topAccessibleMatches": top_accessible_matches,
        "topConfidenceMatches": top_confidence_matches,

        # 개별 매칭 결과
        "manualMatches": manual_matches,

        "matchCount": data.get("matchCount", len(matches)),
        "topFitCount": data.get("topFitCount", len(top_fit_matches)),
        "topAccessibleCount": data.get(
            "topAccessibleCount",
            len(top_accessible_matches)
        ),
        "topConfidenceCount": data.get(
            "topConfidenceCount",
            len(top_confidence_matches)
        ),
        "manualMatchCount": data.get(
            "manualMatchCount",
            len(manual_matches)
        ),

        "matchPreferences": data.get("matchPreferences", {}),
        "totalJobCount": data.get("totalJobCount"),
        "filteredJobCount": data.get("filteredJobCount"),
        "aiSummary": data.get("aiSummary", {}),

        "analysisSource": data.get("analysisSource", "original"),
        "resumeAnalysisVersion": data.get(
            "resumeAnalysisVersion",
            1
        ),
        "isAnalysisEdited": data.get(
            "isAnalysisEdited",
            False
        ),

        "status": data.get("status", "DONE"),
        "updatedAt": data.get("updatedAt", ""),
    }