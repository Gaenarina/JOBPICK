from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import json
import os
import traceback
import urllib.error
import urllib.parse
import urllib.request

from database.firebase_init import init_firebase
from database.firebase_save_matching import (
    save_matching_result,
    get_matching_result,
)

from main.main_resume import process_resume_by_doc_id
from main.main_matching import process_matching_groups_by_resume_id
from main.main_matching_one import process_matching_one_by_ids

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_ROOT, ".env.local"))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

app = Flask(__name__)
CORS(app)

db, bucket = init_firebase("config/firebase_key.json")


def get_score_value(item, keys):
    if not isinstance(item, dict):
        return 0

    for key in keys:
        value = item.get(key)

        try:
            value = float(value)

            if 0 < value <= 1:
                return value * 100

            return value
        except:
            pass

    return 0


def get_fit_score(item):
    return get_score_value(item, [
        "fitScore",
        "fit_score",
        "finalScore",
        "final_score",
        "matchRate",
        "match_rate",
    ])


def get_accessibility_score(item):
    return get_score_value(item, [
        "accessibilityScore",
        "accessibility_score",
    ])


def get_confidence_score(item):
    return get_score_value(item, [
        "confidenceScore",
        "confidence_score",
    ])


def get_company_from_job_data(data):
    if not isinstance(data, dict):
        return ""

    job_posting = data.get("jobPosting", {}) or {}
    legacy = data.get("legacyJobPosting", {}) or {}
    meta = data.get("meta", {}) or {}
    company_info = job_posting.get("companyInfo", {}) or {}

    company = (
        data.get("company")
        or data.get("companyName")
        or job_posting.get("companyName")
        or job_posting.get("company")
        or company_info.get("name")
        or company_info.get("companyName")
        or legacy.get("companyName")
        or legacy.get("company")
        or meta.get("companyName")
        or meta.get("company")
        or ""
    )

    return str(company).strip() if company else ""


def get_company_from_match_item(item):
    if not isinstance(item, dict):
        return ""

    company = get_company_from_job_data(item)

    if company:
        return company

    raw_data = item.get("rawData", {}) or {}
    company = get_company_from_job_data(raw_data)

    if company:
        return company

    job_posting = item.get("jobPosting", {}) or {}

    if isinstance(job_posting, dict):
        company = get_company_from_job_data(job_posting)

        if company:
            return company

    return ""


def get_match_job_id(item):
    if not isinstance(item, dict):
        return ""

    return (
        item.get("jobId")
        or item.get("id")
        or item.get("postingId")
        or item.get("posting_id")
        or item.get("jobPostingId")
        or item.get("job_posting_id")
        or item.get("docId")
        or ""
    )


def fill_missing_company_names(db, matches):
    fixed_matches = []

    for item in matches or []:
        if not isinstance(item, dict):
            fixed_matches.append(item)
            continue

        fixed_item = dict(item)

        company = get_company_from_match_item(fixed_item)

        if company:
            fixed_item["company"] = company
            fixed_item["companyName"] = company
            fixed_matches.append(fixed_item)
            continue

        job_id = get_match_job_id(fixed_item)

        if job_id:
            doc = db.collection("job_postings").document(str(job_id)).get()

            if doc.exists:
                data = doc.to_dict() or {}
                company = get_company_from_job_data(data)

                if company:
                    fixed_item["company"] = company
                    fixed_item["companyName"] = company

        fixed_matches.append(fixed_item)

    return fixed_matches


def dedupe_matches(matches):
    result = []
    seen = set()

    for item in matches or []:
        if not isinstance(item, dict):
            continue

        job_id = get_match_job_id(item)

        if not job_id:
            continue

        key = str(job_id)

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result


def build_matching_groups(matches, limit=5):
    unique_matches = dedupe_matches(matches)

    top_fit_matches = sorted(
        unique_matches,
        key=get_fit_score,
        reverse=True
    )[:limit]

    top_accessible_matches = sorted(
        unique_matches,
        key=get_accessibility_score,
        reverse=True
    )[:limit]

    top_confidence_matches = sorted(
        unique_matches,
        key=get_confidence_score,
        reverse=True
    )[:limit]

    return {
        "matches": unique_matches,
        "topFitMatches": top_fit_matches,
        "topAccessibleMatches": top_accessible_matches,
        "topConfidenceMatches": top_confidence_matches,
    }


