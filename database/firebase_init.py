import firebase_admin
from firebase_admin import credentials, firestore, storage


def init_firebase(key_path: str = "config/firebase_key.json"):
    """
    Firebase Admin SDK 초기화 후 Firestore client와 Storage bucket 반환
    """

    if not firebase_admin._apps:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred, {
            "storageBucket": "jobpick.firebasestorage.app"
        })

    db = firestore.client()
    bucket = storage.bucket()

    return db, bucket