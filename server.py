from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback

from database.firebase_init import init_firebase
from database.firebase_save_matching import (
    save_matching_result,
    get_matching_result,
)

from main.main_resume import process_resume_by_doc_id
from main.main_matching import process_matching_by_resume_id

app = Flask(__name__)
CORS(app)

db, bucket = init_firebase("config/firebase_key.json")


def get_match_score(item):
    if not isinstance(item, dict):
        return 0

    score_keys = [
        "matchRate",
        "finalScore",
        "final_score",
        "score",
        "matchScore",
        "match_score",
        "similarity",
        "totalScore",
        "total_score",
    ]

    for key in score_keys:
        value = item.get(key)

        try:
            value = float(value)

            if 0 < value <= 1:
                return value * 100

            return value
        except:
            pass

    return 0


def get_top_matches(matches, limit=5):
    return sorted(
        matches or [],
        key=get_match_score,
        reverse=True
    )[:limit]


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


def return_cached_result(cached_result):
    matches = fill_missing_company_names(
        db,
        cached_result.get("matches", [])
    )
    matches = get_top_matches(matches, limit=5)

    save_matching_result(
        db=db,
        resume_id=cached_result["resumeId"],
        matches=matches,
    )

    return jsonify({
        "message": "저장된 매칭 결과 조회 완료",
        "resumeId": cached_result["resumeId"],
        "matches": matches,
        "matchCount": len(matches or []),
        "cached": True,
        "updatedAt": cached_result["updatedAt"],
    })


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Python OCR server is running"
    })


@app.route("/process-resume", methods=["POST"])
def process_resume():
    try:
        print("\n========== /process-resume 요청 시작 ==========")

        data = request.get_json(silent=True) or {}
        doc_id = data.get("docId")
        force = data.get("force", False)

        print("[1] 받은 docId:", doc_id)
        print("[2] force:", force)

        if not doc_id:
            return jsonify({
                "error": "docId가 필요합니다."
            }), 400

        if not force:
            print("[3] 기존 매칭 결과 조회 시도:", doc_id)
            cached_result = get_matching_result(db, doc_id)

            if cached_result:
                print("[4] 기존 매칭 결과 있음. 재계산 안 함.")
                return return_cached_result(cached_result)

        print("[5] 이력서 처리 시작")
        resume_id = process_resume_by_doc_id(doc_id)
        print("[6] 이력서 처리 완료 resume_id:", resume_id)

        if not force:
            print("[7] resume_id 기준 기존 매칭 결과 조회:", resume_id)
            cached_result = get_matching_result(db, resume_id)

            if cached_result:
                print("[8] resume_id 기준 기존 매칭 결과 있음. 재계산 안 함.")
                return return_cached_result(cached_result)

        print("[9] 매칭 점수 계산 시작")
        matches = process_matching_by_resume_id(resume_id)
        matches = fill_missing_company_names(db, matches)
        matches = get_top_matches(matches, limit=5)

        print("[10] 매칭 점수 계산 완료")
        print("[11] matches 개수:", len(matches or []))

        print("[12] Firestore matching_results 저장 시작")
        save_matching_result(
            db=db,
            resume_id=resume_id,
            matches=matches,
        )
        print("[13] Firestore matching_results 저장 완료")

        print("========== /process-resume 요청 완료 ==========\n")

        return jsonify({
            "message": "처리 완료",
            "resumeId": resume_id,
            "matches": matches,
            "matchCount": len(matches or []),
            "cached": False,
        })

    except Exception as e:
        print("\n[Python 서버 처리 실패]")
        print(traceback.format_exc())

        return jsonify({
            "error": str(e)
        }), 500


@app.route("/matching-results/<resume_id>", methods=["GET"])
def read_matching_result(resume_id):
    try:
        result = get_matching_result(db, resume_id)

        if not result:
            return jsonify({
                "error": "저장된 매칭 결과가 없습니다."
            }), 404

        matches = fill_missing_company_names(
            db,
            result.get("matches", [])
        )
        matches = get_top_matches(matches, limit=5)

        save_matching_result(
            db=db,
            resume_id=result["resumeId"],
            matches=matches,
        )

        return jsonify({
            "resumeId": result["resumeId"],
            "matches": matches,
            "matchCount": len(matches or []),
            "status": result.get("status", "DONE"),
            "updatedAt": result.get("updatedAt", ""),
        })

    except Exception as e:
        print("\n[매칭 결과 조회 실패]")
        print(traceback.format_exc())

        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)