def normalize_matching_groups(groups):
    matches = fill_missing_company_names(
        db,
        groups.get("matches", [])
    )

    top_fit_matches = fill_missing_company_names(
        db,
        groups.get("topFitMatches", [])
    )

    top_accessible_matches = fill_missing_company_names(
        db,
        groups.get("topAccessibleMatches", [])
    )

    top_confidence_matches = fill_missing_company_names(
        db,
        groups.get("topConfidenceMatches", [])
    )

    if not top_fit_matches or not top_accessible_matches or not top_confidence_matches:
        rebuilt_groups = build_matching_groups(matches, limit=5)

        if not top_fit_matches:
            top_fit_matches = rebuilt_groups["topFitMatches"]

        if not top_accessible_matches:
            top_accessible_matches = rebuilt_groups["topAccessibleMatches"]

        if not top_confidence_matches:
            top_confidence_matches = rebuilt_groups["topConfidenceMatches"]

    return {
        "matches": matches,
        "topFitMatches": top_fit_matches,
        "topAccessibleMatches": top_accessible_matches,
        "topConfidenceMatches": top_confidence_matches,
        "matchPreferences": groups.get("matchPreferences", {}) or {},
        "totalJobCount": groups.get("totalJobCount"),
        "filteredJobCount": groups.get("filteredJobCount"),
        "aiSummary": groups.get("aiSummary", {}) or {},
        "selectedAnalysisField": groups.get("selectedAnalysisField"),
        "analysisSource": groups.get("analysisSource"),
        "resumeAnalysisVersion": groups.get("resumeAnalysisVersion"),
        "isAnalysisEdited": groups.get("isAnalysisEdited"),
    }


def clean_list(value):
    if not isinstance(value, list):
        return []

    return [str(item).strip() for item in value if str(item or "").strip()]


