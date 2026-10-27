import os

import firebase_admin
from firebase_admin import credentials, firestore, storage


def init_firebase(firebase_key_path="config/firebase_key.json"):
    if not firebase_admin._apps:
        project_id = os.getenv("FIREBASE_PROJECT_ID")
        client_email = os.getenv("FIREBASE_CLIENT_EMAIL")
        private_key = os.getenv("FIREBASE_PRIVATE_KEY")

        if os.path.exists(firebase_key_path):
            cred = credentials.Certificate(firebase_key_path)

        elif project_id and client_email and private_key:
            service_account_info = {
                "type": "service_account",
                "project_id": project_id,
                "client_email": client_email,
                "private_key": private_key.replace("\\n", "\n"),
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            cred = credentials.Certificate(service_account_info)

        else:
            # Cloud Run 서비스 계정의 기본 인증 사용
            cred = credentials.ApplicationDefault()

        options = {
            "storageBucket": os.getenv(
                "FIREBASE_STORAGE_BUCKET",
                "jobpick.firebasestorage.app"
            )
        }

        if project_id:
            options["projectId"] = project_id

        firebase_admin.initialize_app(cred, options)

    db = firestore.client()
    bucket = storage.bucket()

    return db, bucket