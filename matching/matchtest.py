import re
from sentence_transformers import SentenceTransformer, util


model = SentenceTransformer("jhgan/ko-sroberta-multitask")


WEIGHTS = {
    "skills": 30,
    "experience": 20,
    "education": 10,
    "certifications": 10,
    "qualifications_rule": 10,
    "semantic_responsibilities": 15,
    "semantic_qualifications": 5
}


def normalize_text(text):
    if not text:
        return ""
    return str(text).replace("ㆍ", "").strip()


def normalize_education_level(text):
    if not text:
        return "고졸"

    text = str(text).strip()

    if "박사" in text:
        return "박사"
    elif "석사" in text:
        return "석사"
    elif "초대졸" in text or "전문학사" in text:
        return "전문학사"
    elif "대졸" in text or "학사" in text:
        return "학사"
    elif "고졸" in text:
        return "고졸"
    else:
        return "고졸"


def education_to_index(level):
    education_levels = ["고졸", "전문학사", "학사", "석사", "박사"]
    if level not in education_levels:
        return 0
    return education_levels.index(level)


def parse_experience_years(exp_text):
    if not exp_text:
        return 0

    text = str(exp_text)

    match = re.search(r"(\d+)\s*년", text)
    if match:
        return int(match.group(1))

    match = re.search(r"(\d+)\s*↑", text)
    if match:
        return int(match.group(1))

    return 0


def flatten_resume(firebase_resume_doc):
    resume_data = firebase_resume_doc.get("resume", {}).get("resumeData", {})

    skills_map = resume_data.get("skills", {})
    languages = skills_map.get("languages", [])
    frameworks = skills_map.get("frameworks", [])
    tools = skills_map.get("tools", [])
    etc = skills_map.get("etc", [])

    all_skills = []
    for skill_list in [languages, frameworks, tools, etc]:
        for item in skill_list:
            item = normalize_text(item)
            if item and item not in all_skills:
                all_skills.append(item)

    education_list = resume_data.get("education", [])
    highest_degree = "고졸"
    if education_list:
        degree_values = [normalize_education_level(edu.get("degree", "")) for edu in education_list]
        if degree_values:
            highest_degree = max(degree_values, key=education_to_index)

    certs = []
    for cert in resume_data.get("certifications", []):
        name = normalize_text(cert.get("name", ""))
        if name:
            certs.append(name)

    experience_texts = []
    total_months = 0

    for exp in resume_data.get("experience", []):
        org = normalize_text(exp.get("organization", ""))
        pos = normalize_text(exp.get("position", ""))
        start_date = normalize_text(exp.get("startDate", ""))
        end_date = normalize_text(exp.get("endDate", ""))
        resp_list = [normalize_text(x) for x in exp.get("responsibilities", []) if normalize_text(x)]

        joined = " / ".join([x for x in [org, pos, " ".join(resp_list)] if x])
        if joined:
            experience_texts.append(joined)

        if not start_date:
            continue

        try:
            start_year, start_month = map(int, start_date.split("-")[:2])

            if end_date == "현재":
                end_year, end_month = 2026, 4
            elif end_date:
                end_year, end_month = map(int, end_date.split("-")[:2])
            else:
                continue

            months = (end_year - start_year) * 12 + (end_month - start_month)
            if months > 0:
                total_months += months
        except Exception:
            pass

    self_intro = normalize_text(resume_data.get("selfIntroduction", ""))
    if self_intro:
        experience_texts.append(self_intro)

    projects_text = []
    for project in resume_data.get("projects", []):
        project_name = normalize_text(project.get("name", ""))
        if project_name:
            projects_text.append(project_name)

        for resp in project.get("responsibilities", []):
            resp = normalize_text(resp)
            if resp:
                projects_text.append(resp)

        for achievement in project.get("achievements", []):
            achievement = normalize_text(achievement)
            if achievement:
                projects_text.append(achievement)

    combined_texts = []
    for item in experience_texts + projects_text:
        if item and item not in combined_texts:
            combined_texts.append(item)

    return {
        "skills": all_skills,
        "education": highest_degree,
        "experienceYears": round(total_months / 12, 1),
        "certifications": certs,
        "projects": combined_texts
    }


def flatten_job(firebase_job_doc):
    job_data = firebase_job_doc.get("jobPosting", {})
    requirements = job_data.get("requirements", {})
    embedding_text = job_data.get("embeddingText", {})

    required_skills = []
    for skill in requirements.get("requiredSkills", []):
        skill = normalize_text(skill).replace("ㆍ", "")
        if skill and skill not in required_skills:
            required_skills.append(skill)

    required_qualifications = []
    for qual in requirements.get("requiredQualifications", []):
        qual = normalize_text(qual)
        if qual:
            required_qualifications.append(qual)

    preferred_qualifications = []
    for qual in requirements.get("preferredQualifications", []):
        qual = normalize_text(qual)
        if qual:
            preferred_qualifications.append(qual)

    education_min = requirements.get("education", {}).get("minimum", "")
    exp_text = requirements.get("experience", {}).get("type", "")
    min_years = parse_experience_years(exp_text)

    responsibilities = []
    raw_resps = requirements.get("responsibilities", [])
    if raw_resps:
        for item in raw_resps:
            item = normalize_text(item)
            if item:
                responsibilities.append(item)

    if not responsibilities:
        resp_text = normalize_text(embedding_text.get("responsibilities", ""))
        if resp_text:
            responsibilities.append(resp_text)

    certs = []
    for qual in required_qualifications:
        if "기사" in qual or "자격증" in qual or "SQLD" in qual or "TOEIC" in qual:
            certs.append(qual)

    return {
        "skills": {
            "required": required_skills,
            "preferred": []
        },
        "responsibilities": responsibilities,
        "qualifications": {
            "required": required_qualifications,
            "preferred": preferred_qualifications
        },
        "education": education_min,
        "experience": {
            "minYears": min_years
        },
        "certifications": certs
    }


