from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback

from main.main_resume import process_resume_by_doc_id
from main.main_matching import process_matching_by_resume_id

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Python OCR server is running"
    })


@app.route("/process-resume", methods=["POST"])
def process_resume():
    try:
        data = request.get_json(silent=True) or {}
        doc_id = data.get("docId")

        if not doc_id:
            return jsonify({
                "error": "docId가 필요합니다."
            }), 400

        resume_id = process_resume_by_doc_id(doc_id)
        matches = process_matching_by_resume_id(resume_id)

        return jsonify({
            "message": "처리 완료",
            "resumeId": resume_id,
            "matches": matches
        })

    except Exception as e:
        print("\n[Python 서버 처리 실패]")
        print(traceback.format_exc())

        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)