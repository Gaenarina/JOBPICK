# structure_resume.py

import re
import uuid


# -----------------------------
# 1. 기본 정리
# -----------------------------
def clean_text(text):
    if text is None:
        return ""
    text = str(text)
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def unique_preserve_order(items):
    seen = set()
    result = []

    for item in items:
        value = clean_text(item)
        if not value:
            continue
        if value not in seen:
            seen.add(value)
            result.append(value)

    return result


def normalize_date(text):
    text = clean_text(text)
    if not text:
        return ""
    text = text.replace(".", "-").replace("/", "-")
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


# -----------------------------
# 2. OCR 텍스트 보정
# -----------------------------
def normalize_ocr_text(text):
    text = clean_text(text)

    replacements = {
        "이 력서": "이력서",
        "생 년 월 일": "생년월일",
        "현 주 소": "현주소",
        "연 락 처": "연락처",
        "학 력": "학력",
        "외 국 어": "외국어",
        "컴퓨터 사용 능력": "컴퓨터 사용능력",
        "컴 퓨 터 사용능력": "컴퓨터 사용능력",
        "자 격 증": "자격증",
        "면 허": "면허",
        "업 품목": "업품목",
        "기 간": "기간",
        "부 전 공": "부전공",
        "복 수 전 공": "복수전공",
        "자 기 소 개 서": "자기소개서",
        "경 력 사 항": "경력사항",
        "사 업 목 적": "사업목적",
        "회 사 연 혁": "회사연혁",
        "보 훈 대 상 여 부": "보훈대상여부",
        "병 역": "병역",
        "병 역 사 항": "병역사항",
        "취 득 일": "취득일",
        "일 자": "일자",
        "명 칭": "명칭",
        "내 용": "내용",
        "용기술": "용기술",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text).strip()
    return text


# -----------------------------
# 3. 공통 추출 함수
# -----------------------------
def extract_email(text):
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group() if match else ""


def extract_phone(text):
    match = re.search(r"01[0-9]-?\d{3,4}-?\d{4}", text)
    return match.group() if match else ""