def get_resume_embedding_text(firebase_resume_doc):
    return (
        firebase_resume_doc.get("resume", {})
        .get("resumeData", {})
        .get("embeddingText", {})
        .get("fullForEmbedding", "")
    )


def get_job_embedding_text(firebase_job_doc):
    return (
        firebase_job_doc.get("jobPosting", {})
        .get("embeddingText", {})
        .get("fullForEmbedding", "")
    )


def calculate_full_embedding_similarity(resume_text, job_text):
    if not resume_text or not job_text:
        return 0.0, 0.0

    emb_resume = model.encode(resume_text, convert_to_tensor=True)
    emb_job = model.encode(job_text, convert_to_tensor=True)

    sim = util.pytorch_cos_sim(emb_resume, emb_job).item()
    score = max(sim, 0) * 20

    return sim, score


def calculate_qualification_rule_score(job, resume):
    required_qualifications = job.get("qualifications", {}).get("required", [])
    resume_text = " ".join(resume.get("projects", []))

    matched_qualifications = []
    for qual in required_qualifications:
        if qual and qual in resume_text:
            matched_qualifications.append(qual)

    if required_qualifications:
        qualification_score = (
            len(matched_qualifications) / len(required_qualifications)
        ) * WEIGHTS["qualifications_rule"]
    else:
        qualification_score = 0

    return qualification_score, matched_qualifications, len(required_qualifications)


def calculate_rule_score(job, resume):
    required_skills = job.get("skills", {}).get("required", [])
    resume_skills = resume.get("skills", [])

    clean_required_skills = [s for s in required_skills if s]
    skill_match_count = sum(skill in resume_skills for skill in clean_required_skills)
    skill_score = (
        (skill_match_count / len(clean_required_skills)) * WEIGHTS["skills"]
        if clean_required_skills else 0
    )

    job_edu_level = normalize_education_level(job.get("education", ""))
    resume_edu_level = normalize_education_level(resume.get("education", ""))
    job_edu_idx = education_to_index(job_edu_level)
    resume_edu_idx = education_to_index(resume_edu_level)
    edu_score = WEIGHTS["education"] if resume_edu_idx >= job_edu_idx else 0

    min_exp = job.get("experience", {}).get("minYears", 0)
    exp_years = resume.get("experienceYears", 0)
    if min_exp > 0:
        exp_score = min(exp_years / max(min_exp, 1), 1.0) * WEIGHTS["experience"]
    else:
        exp_score = WEIGHTS["experience"]

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
        "skill_total_count": len(clean_required_skills),
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


def calculate_semantic_score(job, resume):
    job_resp_text = " ".join(job.get("responsibilities", []))
    resume_proj_text = " ".join(resume.get("projects", []))

    resp_score = 0
    resp_sim = 0
    qual_score = 0
    qual_sim = 0

    if job_resp_text.strip() and resume_proj_text.strip():
        emb_resp = model.encode(job_resp_text, convert_to_tensor=True)
        emb_proj = model.encode(resume_proj_text, convert_to_tensor=True)
        resp_sim = util.pytorch_cos_sim(emb_resp, emb_proj).item()
        resp_score = max(resp_sim, 0) * WEIGHTS["semantic_responsibilities"]

    job_qual_text = " ".join(job.get("qualifications", {}).get("required", []))
    if job_qual_text.strip() and resume_proj_text.strip():
        emb_qual = model.encode(job_qual_text, convert_to_tensor=True)
        emb_proj = model.encode(resume_proj_text, convert_to_tensor=True)
        qual_sim = util.pytorch_cos_sim(emb_qual, emb_proj).item()
        qual_score = max(qual_sim, 0) * WEIGHTS["semantic_qualifications"]

    total_semantic_score = resp_score + qual_score

    details = {
        "resp_sim": resp_sim,
        "resp_score": resp_score,
        "qual_sim": qual_sim,
        "qual_score": qual_score
    }

    return total_semantic_score, details


def get_unmet_conditions(job, resume):
    reasons = []

    job_edu_level = normalize_education_level(job.get("education", ""))
    resume_edu_level = normalize_education_level(resume.get("education", ""))
    if education_to_index(resume_edu_level) < education_to_index(job_edu_level):
        reasons.append("학력 미충족")

    required_skills = [s for s in job.get("skills", {}).get("required", []) if s]
    match_count = sum(skill in resume.get("skills", []) for skill in required_skills)
    if required_skills and (match_count / len(required_skills) < 0.5):
        reasons.append("필수 기술 50% 미만 충족")

    min_exp = job.get("experience", {}).get("minYears", 0)
    if resume.get("experienceYears", 0) < min_exp:
        reasons.append("경력 미충족")

    _, matched_quals, total_quals = calculate_qualification_rule_score(job, resume)
    if total_quals > 0 and len(matched_quals) == 0:
        reasons.append("필수 자격요건 미충족")

    return reasons


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

    final_score = rule_total + semantic_total
    unmet_conditions = get_unmet_conditions(job, resume)

    print("[최종 점수]")
    print(f"- 룰 기반 점수: {rule_total:.2f}/80")
    print(f"- 의미 기반 점수: {semantic_total:.2f}/20")
    print(f"- 합산 점수: {final_score:.2f}/100")

    print("[미충족 조건]")
    if unmet_conditions:
        for reason in unmet_conditions:
            print(f"- {reason}")
    else:
        print("- 없음")

    return {
        "final_score": final_score,
        "rule_total": rule_total,
        "semantic_total": semantic_total,
        "unmet_conditions": unmet_conditions
    }