'''
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# 한국어 특화 모델
model = SentenceTransformer("jhgan/ko-sroberta-multitask")

# 테스트 문장
sentences = ["예쁘다", "못생겼다"]

# 임베딩
embeddings = model.encode(sentences)

# 유사도 계산
similarity = cosine_similarity([embeddings[0]], [embeddings[1]])
print("문장 유사도:", similarity[0][0])
print("임베딩 shape:", embeddings.shape)
'''

# =========================================
# 한국어 채용공고 ↔ 지원서 매칭 예제
# =========================================

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# 한국어 특화 SBERT 모델 불러오기
model = SentenceTransformer("jhgan/ko-sroberta-multitask")

# 예시 채용공고 문장 (직무 요구 기술)
job_posting = [
    "Python을 활용한 데이터 분석 경험",
    "머신러닝 모델 개발 경험",
    "협업과 커뮤니케이션 능력"
]

# 예시 지원서 문장 (경험/기술)
resume = [
    "Python으로 데이터 분석 프로젝트 수행",
    "딥러닝 모델 구현 경험 있음",
    "팀 프로젝트를 통한 협업 경험"
]

# 임베딩 생성
job_embeddings = model.encode(job_posting)
resume_embeddings = model.encode(resume)

# 공고 ↔ 지원서 문장별 유사도 계산
similarity_matrix = cosine_similarity(job_embeddings, resume_embeddings)

print("공고-지원서 문장 유사도 행렬 (job x resume):")
print(np.round(similarity_matrix, 3))  # 소수점 3자리로 보기 좋게

# 문장별 최대 유사도 기반 매칭 점수 계산
# 각 공고 문장마다 가장 유사한 지원서 문장 선택 후 평균
max_sim_per_job = similarity_matrix.max(axis=1)
matching_score = max_sim_per_job.mean()

print("\n 공고-지원서 종합 매칭 점수:", round(matching_score, 3))