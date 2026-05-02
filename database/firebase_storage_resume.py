import os


def download_resume_from_storage(bucket, storage_path: str, local_dir: str = "temp") -> str:
    os.makedirs(local_dir, exist_ok=True)

    filename = os.path.basename(storage_path)
    local_path = os.path.join(local_dir, filename)

    blob = bucket.blob(storage_path)
    blob.download_to_filename(local_path)

    return local_path