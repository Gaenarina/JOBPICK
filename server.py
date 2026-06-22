from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback

from database.firebase_init import init_firebase
from database.firebase_save_matching import (
    save_matching_result,
    get_matching_result,
)

from main.main_resume import process_resume_by_doc_id
from main.main_matching import process_matching_groups_by_resume_id
from main.main_matching_one import process_matching_one_by_ids

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
    }


def return_cached_result(cached_result, user_id=""):
    groups = normalize_matching_groups({
        "matches": cached_result.get("matches", []),
        "topFitMatches": cached_result.get("topFitMatches", []),
        "topAccessibleMatches": cached_result.get("topAccessibleMatches", []),
        "topConfidenceMatches": cached_result.get("topConfidenceMatches", []),
    })

    save_matching_result(
        db=db,
        resume_id=cached_result["resumeId"],
        user_id=user_id or cached_result.get("userId", ""),
        matches=groups["matches"],
        top_fit_matches=groups["topFitMatches"],
        top_accessible_matches=groups["topAccessibleMatches"],
        top_confidence_matches=groups["topConfidenceMatches"],
    )

    return jsonify({
        "message": "저장된 매칭 결과 조회 완료",
        "resumeId": cached_result["resumeId"],
        "matches": groups["topFitMatches"],
        "topFitMatches": groups["topFitMatches"],
        "topAccessibleMatches": groups["topAccessibleMatches"],
        "topConfidenceMatches": groups["topConfidenceMatches"],
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
            return jsonify({"error": "docId가 없습니다."}), 400

        print("[process-resume] 요청 doc_id:", doc_id)
        print("[process-resume] force_refresh:", force_refresh)

        # forceRefresh가 아닐 때만 기존 결과 반환
        if not force_refresh:
            cached_result = get_matching_result(db, doc_id)

            if cached_result:
                print("[process-resume] 기존 매칭 결과 반환")
                return jsonify({
                    "message": "기존 매칭 결과 반환",
                    "resumeId": doc_id,
                    "groups": cached_result,
                    "fromCache": True,
                })

        # 이력서 문서 확인
        resume_ref = db.collection("resumes").document(doc_id)
        resume_snap = resume_ref.get()

        if not resume_snap.exists:
            return jsonify({"error": "이력서를 찾을 수 없습니다."}), 404

        resume_data = resume_snap.to_dict() or {}

        # 아직 이력서 분석이 안 된 경우에만 OCR/구조화 실행
        has_analysis = bool(
            resume_data.get("effectiveAnalysis")
            or resume_data.get("originalAnalysis")
            or resume_data.get("resume")
        )

        if not has_analysis:
            print("[process-resume] 이력서 분석 결과 없음 → OCR/구조화 실행")
            resume_id = process_resume_by_doc_id(doc_id)
        else:
            print("[process-resume] 기존 이력서 분석 결과 사용")
            resume_id = doc_id

        # 항상 최신 공고 DB + 최신 이력서 분석 기준으로 재매칭
        print("[process-resume] 최신 기준 매칭 시작")
        groups = process_matching_groups_by_resume_id(resume_id, limit=5)
        groups = normalize_matching_groups(groups)

        # 이력서 최신 상태 다시 읽기
        latest_resume_snap = db.collection("resumes").document(resume_id).get()
        latest_resume_data = latest_resume_snap.to_dict() or {}

        analysis_source = "edited" if latest_resume_data.get("isAnalysisEdited") else "original"
        resume_analysis_version = latest_resume_data.get("analysisVersion", 1)
        is_analysis_edited = latest_resume_data.get("isAnalysisEdited", False)

        print("[process-resume] Firestore matching_results 저장 시작")

        save_matching_result(
            db=db,
            resume_id=resume_id,
            user_id=latest_resume_data.get("userId", ""),
            matches=groups.get("matches", []),
            top_fit_matches=groups.get("topFitMatches", []),
            top_accessible_matches=groups.get("topAccessibleMatches", []),
            top_confidence_matches=groups.get("topConfidenceMatches", []),
            analysis_source=analysis_source,
            resume_analysis_version=resume_analysis_version,
            is_analysis_edited=is_analysis_edited,
        )

        print("[process-resume] Firestore matching_results 저장 완료")

        return jsonify({
            "message": "최신 정보로 매칭 완료",
            "resumeId": resume_id,
            "fromCache": False,
            "analysisSource": analysis_source,
            "resumeAnalysisVersion": resume_analysis_version,
            "isAnalysisEdited": is_analysis_edited,
            "groups": groups,
        })

    except Exception as e:
        print("[process-resume] 오류:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/matching-results/<resume_id>", methods=["GET"])
def read_matching_result(resume_id):
    try:
        result = get_matching_result(db, resume_id)

        if not result:
            return jsonify({
                "error": "저장된 매칭 결과가 없습니다."
            }), 404

        groups = normalize_matching_groups({
            "matches": result.get("matches", []),
            "topFitMatches": result.get("topFitMatches", []),
            "topAccessibleMatches": result.get("topAccessibleMatches", []),
            "topConfidenceMatches": result.get("topConfidenceMatches", []),
        })

        save_matching_result(
            db=db,
            resume_id=result["resumeId"],
            matches=groups["matches"],
            top_fit_matches=groups["topFitMatches"],
            top_accessible_matches=groups["topAccessibleMatches"],
            top_confidence_matches=groups["topConfidenceMatches"],
        )

        return jsonify({
            "resumeId": result["resumeId"],
            "matches": groups["topFitMatches"],
            "topFitMatches": groups["topFitMatches"],
            "topAccessibleMatches": groups["topAccessibleMatches"],
            "topConfidenceMatches": groups["topConfidenceMatches"],
            "matchCount": len(groups["matches"] or []),
            "status": result.get("status", "DONE"),
            "updatedAt": result.get("updatedAt", ""),
        })

    except Exception as e:
        print("\n[매칭 결과 조회 실패]")
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
                "error": "docId가 필요합니다."
            }), 400

        if not job_id:
            return jsonify({
                "error": "jobId가 필요합니다."
            }), 400

        if not user_id:
            return jsonify({
                "error": "로그인이 필요합니다.",
                "message": "로그인이 필요합니다."
            }), 401

        result = process_matching_one_by_ids(doc_id, job_id)
        result = fill_missing_company_names(db, [result])[0]

        return jsonify({
            "message": "1:1 매칭 완료",
            "resumeId": doc_id,
            "jobId": job_id,
            "match": result
        })

    except Exception as e:
        print("\n[1:1 매칭 처리 실패]")
        print(traceback.format_exc())

        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)