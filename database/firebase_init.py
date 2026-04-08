import firebase_admin
from firebase_admin import credentials, firestore, storage

def init_firebase(firebase_key_path):
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_key_path)
        firebase_admin.initialize_app(cred, {
            "storageBucket": "jobpick.firebasestorage.app",
        })

    db = firestore.client()
    bucket = storage.bucket()
    return db, bucket