def extract_birth(text):
    patterns = [
        r"\d{4}[./-]\d{1,2}[./-]\d{1,2}",
        r"\d{2}[./-]\d{1,2}[./-]\d{1,2}",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_date(match.group())

    return ""


def extract_between(text, start_keywords, end_keywords):
    text = clean_text(text)
    if not text:
        return ""

    start_pattern = "|".join(re.escape(x) for x in start_keywords)
    end_pattern = "|".join(re.escape(x) for x in end_keywords)

    pattern = rf"(?:{start_pattern})\s*(.*?)(?=(?:{end_pattern})|$)"
    match = re.search(pattern, text)

    return clean_text(match.group(1)) if match else ""


# -----------------------------
# 4. 기본 정보
# -----------------------------
def extract_name(text):
    text = normalize_ocr_text(text)

    blocked = {
        "이력서", "회사명", "생산", "업종", "업품목", "연령",
        "성명", "현주소", "연락처", "학력", "경력", "병역",
        "취미", "특기", "기타", "자격증", "외국어"
    }

    match = re.search(r"이력서\s*(?:\(한글\))?\s*([가-힣]{2,4})", text)
    if match:
        name = match.group(1)
        if name not in blocked:
            return name

    match = re.search(r"성명\s*(?:\(한글\))?\s*([가-힣]{2,4})", text)
    if match:
        name = match.group(1)
        if name not in blocked:
            return name

    header = text[:100]
    candidates = re.findall(r"[가-힣]{2,4}", header)
    for cand in candidates:
        if cand not in blocked:
            return cand

    return ""


def extract_address(text):
    match = re.search(r"현주소\s*(.*?)\s*(e-mail|email|긴급|연락처|학력|기간)", text)
    if match:
        return clean_text(match.group(1))
    return ""


# -----------------------------
# 5. 학력
# -----------------------------
def extract_gpa(text):
    match = re.search(r"대학평균\s*(\d\.\d+)", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def extract_education(text):
    text = normalize_ocr_text(text)
    results = []

    edu_block = extract_between(
        text,
        ["학력", "학"],
        ["성적", "외국어명", "외국어", "컴퓨터 사용능력", "컴퓨터사용능력"]
    )

    hs_match = re.search(
        r"(\d{4}[.-]\d{1,2})\s*([가-힣A-Za-z0-9]+고등학교).*?(\d{4}[.-]\d{1,2})?",
        edu_block
    )
    if hs_match:
        results.append({
            "school": clean_text(hs_match.group(2)),
            "degree": "고졸",
            "major": "",
            "startDate": normalize_date(hs_match.group(1)) if hs_match.group(1) else "",
            "endDate": normalize_date(hs_match.group(3)) if hs_match.group(3) else "",
            "gpa": None
        })

    uni_match = re.search(
        r"(\d{4}[.-]\d{1,2})\s*~\s*([가-힣A-Za-z0-9]+대학교?)\s*([가-힣A-Za-z0-9]+학과).*?(\d{4}[.-]\d{1,2})",
        edu_block
    )
    if uni_match:
        results.append({
            "school": clean_text(uni_match.group(2)),
            "degree": "학사",
            "major": clean_text(uni_match.group(3)),
            "startDate": normalize_date(uni_match.group(1)),
            "endDate": normalize_date(uni_match.group(4)),
            "gpa": extract_gpa(text)
        })

    return results


# -----------------------------
# 6. 외국어
# -----------------------------
def extract_language_tests(text):
    text = normalize_ocr_text(text)

    block = extract_between(
        text,
        ["외국어명", "외국어"],
        ["컴퓨터 사용능력", "컴퓨터사용능력", "자격 및 면허", "자격증"]
    )

    results = []

    test_names = ["TOEIC", "TOEFL", "OPIc", "OPIC", "IELTS", "TEPS", "텝스"]

    for test_name in test_names:
        if re.search(re.escape(test_name), block, re.IGNORECASE):
            date_match = re.search(r"\d{4}[.-]\d{1,2}", block)
            score_match = re.search(rf"{re.escape(test_name)}.*?(\b\d{{2,4}}\b)", block, re.IGNORECASE)

            results.append({
                "language": "영어",
                "testName": "OPIc" if test_name.upper() == "OPIC" else test_name,
                "date": normalize_date(date_match.group()) if date_match else "",
                "score": score_match.group(1) if score_match else ""
            })

    dedup = []
    seen = set()
    for item in results:
        key = (item["language"], item["testName"], item["date"], item["score"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(item)

    return dedup


# -----------------------------
# 7. 스킬
# -----------------------------
def classify_skill(skill):
    languages = {
        "Python", "Java", "JavaScript", "TypeScript", "C", "C++", "C#", "SQL",
        "R", "Go", "Kotlin", "Swift", "PHP"
    }
    frameworks = {
        "React", "Next.js", "Node.js", "Spring", "Django", "Flask",
        "TensorFlow", "PyTorch", "Vue", "Angular"
    }
    tools = {
        "Git", "Docker", "Kubernetes", "Firebase", "MySQL", "MongoDB",
        "Oracle", "Linux", "Pandas", "NumPy"
    }

    if skill in languages:
        return "languages"
    if skill in frameworks:
        return "frameworks"
    if skill in tools:
        return "tools"
    return "etc"


def extract_skills(text):
    text = normalize_ocr_text(text)

    skill_block = extract_between(
        text,
        ["컴퓨터 사용능력", "컴퓨터사용능력"],
        ["자격 및 면허", "자격증", "보훈대상여부", "종교"]
    )

    skill_keywords = [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "C",
        "React", "Next.js", "Node.js", "Spring", "Django", "Flask",
        "TensorFlow", "PyTorch", "Pandas", "NumPy", "MySQL", "Oracle",
        "MongoDB", "Firebase", "Git", "Docker", "Kubernetes", "Linux",
        "SQL", "R", "Go", "Kotlin", "Swift", "PHP", "Vue", "Angular"
    ]

    found = []
    for keyword in skill_keywords:
        if re.search(rf"(?<![A-Za-z]){re.escape(keyword)}(?![A-Za-z])", skill_block, re.IGNORECASE):
            found.append(keyword)

    found = unique_preserve_order(found)

    result = {
        "languages": [],
        "frameworks": [],
        "tools": [],
        "etc": []
    }

    for skill in found:
        result[classify_skill(skill)].append(skill)

    return result


# -----------------------------
# 8. 자격증
# -----------------------------
def extract_certifications(text):
    text = normalize_ocr_text(text)

    block = extract_between(
        text,
        ["자격 및 면허", "자격증"],
        ["보훈대상여부", "종교", "상벌", "경력", "취미", "특기"]
    )

    cert_keywords = [
        "정보처리기사", "SQLD", "ADsP", "ADSP", "컴퓨터활용능력",
        "정보처리산업기사", "리눅스마스터", "한국사능력검정시험"
    ]

    date_candidates = re.findall(r"\d{4}[.-]\d{1,2}", block)
    results = []

    found_names = []
    for cert in cert_keywords:
        if re.search(re.escape(cert), block, re.IGNORECASE):
            found_names.append(cert)

    found_names = unique_preserve_order(found_names)

    for idx, name in enumerate(found_names):
        results.append({
            "name": name,
            "grade": "",
            "date": normalize_date(date_candidates[idx]) if idx < len(date_candidates) else ""
        })

    return results


# -----------------------------
# 9. 활동 / 수상
# -----------------------------
def extract_activities(text):
    text = normalize_ocr_text(text)

    block = extract_between(
        text,
        ["상벌"],
        ["취미", "특기", "병역", "병역사항", "회사연혁", "사업목적", "자기소개서"]
    )

    award_keywords = ["대상", "최우수상", "우수상", "장려상", "수상"]
    results = []

    parts = re.split(r"(?=20\d{2})|(?=AI)|(?=교내)|(?=대외)", block)

    for part in parts:
        part = clean_text(part)
        if len(part) < 2:
            continue

        award = ""
        for keyword in award_keywords:
            if keyword in part:
                award = keyword
                break

        year_match = re.search(r"\b(20\d{2})\b", part)

        name = part
        if year_match:
            name = name.replace(year_match.group(1), "")
        if award:
            name = name.replace(award, "")

        name = clean_text(name)
        if not name:
            continue

        results.append({
            "name": name,
            "organization": "",
            "date": year_match.group(1) if year_match else "",
            "award": award,
            "description": ""
        })

    return results


# -----------------------------
# 10. 병역
# -----------------------------
def extract_military(text):
    text = normalize_ocr_text(text)

    block = extract_between(
        text,
        ["병역", "병역사항"],
        ["회사연혁", "사업목적", "자기소개서", "경력사항"]
    )

    branch = ""
    for cand in ["육군", "해군", "공군", "해병대"]:
        if cand in block:
            branch = cand
            break

    rank = ""
    for cand in ["이병", "일병", "상병", "병장", "하사", "중사", "상사", "소위", "중위", "대위"]:
        if cand in block:
            rank = cand
            break

    status = ""
    if "만기제대" in block or "군필" in block:
        status = "군필"
    elif "미필" in block:
        status = "미필"

    dates = re.findall(r"\d{4}[.-]\d{1,2}", block)

    return {
        "branch": branch,
        "rank": rank,
        "status": status,
        "startDate": normalize_date(dates[0]) if len(dates) >= 1 else "",
        "endDate": normalize_date(dates[1]) if len(dates) >= 2 else ""
    }


# -----------------------------
# 11. 경력
# -----------------------------
def extract_experience_items(text):
    text = normalize_ocr_text(text)

    block = extract_between(
        text,
        ["경력사항"],
        ["기타", "자기소개서상의", "작성자"]
    )

    if not block:
        return []

    if all(x in block for x in ["직장명", "부서/직위", "담당업무", "이직사유"]):
        if len(block) < 60:
            return []

    results = []
    range_matches = re.finditer(r"(\d{4}[.-]\d{1,2})\s*~?\s*(\d{4}[.-]\d{1,2})?", block)

    for match in range_matches:
        start_date = normalize_date(match.group(1))
        end_date = normalize_date(match.group(2)) if match.group(2) else ""
        span_end = match.end()
        snippet = clean_text(block[span_end:span_end + 40])

        results.append({
            "organization": snippet,
            "department": "",
            "position": "",
            "startDate": start_date,
            "endDate": end_date,
            "responsibilities": [],
            "reasonForLeaving": ""
        })

    return results


# -----------------------------
# 12. 자기소개서 / 역량 / 프로젝트
# -----------------------------
def extract_self_introduction(text):
    text = normalize_ocr_text(text)

    block = extract_between(
        text,
        ["자기소개서", "경력사항"],
        ["기타", "자기소개서상의", "작성자"]
    )

    noise_patterns = [
        r"^기간\s*직장명\s*부서/직위\s*담당업무\s*이직사유",
        r"^경력사항",
        r"자기소개서상의 모든 기재사항은 사실임을 확인합니다.*$",
        r"작성자\s*[:：].*$",
        r"\b기타\b.*$",
        r"용기술$",
    ]

    for pattern in noise_patterns:
        block = re.sub(pattern, "", block)

    return clean_text(block)


def extract_core_competencies(self_intro):
    keywords = [
        "문제 해결", "협업", "데이터 분석", "데이터 기반", "머신러닝", "딥러닝",
        "논리적", "빠르게 학습", "커뮤니케이션", "책임감", "성실"
    ]

    found = []
    for keyword in keywords:
        if keyword in self_intro:
            found.append(keyword)

    return unique_preserve_order(found)


def extract_projects_from_intro(self_intro, skills):
    if not self_intro:
        return []

    all_skills = (
        skills.get("languages", [])
        + skills.get("frameworks", [])
        + skills.get("tools", [])
        + skills.get("etc", [])
    )

    tech_stack = []
    for skill in all_skills:
        if skill.lower() in self_intro.lower():
            tech_stack.append(skill)

    sentences = re.split(r"[.!?\n]", self_intro)
    responsibilities = []

    for sentence in sentences:
        sentence = clean_text(sentence)
        if not sentence:
            continue
        if any(keyword in sentence for keyword in ["프로젝트", "해커톤", "캡스톤", "협업", "머신러닝", "데이터"]):
            responsibilities.append(sentence)

    if not responsibilities:
        return []

    return [{
        "name": "자기소개 기반 프로젝트/경험",
        "organization": "",
        "role": "",
        "startDate": "",
        "endDate": "",
        "responsibilities": unique_preserve_order(responsibilities),
        "techStack": unique_preserve_order(tech_stack),
        "achievements": []
    }]


# -----------------------------
# 13. 임베딩용 텍스트
# -----------------------------
def build_embedding_text(resume_data):
    basic = resume_data.get("basicInfo", {})
    education = resume_data.get("education", [])
    skills = resume_data.get("skills", {})
    certifications = resume_data.get("certifications", [])
    projects = resume_data.get("projects", [])
    self_intro = resume_data.get("selfIntroduction", "")

    summary_parts = [
        basic.get("name", ""),
        ", ".join([item.get("major", "") for item in education if item.get("major")]),
        ", ".join(
            skills.get("languages", [])
            + skills.get("frameworks", [])
            + skills.get("tools", [])
        ),
        ", ".join([item.get("name", "") for item in certifications if item.get("name")]),
    ]

    project_parts = []
    for project in projects:
        project_parts.extend(project.get("responsibilities", []))
        project_parts.extend(project.get("techStack", []))

    summary = clean_text(" / ".join([x for x in summary_parts if clean_text(x)]))
    experience_text = clean_text(" / ".join(unique_preserve_order(project_parts)))
    full_for_embedding = clean_text(" / ".join([summary, experience_text, self_intro]))

    return {
        "summary": summary,
        "experience": experience_text,
        "fullForEmbedding": full_for_embedding
    }


# -----------------------------
# 14. 전체 구조화
# -----------------------------
def build_resume(preprocessed_text):
    text = normalize_ocr_text(preprocessed_text)

    basic_info = {
        "name": extract_name(text),
        "birthDate": extract_birth(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "address": extract_address(text)
    }

    education = extract_education(text)
    skills = extract_skills(text)
    language_tests = extract_language_tests(text)
    certifications = extract_certifications(text)
    activities = extract_activities(text)
    experience = extract_experience_items(text)
    military = extract_military(text)
    self_introduction = extract_self_introduction(text)
    projects = extract_projects_from_intro(self_introduction, skills)
    core_competencies = extract_core_competencies(self_introduction)

    resume_data = {
        "resumeId": str(uuid.uuid4()),
        "basicInfo": basic_info,
        "education": education,
        "skills": skills,
        "languageTests": language_tests,
        "certifications": certifications,
        "activities": activities,
        "experience": experience,
        "projects": projects,
        "military": military,
        "selfIntroduction": self_introduction,
        "coreCompetencies": core_competencies,
        "rawText": text
    }

    resume_data["embeddingText"] = build_embedding_text(resume_data)

    return {
        "resumeData": resume_data
    }


def structure_resume(preprocessed_text):
    return build_resume(preprocessed_text)