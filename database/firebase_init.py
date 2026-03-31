import firebase_admin
from firebase_admin import credentials, firestore


def init_firebase(key_path: str = "config/firebase_key.json"):
    """
    Firebase Admin SDK 초기화 후 Firestore client 반환
    """

    # 이미 초기화된 경우 중복 실행 방지
    if not firebase_admin._apps:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)

    db = firestore.client()
    return db