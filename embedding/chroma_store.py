import chromadb


CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "resume_job_match"


def get_chroma_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    return collection


def upsert_document(collection, doc_id, text, metadata):
    collection.upsert(
        ids=[doc_id],
        documents=[text],
        metadatas=[metadata]
    )


def query_similar(collection, query_text, n_results=5):
    return collection.query(
        query_texts=[query_text],
        n_results=n_results
    )