def to_float(value, fallback=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def get_group_score_average(matches, key):
    values = []

    for item in matches or []:
        try:
            value = to_float(item.get(key, 0))
            values.append(value)
        except (TypeError, ValueError, AttributeError):
            pass

    if not values:
        return 0

    return round(sum(values) / len(values))


def get_match_distribution(matches):
    distribution = {
        "aiFit": 0,
        "accessible": 0,
        "insufficientInfo": 0,
        "needsReview": 0,
    }

    for item in matches or []:
        recommend_type = str(item.get("recommendType") or item.get("recommend_type") or "")
        badges = item.get("matchBadges") or item.get("match_badges") or []
        text = " ".join([recommend_type] + [str(badge) for badge in badges])
        fit_score = to_float(item.get("fitScore") or item.get("finalScore") or item.get("matchRate") or 0)
        accessibility_score = to_float(item.get("accessibilityScore") or 0)
        confidence_score = to_float(item.get("confidenceScore") or 0)

        if "AI 적합" in text or fit_score >= 70:
            distribution["aiFit"] += 1
        elif "지원 가능" in text or accessibility_score >= 70:
            distribution["accessible"] += 1
        elif "정보 부족" in text or confidence_score < 45:
            distribution["insufficientInfo"] += 1
        else:
            distribution["needsReview"] += 1

    return distribution


def has_match_preferences(preferences):
    return any(
        clean_list(preferences.get(key))
        for key in ("desiredRoles", "desiredLocations", "employmentTypes")
    )


def build_gemini_summary_payload(groups):
    preferences = groups.get("matchPreferences", {}) or {}
    top_matches = groups.get("topFitMatches", []) or []
    all_matches = groups.get("matches", []) or top_matches
    has_preferences = has_match_preferences(preferences)

    return {
        "matchPreferences": {
            "desiredRoles": clean_list(preferences.get("desiredRoles")),
            "desiredLocations": clean_list(preferences.get("desiredLocations")),
            "employmentTypes": clean_list(preferences.get("employmentTypes")),
        },
        "hasMatchPreferences": has_preferences,
        "jobCounts": {
            "totalJobCount": groups.get("totalJobCount"),
            "filteredJobCount": groups.get("filteredJobCount"),
            "recommendedCount": len(top_matches),
        },
        "distribution": get_match_distribution(all_matches),
        "scoreAverages": {
            "fitScore": get_group_score_average(top_matches, "fitScore"),
            "accessibilityScore": get_group_score_average(top_matches, "accessibilityScore"),
            "confidenceScore": get_group_score_average(top_matches, "confidenceScore"),
        },
        "recommendedJobs": [
            {
                "title": item.get("title", ""),
                "company": item.get("company") or item.get("companyName") or "",
                "matchRate": item.get("matchRate"),
                "fitScore": item.get("fitScore"),
                "accessibilityScore": item.get("accessibilityScore"),
                "confidenceScore": item.get("confidenceScore"),
                "recommendType": item.get("recommendType"),
                "matchBadges": item.get("matchBadges", []),
                "unmetConditions": item.get("unmetConditions", []),
                "explanationSummary": item.get("explanationSummary", {}),
            }
            for item in top_matches[:5]
        ],
    }


def extract_json_object(text):
    if not text:
        return None

    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1 or start >= end:
        return None

    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        return None


def extract_gemini_text(response_data):
    if not isinstance(response_data, dict):
        return ""

    output_text = response_data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    candidates = response_data.get("candidates")
    if isinstance(candidates, list) and candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        text = "\n".join([part for part in text_parts if part])
        if text.strip():
            return text

    steps = response_data.get("steps")
    if isinstance(steps, list):
        text_parts = []
        for step in steps:
            content = step.get("content") if isinstance(step, dict) else None
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        text_parts.append(item.get("text", ""))
            elif isinstance(content, str):
                text_parts.append(content)
        return "\n".join([part for part in text_parts if part])

    return ""


def generate_gemini_ai_summary(groups):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        return None

    configured_model = os.getenv("GEMINI_MODEL", "").strip()
    fallback_models = [
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-3.5-flash",
    ]
    models = [configured_model] if configured_model else []
    models.extend([model for model in fallback_models if model and model not in models])
    payload = build_gemini_summary_payload(groups)

    prompt = (
        "You are an explanation assistant for JOBPICK, a job matching service. "
        "Use only the given matching result JSON. Do not invent facts or personal data. "
        "Write a Korean summary of the overall recommendation result, not a single job. "
        "Do not start the description with a company name or a job title. "
        "Do not describe one specific posting as if it represents the whole result. "
        "Summarize common patterns across the recommended jobs, score distribution, and user check points. "
        "Use these Korean score terms consistently: 적합도, 지원 가능성, 판단 근거 충분도. "
        "If hasMatchPreferences is false, say that all postings were analyzed because no preference condition was selected; do not say '20 out of 20 were filtered'. "
        "If you mention semantic similarity, phrase it cautiously as '일정 수준의 의미 유사도' unless the JSON explicitly provides a stronger basis. "
        "Return exactly one JSON object with this shape: "
        "{\"description\":\"2-3 Korean sentences\","
        "\"strongSignals\":[\"reason 1\",\"reason 2\"],"
        "\"checkPoints\":[\"thing to check 1\",\"thing to check 2\"],"
        "\"nextAction\":\"recommended next action\"}.\n\n"
        f"Matching result JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    )

    generate_content_body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 700,
            "responseMimeType": "application/json",
        },
    }

    for model in models:
        model_id = model.replace("models/", "").strip("/")
        requests = [
            (
                "interactions",
                "https://generativelanguage.googleapis.com/v1beta/interactions",
                {"model": model_id, "input": prompt, "store": False},
            ),
            (
                "generateContent",
                "https://generativelanguage.googleapis.com/v1beta/models/"
                + urllib.parse.quote(model_id, safe="")
                + ":generateContent",
                generate_content_body,
            ),
        ]

        for api_name, url, request_body in requests:
            try:
                print(f"[gemini-summary] {model_id} {api_name} 시도")
                request_obj = urllib.request.Request(
                    url,
                    data=json.dumps(request_body).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": api_key,
                    },
                    method="POST",
                )

                with urllib.request.urlopen(request_obj, timeout=15) as response:
                    response_data = json.loads(response.read().decode("utf-8"))

                parsed = extract_json_object(extract_gemini_text(response_data))

                if not isinstance(parsed, dict):
                    print(f"[gemini-summary] {model_id} {api_name} JSON 파싱 실패")
                    continue

                print(f"[gemini-summary] {model_id} {api_name} 생성 성공")

                return {
                    "description": str(parsed.get("description", "")).strip(),
                    "strongSignals": clean_list(parsed.get("strongSignals"))[:3],
                    "checkPoints": clean_list(parsed.get("checkPoints"))[:3],
                    "nextAction": str(parsed.get("nextAction", "")).strip(),
                    "source": "gemini",
                    "model": model_id,
                }
            except urllib.error.HTTPError as error:
                try:
                    detail = error.read().decode("utf-8")
                except Exception:
                    detail = str(error)

                print(f"[gemini-summary] {model_id} {api_name} 생성 실패:", error, detail[:300])
                continue
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError) as error:
                print(f"[gemini-summary] {model_id} {api_name} 생성 실패:", error)
                continue

    return None


