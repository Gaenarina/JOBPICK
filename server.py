from flask import Flask, request, jsonify
import traceback
from main.main_resume import process_resume_by_doc_id

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Python OCR server is running"

@app.route("/process-resume", methods=["POST"])
def process_resume():
    data = request.get_json()
    doc_id = data.get("docId")

    try:
        process_resume_by_doc_id(doc_id)
        return jsonify({"message": "처리 완료"})
    except Exception as e:
        print("\n[Python 서버 처리 실패]")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=8000)