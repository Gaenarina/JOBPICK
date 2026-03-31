import chromadb
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("jhgan/ko-sroberta-multitask")

client = chromadb.PersistentClient(path="./chroma_db")
client.delete_collection("resume")
#collection = client.get_or_create_collection(name="resume")

collection = client.get_or_create_collection(
    name="resume",
    metadata={"hnsw:space": "cosine"}
)

# ex 이력
text = "Spring 기반 백엔드 개발 3년"

embedding = model.encode(text).tolist()

collection.add(
    ids=["resume_1"],
    embeddings=[embedding],
    documents=[text]
)

# ex 공고
query = "Spring 백엔드 개발자 모집"

query_embedding = model.encode(query).tolist()

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=1
)


print(results)
print(collection.count())
data = collection.get()
# data = collection.get(include=["embeddings", "documents"])
print(data)