def attach_ai_summary(groups):
    ai_summary = generate_gemini_ai_summary(groups)

    if ai_summary:
        groups["aiSummary"] = ai_summary
    else:
        print("[gemini-summary] fallback to rule-based summary")

    return groups


def return_cached_result(cached_result, user_id=""):
    groups = normalize_matching_groups({
        "matches": cached_result.get("matches", []),
        "topFitMatches": cached_result.get("topFitMatches", []),
        "topAccessibleMatches": cached_result.get("topAccessibleMatches", []),
        "topConfidenceMatches": cached_result.get("topConfidenceMatches", []),
        "matchPreferences": cached_result.get("matchPreferences", {}),
        "totalJobCount": cached_result.get("totalJobCount"),
        "filteredJobCount": cached_result.get("filteredJobCount"),
        "aiSummary": cached_result.get("aiSummary", {}),
    })

    if not groups.get("aiSummary"):
        groups = attach_ai_summary(groups)

    save_matching_result(
        db=db,
        resume_id=cached_result["resumeId"],
        user_id=user_id or cached_result.get("userId", ""),
        matches=groups["matches"],
        top_fit_matches=groups["topFitMatches"],
        top_accessible_matches=groups["topAccessibleMatches"],
        top_confidence_matches=groups["topConfidenceMatches"],
        match_preferences=groups.get("matchPreferences", {}),
        total_job_count=groups.get("totalJobCount"),
        filtered_job_count=groups.get("filteredJobCount"),
        ai_summary=groups.get("aiSummary", {}),
    )

    return jsonify({
        "message": "??λ맂 留ㅼ묶 寃곌낵 議고쉶 ?꾨즺",
        "resumeId": cached_result["resumeId"],
        "matches": groups["topFitMatches"],
        "topFitMatches": groups["topFitMatches"],
        "topAccessibleMatches": groups["topAccessibleMatches"],
        "topConfidenceMatches": groups["topConfidenceMatches"],
        "matchPreferences": groups.get("matchPreferences", {}),
        "totalJobCount": groups.get("totalJobCount"),
        "filteredJobCount": groups.get("filteredJobCount"),
        "aiSummary": groups.get("aiSummary", {}),
        "matchCount": len(groups["matches"] or []),
        "cached": True,
        "updatedAt": cached_result.get("updatedAt", ""),
    })


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Python OCR server is running"
    })


@app.route("/process-resume", methods=["POST"])
def process_resume():
    try:
        data = request.get_json() or {}

        doc_id = data.get("docId") or data.get("resumeId")
        force_refresh = bool(data.get("forceRefresh", False))

        if not doc_id:
            return jsonify({"error": "docId is required."}), 400

        print("[process-resume] request doc_id:", doc_id)
        print("[process-resume] force_refresh:", force_refresh)

        # Return cached matching results unless the client explicitly asks for refresh.
        if not force_refresh:
            cached_result = get_matching_result(db, doc_id)

            if cached_result:
                print("[process-resume] return cached matching result")
                return jsonify({
                    "message": "Cached matching result returned",
                    "resumeId": doc_id,
                    "groups": cached_result,
                    "fromCache": True,
                })

        # Load resume document.
        resume_ref = db.collection("resumes").document(doc_id)
        resume_snap = resume_ref.get()

        if not resume_snap.exists:
            return jsonify({"error": "Resume not found."}), 404

        resume_data = resume_snap.to_dict() or {}

        # Run OCR/structuring only when resume analysis does not exist yet.
        has_analysis = bool(
            resume_data.get("effectiveAnalysis")
            or resume_data.get("originalAnalysis")
            or resume_data.get("resume")
        )

        if not has_analysis:
            print("[process-resume] no resume analysis found; run OCR/structuring")
            resume_id = process_resume_by_doc_id(doc_id)
        else:
            print("[process-resume] use existing resume analysis")
            resume_id = doc_id

        # Run matching with latest resume analysis and current job postings.
        print("[process-resume] matching started")
        groups = process_matching_groups_by_resume_id(resume_id, limit=5)
        groups = normalize_matching_groups(groups)
        groups = attach_ai_summary(groups)

        # Re-read latest resume state before saving matching result.
        latest_resume_snap = db.collection("resumes").document(resume_id).get()
        latest_resume_data = latest_resume_snap.to_dict() or {}

        analysis_source = "edited" if latest_resume_data.get("isAnalysisEdited") else "original"
        resume_analysis_version = latest_resume_data.get("analysisVersion", 1)
        is_analysis_edited = latest_resume_data.get("isAnalysisEdited", False)

        print("[process-resume] saving Firestore matching_results")

        save_matching_result(
            db=db,
            resume_id=resume_id,
            user_id=latest_resume_data.get("userId", ""),
            matches=groups.get("matches", []),
            top_fit_matches=groups.get("topFitMatches", []),
            top_accessible_matches=groups.get("topAccessibleMatches", []),
            top_confidence_matches=groups.get("topConfidenceMatches", []),
            match_preferences=groups.get("matchPreferences", {}),
            total_job_count=groups.get("totalJobCount"),
            filtered_job_count=groups.get("filteredJobCount"),
            ai_summary=groups.get("aiSummary", {}),
            analysis_source=analysis_source,
            resume_analysis_version=resume_analysis_version,
            is_analysis_edited=is_analysis_edited,
        )

        print("[process-resume] saved Firestore matching_results")

        return jsonify({
            "message": "Matching completed with latest data",
            "resumeId": resume_id,
            "fromCache": False,
            "analysisSource": analysis_source,
            "resumeAnalysisVersion": resume_analysis_version,
            "isAnalysisEdited": is_analysis_edited,
            "groups": groups,
        })

    except Exception as e:
        print("[process-resume] error:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/matching-results/<resume_id>", methods=["GET"])
