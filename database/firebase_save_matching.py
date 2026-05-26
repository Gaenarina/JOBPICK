from datetime import datetime


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
        "status": "DONE",
        "updatedAt": datetime.utcnow().isoformat(),
    }

    db.collection("matching_results").document(str(resume_id)).set(save_data, merge=True)

    return str(resume_id)


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

    return {
        "resumeId": data.get("resumeId", str(resume_id)),
        "userId": data.get("userId", ""),
        "matches": matches,
        "topFitMatches": top_fit_matches,
        "topAccessibleMatches": top_accessible_matches,
        "topConfidenceMatches": top_confidence_matches,
        "matchCount": data.get("matchCount", len(matches)),
        "topFitCount": data.get("topFitCount", len(top_fit_matches)),
        "topAccessibleCount": data.get("topAccessibleCount", len(top_accessible_matches)),
        "topConfidenceCount": data.get("topConfidenceCount", len(top_confidence_matches)),
        "status": data.get("status", "DONE"),
        "updatedAt": data.get("updatedAt", ""),
    }