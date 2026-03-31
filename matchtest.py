from sentence_transformers import SentenceTransformer, util

# SBERT 모델 로드
model = SentenceTransformer("jhgan/ko-sroberta-multitask")

# -----------------------------
# 가중치 / 패널티 설정
# 공기업 평가표 참고 후 재구성
# -----------------------------
WEIGHTS = {
    "skills": 30,
    "experience": 20,
    "education": 10,
    "certifications": 10,
    "qualifications_rule": 10,
    "semantic_responsibilities": 15,
    "semantic_qualifications": 5
}

PENALTIES = {
    "education_mismatch": 15,
    "skill_mismatch": 20,
    "experience_mismatch": 20,
    "qualification_mismatch": 25
}

# -----------------------------
# 채용공고 예시
# -----------------------------
job_posting = {
    "skills": {
        "required": ["Python", "React", "SQL"],
        "preferred": ["AWS", "Docker"]
    },
    "responsibilities": [
        "사용자 맞춤형 추천 시스템 개발",
        "데이터 분석 및 시각화"
    ],
    "qualifications": {
        "required": ["컴퓨터 관련 전공", "팀 프로젝트 경험"],
        "preferred": ["협업 능력", "Git 사용 경험"]
    },
    "education": "대졸 이상",
    "experience": {"minYears": 2},
    "certifications": ["정보처리기사"]
}

# -----------------------------
# 이력서 예시 1: 패널티 적용
# -----------------------------
resume_penalty = {
    "skills": ["Python", "JavaScript"],
    "education": "전문학사",
    "experienceYears": 1,
    "certifications": ["정보처리기사"],
    "projects": [
        "개인화 추천 알고리즘 프로젝트 수행",
        "웹 데이터 시각화 경험"
    ]
}

# -----------------------------
# 이력서 예시 2: 패널티 없음
# -----------------------------
resume_no_penalty = {
    "skills": ["Python", "React", "SQL"],
    "education": "학사",
    "experienceYears": 3,
    "certifications": ["정보처리기사"],
    "projects": [
        "사용자 맞춤형 추천 시스템 개발 프로젝트",
        "데이터 분석 및 시각화 경험"
    ]
}

# -----------------------------
# 학력 정규화
# -----------------------------
def normalize_education_level(text):
    if not text:
        return "고졸"

    text = text.strip()

    if "박사" in text:
        return "박사"
    elif "석사" in text:
        return "석사"
    elif "대졸" in text or "학사" in text:
        return "학사"
    elif "전문학사" in text:
        return "전문학사"
    elif "고졸" in text:
        return "고졸"
    else:
        return "고졸"


def education_to_index(level):
    education_levels = ["고졸", "전문학사", "학사", "석사", "박사"]
    return education_levels.index(level)


# -----------------------------
# 자격요건 룰 기반 점수
# -----------------------------
def calculate_qualification_rule_score(job, resume):
    required_qualifications = job.get("qualifications", {}).get("required", [])
    resume_text = " ".join(resume.get("projects", []))

    matched_qualifications = []
    for qual in required_qualifications:
        if qual in resume_text:
            matched_qualifications.append(qual)

    if required_qualifications:
        qualification_score = (
            len(matched_qualifications) / len(required_qualifications)
        ) * WEIGHTS["qualifications_rule"]
    else:
        qualification_score = 0

    return qualification_score, matched_qualifications, len(required_qualifications)


# -----------------------------
# 룰 기반 점수
# -----------------------------
def calculate_rule_score(job, resume):
    required_skills = job.get("skills", {}).get("required", [])
    skill_match_count = sum(skill in resume.get("skills", []) for skill in required_skills)
    skill_score = (
        (skill_match_count / len(required_skills)) * WEIGHTS["skills"]
        if required_skills else 0
    )

    job_edu_level = normalize_education_level(job.get("education", ""))
    resume_edu_level = normalize_education_level(resume.get("education", ""))
    job_edu_idx = education_to_index(job_edu_level)
    resume_edu_idx = education_to_index(resume_edu_level)
    edu_score = WEIGHTS["education"] if resume_edu_idx >= job_edu_idx else 0

    min_exp = job.get("experience", {}).get("minYears", 0)
    exp_years = resume.get("experienceYears", 0)
    exp_score = min(exp_years / max(min_exp, 1), 1.0) * WEIGHTS["experience"]

    certs_required = job.get("certifications", [])
    cert_match_count = sum(cert in resume.get("certifications", []) for cert in certs_required)
    cert_score = (
        (cert_match_count / len(certs_required)) * WEIGHTS["certifications"]
        if certs_required else 0
    )

    qual_rule_score, matched_quals, total_quals = calculate_qualification_rule_score(job, resume)

    total_rule_score = skill_score + edu_score + exp_score + cert_score + qual_rule_score

    details = {
        "skill_score": skill_score,
        "skill_match_count": skill_match_count,
        "skill_total_count": len(required_skills),
        "edu_score": edu_score,
        "job_edu_level": job_edu_level,
        "resume_edu_level": resume_edu_level,
        "exp_score": exp_score,
        "min_exp": min_exp,
        "resume_exp": exp_years,
        "cert_score": cert_score,
        "cert_match_count": cert_match_count,
        "cert_total_count": len(certs_required),
        "qual_rule_score": qual_rule_score,
        "matched_quals": matched_quals,
        "qual_total_count": total_quals
    }

    return total_rule_score, details


