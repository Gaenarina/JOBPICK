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


def save_matching_result(db, resume_id, matches):
    doc_ref = db.collection("matching_results").document(str(resume_id))

    safe_matches = make_json_safe(matches or [])

    save_data = {
        "resumeId": str(resume_id),
        "matches": safe_matches,
        "matchCount": len(safe_matches),
        "status": "DONE",
        "updatedAt": datetime.utcnow().isoformat(),
    }

    doc_ref.set(save_data, merge=True)

    return str(resume_id)


def get_matching_result(db, resume_id):
    doc_ref = db.collection("matching_results").document(str(resume_id))
    doc = doc_ref.get()

    if not doc.exists:
        return None

    data = doc.to_dict() or {}
    matches = data.get("matches", [])

    return {
        "resumeId": data.get("resumeId", str(resume_id)),
        "matches": matches,
        "matchCount": data.get("matchCount", len(matches)),
        "status": data.get("status", "DONE"),
        "updatedAt": data.get("updatedAt", ""),
    }