def read_matching_result(resume_id):
    try:
        result = get_matching_result(db, resume_id)

        if not result:
            return jsonify({
                "error": "??λ맂 留ㅼ묶 寃곌낵媛 ?놁뒿?덈떎."
            }), 404

        groups = normalize_matching_groups({
            "matches": result.get("matches", []),
            "topFitMatches": result.get("topFitMatches", []),
            "topAccessibleMatches": result.get("topAccessibleMatches", []),
            "topConfidenceMatches": result.get("topConfidenceMatches", []),
            "matchPreferences": result.get("matchPreferences", {}),
            "totalJobCount": result.get("totalJobCount"),
            "filteredJobCount": result.get("filteredJobCount"),
            "aiSummary": result.get("aiSummary", {}),
        })

        if not groups.get("aiSummary"):
            groups = attach_ai_summary(groups)

        save_matching_result(
            db=db,
            resume_id=result["resumeId"],
            matches=groups["matches"],
            top_fit_matches=groups["topFitMatches"],
            top_accessible_matches=groups["topAccessibleMatches"],
            top_confidence_matches=groups["topConfidenceMatches"],
            match_preferences=groups.get("matchPreferences", {}),
            total_job_count=groups.get("totalJobCount"),
            filtered_job_count=groups.get("filteredJobCount"),
            ai_summary=groups.get("aiSummary", {}),
        )

        return jsonify({
            "resumeId": result["resumeId"],
            "matches": groups["topFitMatches"],
            "topFitMatches": groups["topFitMatches"],
            "topAccessibleMatches": groups["topAccessibleMatches"],
            "topConfidenceMatches": groups["topConfidenceMatches"],
            "matchPreferences": groups.get("matchPreferences", {}),
            "totalJobCount": groups.get("totalJobCount"),
            "filteredJobCount": groups.get("filteredJobCount"),
            "aiSummary": groups.get("aiSummary", {}),
            "matchCount": len(groups["matches"] or []),
            "status": result.get("status", "DONE"),
            "updatedAt": result.get("updatedAt", ""),
        })

    except Exception as e:
        print("\n[留ㅼ묶 寃곌낵 議고쉶 ?ㅽ뙣]")
        print(traceback.format_exc())

        return jsonify({
            "error": str(e)
        }), 500


@app.route("/process-one-match", methods=["POST"])
def process_one_match():
    try:
        data = request.get_json(silent=True) or {}

        doc_id = data.get("docId")
        job_id = data.get("jobId")
        user_id = data.get("userId")

        if not doc_id:
            return jsonify({
                "error": "docId媛 ?꾩슂?⑸땲??"
            }), 400

        if not job_id:
            return jsonify({
                "error": "jobId媛 ?꾩슂?⑸땲??"
            }), 400

        if not user_id:
            return jsonify({
                "error": "濡쒓렇?몄씠 ?꾩슂?⑸땲??",
                "message": "濡쒓렇?몄씠 ?꾩슂?⑸땲??"
            }), 401

        result = process_matching_one_by_ids(doc_id, job_id)
        result = fill_missing_company_names(db, [result])[0]

        return jsonify({
            "message": "1:1 留ㅼ묶 ?꾨즺",
            "resumeId": doc_id,
            "jobId": job_id,
            "match": result
        })

    except Exception as e:
        print("\n[1:1 留ㅼ묶 泥섎━ ?ㅽ뙣]")
        print(traceback.format_exc())

        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