# -----------------------------
# 의미 기반 점수
# -----------------------------
def calculate_semantic_score(job, resume):
    job_resp_text = " ".join(job.get("responsibilities", []))
    resume_proj_text = " ".join(resume.get("projects", []))

    emb_resp = model.encode(job_resp_text, convert_to_tensor=True)
    emb_proj = model.encode(resume_proj_text, convert_to_tensor=True)
    resp_sim = util.pytorch_cos_sim(emb_resp, emb_proj).item()
    resp_score = resp_sim * WEIGHTS["semantic_responsibilities"]

    job_qual_text = " ".join(job.get("qualifications", {}).get("required", []))
    emb_qual = model.encode(job_qual_text, convert_to_tensor=True)
    qual_sim = util.pytorch_cos_sim(emb_qual, emb_proj).item()
    qual_score = qual_sim * WEIGHTS["semantic_qualifications"]

    total_semantic_score = resp_score + qual_score

    details = {
        "resp_sim": resp_sim,
        "resp_score": resp_score,
        "qual_sim": qual_sim,
        "qual_score": qual_score
    }

    return total_semantic_score, details


# -----------------------------
# 패널티
# -----------------------------
def calculate_penalty(job, resume):
    penalty = 0
    reasons = []

    job_edu_level = normalize_education_level(job.get("education", ""))
    resume_edu_level = normalize_education_level(resume.get("education", ""))
    if education_to_index(resume_edu_level) < education_to_index(job_edu_level):
        penalty += PENALTIES["education_mismatch"]
        reasons.append(f"학력 미충족: -{PENALTIES['education_mismatch']}")

    required_skills = job.get("skills", {}).get("required", [])
    match_count = sum(skill in resume.get("skills", []) for skill in required_skills)
    if required_skills and (match_count / len(required_skills) < 0.5):
        penalty += PENALTIES["skill_mismatch"]
        reasons.append(f"필수 기술 50% 미만 충족: -{PENALTIES['skill_mismatch']}")

    min_exp = job.get("experience", {}).get("minYears", 0)
    if resume.get("experienceYears", 0) < min_exp:
        penalty += PENALTIES["experience_mismatch"]
        reasons.append(f"경력 미충족: -{PENALTIES['experience_mismatch']}")

    _, matched_quals, total_quals = calculate_qualification_rule_score(job, resume)
    if total_quals > 0 and len(matched_quals) == 0:
        penalty += PENALTIES["qualification_mismatch"]
        reasons.append(f"필수 자격요건 미충족: -{PENALTIES['qualification_mismatch']}")

    return penalty, reasons


# -----------------------------
# 최종 점수 계산 및 출력
# -----------------------------
def calculate_full_score(job, resume, label="이력서"):
    print(f"\n=== {label} 계산 과정 ===")

    rule_total, rule_details = calculate_rule_score(job, resume)
    print("[룰 기반]")
    print(
        f"- 기술 점수: {rule_details['skill_score']:.2f}/{WEIGHTS['skills']} "
        f"(일치 {rule_details['skill_match_count']}/{rule_details['skill_total_count']})"
    )
    print(
        f"- 학력 점수: {rule_details['edu_score']:.2f}/{WEIGHTS['education']} "
        f"(공고: {rule_details['job_edu_level']}, 이력서: {rule_details['resume_edu_level']})"
    )
    print(
        f"- 경력 점수: {rule_details['exp_score']:.2f}/{WEIGHTS['experience']} "
        f"(지원자 {rule_details['resume_exp']}년 / 요구 {rule_details['min_exp']}년)"
    )
    print(
        f"- 자격증 점수: {rule_details['cert_score']:.2f}/{WEIGHTS['certifications']} "
        f"(일치 {rule_details['cert_match_count']}/{rule_details['cert_total_count']})"
    )
    print(
        f"- 자격요건 룰 기반 점수: {rule_details['qual_rule_score']:.2f}/{WEIGHTS['qualifications_rule']} "
        f"(일치 {len(rule_details['matched_quals'])}/{rule_details['qual_total_count']})"
    )
    print(f"룰 기반 점수 합계: {rule_total:.2f}/80")

    semantic_total, semantic_details = calculate_semantic_score(job, resume)
    print("[의미 기반]")
    print(
        f"- responsibilities 유사도 점수: {semantic_details['resp_score']:.2f}/"
        f"{WEIGHTS['semantic_responsibilities']} "
        f"(유사도 {semantic_details['resp_sim']:.4f})"
    )
    print(
        f"- qualifications 유사도 점수: {semantic_details['qual_score']:.2f}/"
        f"{WEIGHTS['semantic_qualifications']} "
        f"(유사도 {semantic_details['qual_sim']:.4f})"
    )
    print(f"의미 기반 점수 합계: {semantic_total:.2f}/20")

    penalty, reasons = calculate_penalty(job, resume)
    print("[패널티]")
    if reasons:
        for reason in reasons:
            print(f"- {reason}")
    else:
        print("- 패널티 없음")
    print(f"총 패널티 점수: {penalty:.2f}")

    final_without_penalty = rule_total + semantic_total
    final_with_penalty = max(final_without_penalty - penalty, 0)

    print("[최종 점수]")
    print(f"- 패널티 적용: {final_with_penalty:.2f}/100")
    print(f"- 패널티 미적용: {final_without_penalty:.2f}/100")

    return final_with_penalty, final_without_penalty


# -----------------------------
# 실행
# -----------------------------
calculate_full_score(job_posting, resume_penalty, label="패널티 적용 이력서")
calculate_full_score(job_posting, resume_no_penalty, label="패널티 미적용 이력서")