import os

import firebase_admin
from firebase_admin import credentials, firestore, storage


def init_firebase(firebase_key_path: str = "config/firebase_key.json"):
    if not firebase_admin._apps:

        # 1. 기존 로컬 방식 우선
        if os.path.exists(firebase_key_path):
            cred = credentials.Certificate(firebase_key_path)

        # 2. Render 등 배포 환경에서는 환경변수 사용
        else:
            project_id = os.getenv("FIREBASE_PROJECT_ID")
            client_email = os.getenv("FIREBASE_CLIENT_EMAIL")
            private_key = os.getenv("FIREBASE_PRIVATE_KEY")

            if not project_id or not client_email or not private_key:
                raise RuntimeError(
                    "Firebase 인증 정보가 없습니다. "
                    "firebase_key.json 또는 Firebase 환경변수를 확인하세요."
                )

            service_account_info = {
                "type": "service_account",
                "project_id": project_id,
                "client_email": client_email,
                "private_key": private_key.replace("\\n", "\n"),
                "token_uri": "https://oauth2.googleapis.com/token",
            }

            cred = credentials.Certificate(service_account_info)

        storage_bucket = os.getenv(
            "FIREBASE_STORAGE_BUCKET",
            "jobpick.firebasestorage.app"
        )

        firebase_admin.initialize_app(
            cred,
            {
                "storageBucket": storage_bucket
            }
        )

    db = firestore.client()
    bucket = storage.bucket()

    return db, bucket