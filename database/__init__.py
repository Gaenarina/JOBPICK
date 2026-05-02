import firebase_admin
from firebase_admin import credentials, firestore, storage

def init_firebase(firebase_key_path: str, storage_bucket: str):
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_key_path)
        firebase_admin.initialize_app(cred, {
            "storageBucket": storage_bucket
        })

    db = firestore.client()
    bucket = storage.bucket()
    return db, bucket