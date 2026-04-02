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


def normalize_month_date(text):
    text = normalize_date(text)
    match = re.search(r"(\d{4})-(\d{1,2})", text)
    if not match:
        return ""
    year = match.group(1)
    month = match.group(2).zfill(2)
    return f"{year}-{month}"


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
        "자 격 및 면 허": "자격 및 면허",
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
        "컴퓨터사용 능력": "컴퓨터 사용능력",
        "사용가능 언어 및 TOOL": "사용가능언어및TOOL",
        "부서 / 직위": "부서/직위",
        "병역 사항": "병역사항",
        "상벌경력": "상벌 경력",
        "회혁": "경력사항",
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


def split_sentences(text):
    if not text:
        return []
    parts = re.split(r"[.!?\n]", text)
    return unique_preserve_order([clean_text(x) for x in parts if clean_text(x)])


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

    header = text[:120]
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
        ["성적", "외국어명", "외국어", "컴퓨터 사용능력", "컴퓨터사용능력", "자격 및 면허", "자격증"]
    )

    if not edu_block:
        edu_block = text

    seen = set()

    for match in re.finditer(
        r"(?:(\d{4}[.-]\d{1,2})\s*[-~]?\s*(\d{4}[.-]\d{1,2})\s*)?([가-힣A-Za-z0-9]+고등학교)\s*(졸업|재학|중퇴)?",
        edu_block
    ):
        school = clean_text(match.group(3))
        key = ("고졸", school)
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "school": school,
            "degree": "고졸",
            "major": "",
            "startDate": normalize_month_date(match.group(1)) if match.group(1) else "",
            "endDate": normalize_month_date(match.group(2)) if match.group(2) else "",
            "gpa": None
        })

    for match in re.finditer(
        r"(?:(\d{4}[.-]\d{1,2})\s*[-~]?\s*)?([가-힣A-Za-z0-9]+(?:대학교|대학))\s*([가-힣A-Za-z0-9·\-/]+학과)?\s*(?:(\d{4}[.-]\d{1,2}))?",
        edu_block
    ):
        school = clean_text(match.group(2))
        major = clean_text(match.group(3)) if match.group(3) else ""
        degree = "학사"

        if "전문대" in school:
            degree = "전문학사"

        key = (degree, school, major)
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "school": school,
            "degree": degree,
            "major": major,
            "startDate": normalize_month_date(match.group(1)) if match.group(1) else "",
            "endDate": normalize_month_date(match.group(4)) if match.group(4) else "",
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
                "date": normalize_month_date(date_match.group()) if date_match else "",
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
        "Oracle", "Linux", "Pandas", "NumPy", "Excel", "ERP", "SAP",
        "Microsoft Office", "PowerPoint", "Word", "한글"
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
        ["컴퓨터 사용능력", "컴퓨터사용능력", "사용가능언어및TOOL"],
        ["자격 및 면허", "자격증", "보훈대상여부", "종교", "상벌", "경력"]
    )

    if not skill_block:
        skill_block = text

    skill_keywords = [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "C",
        "React", "Next.js", "Node.js", "Spring", "Django", "Flask",
        "TensorFlow", "PyTorch", "Pandas", "NumPy", "MySQL", "Oracle",
        "MongoDB", "Firebase", "Git", "Docker", "Kubernetes", "Linux",
        "SQL", "R", "Go", "Kotlin", "Swift", "PHP", "Vue", "Angular",
        "Excel", "ERP", "SAP", "Microsoft Office", "PowerPoint", "Word", "한글"
    ]

    found = []
    for keyword in skill_keywords:
        if re.search(rf"(?<![A-Za-z가-힣]){re.escape(keyword)}(?![A-Za-z가-힣])", skill_block, re.IGNORECASE):
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
        ["보훈대상여부", "종교", "상벌", "경력", "취미", "특기", "병역", "병역사항"]
    )

    if not block:
        block = text

    results = []
    seen = set()

    known_keywords = [
        "정보처리기사", "SQLD", "ADsP", "ADSP", "컴퓨터활용능력",
        "정보처리산업기사", "리눅스마스터", "한국사능력검정시험",
        "지게차 운전기능사"
    ]

    found_names = []
    for keyword in known_keywords:
        if re.search(re.escape(keyword), block, re.IGNORECASE):
            found_names.append(keyword)

    pattern_candidates = []
    patterns = [
        r"([가-힣A-Za-z0-9 ]+기사)",
        r"([가-힣A-Za-z0-9 ]+산업기사)",
        r"([가-힣A-Za-z0-9 ]+기능사)",
        r"([가-힣A-Za-z0-9 ]+면허)",
    ]

    for pattern in patterns:
        pattern_candidates.extend(re.findall(pattern, block))

    candidates = unique_preserve_order(found_names + pattern_candidates)
    date_candidates = re.findall(r"\d{4}[.-]?\d{0,2}", block)

    for idx, cand in enumerate(candidates):
        name = clean_text(cand)

        if not name:
            continue

        name = re.sub(r"^(자|격|증|면허)\s*", "", name)
        name = clean_text(name)

        if not name or len(name) <= 1:
            continue

        if name in {"UIO", "TOOL", "Excel", "ERP", "시스템"}:
            continue

        if name in seen:
            continue
        seen.add(name)

        results.append({
            "name": name,
            "grade": "",
            "date": normalize_month_date(date_candidates[idx]) if idx < len(date_candidates) else ""
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
    if "만기제대" in block or "군필" in block or "전역" in block:
        status = "군필"
    elif "미필" in block:
        status = "미필"

    dates = re.findall(r"\d{4}[.-]\d{1,2}", block)

    return {
        "branch": branch,
        "rank": rank,
        "status": status,
        "startDate": normalize_month_date(dates[0]) if len(dates) >= 1 else "",
        "endDate": normalize_month_date(dates[1]) if len(dates) >= 2 else ""
    }


# -----------------------------
# 11. 경력
# -----------------------------
def extract_experience_items(text):
    text = normalize_ocr_text(text)

    block = extract_between(
        text,
        ["기간직장명", "기간 직장명", "자기소개서 기간직장명"],
        ["기타", "자기소개서상의", "작성자"]
    )

    if not block:
        return []

    results = []
    seen = set()

    lines = re.split(r"(?=\d{4}[.-]\d{1,2})", block)

    for line in lines:
        line = clean_text(line)
        if not line:
            continue

        dates = re.findall(r"\d{4}[.-]\d{1,2}", line)
        if not dates:
            continue

        start_date = normalize_month_date(dates[0])

        end_date = ""
        if "현재" in line:
            end_date = "현재"
        elif len(dates) >= 2:
            end_date = normalize_month_date(dates[1])

        org_match = re.search(
            r"\d{4}[.-]\d{1,2}\s*(?:~\s*)?(?:현재|\d{4}[.-]\d{1,2})?\s*([가-힣A-Za-z0-9 ]+(?:회사|산업|기업|공사|센터|공장|연구소))",
            line
        )
        if not org_match:
            continue

        organization = clean_text(org_match.group(1))

        position = ""
        position_match = re.search(
            r"(물류관리|생산관리|경리|총무|회계|사원|주임|대리|과장|차장|부장|인턴|매니저|연구원|개발자|디자이너)",
            line
        )
        if position_match:
            position = clean_text(position_match.group(1))

        responsibilities = []

        responsibility_patterns = [
            r"(재고 관리[, ]*출고 관리)",
            r"(생산 일정 관리[, ]*품질 관리)",
            r"(전표 입력 및 회계 마감 관리)",
            r"(매입/매출 및 채권채무 관리)",
            r"(부가세 등 세무신고 자료 준비)",
            r"(급여/4대보험 등 인사총무 관리)",
            r"(자금 집행 및 증빙서류 관리)",
        ]
        for pattern in responsibility_patterns:
            match = re.search(pattern, line)
            if match:
                responsibilities.append(clean_text(match.group(1)))

        key = (organization, start_date, end_date)
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "organization": organization,
            "department": "",
            "position": position,
            "startDate": start_date,
            "endDate": end_date,
            "responsibilities": unique_preserve_order(responsibilities),
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
        ["자기소개서"],
        ["기타", "자기소개서상의", "작성자"]
    )

    if not block:
        return ""

    noise_patterns = [
        r"기간\s*직장명\s*부서\s*/?\s*직위\s*담당업무\s*이직사유",
        r"^\s*경력사항",
        r"자기소개서상의 모든 기재사항은 사실임을 확인합니다.*$",
        r"작성자\s*[:：].*$",
        r"\b기타\b.*$",
        r"\b내용\s*기술\b.*$",
    ]

    for pattern in noise_patterns:
        block = re.sub(pattern, "", block)

    # 자기소개 시작 전의 경력표 부분 제거
    start_keywords = ["저는", "제가", "항상", "고등학교 졸업 후", "대학 시절"]
    start_positions = [block.find(keyword) for keyword in start_keywords if keyword in block]
    if start_positions:
        block = block[min(start_positions):]

    return clean_text(block)


def extract_core_competencies(self_intro):
    keywords = [
        "문제 해결", "협업", "데이터 분석", "데이터 기반", "머신러닝", "딥러닝",
        "논리적", "빠르게 학습", "커뮤니케이션", "책임감", "성실", "꼼꼼",
        "적응", "품질 관리", "생산 관리", "재고 관리", "출고 관리"
    ]

    found = []
    for keyword in keywords:
        if keyword in self_intro:
            found.append(keyword)

    return unique_preserve_order(found)


def extract_projects_from_intro(self_intro, skills):
    if not self_intro:
        return []

    sentences = split_sentences(self_intro)
    responsibilities = []

    project_keywords = ["프로젝트", "해커톤", "캡스톤", "포트폴리오", "개발", "구현"]

    for sentence in sentences:
        if any(keyword in sentence for keyword in project_keywords):
            responsibilities.append(sentence)

    if not responsibilities:
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
    experience = resume_data.get("experience", [])
    self_intro = resume_data.get("selfIntroduction", "")

    education_parts = []
    for item in education:
        part = " ".join([
            item.get("school", ""),
            item.get("major", ""),
            item.get("degree", "")
        ])
        part = clean_text(part)
        if part:
            education_parts.append(part)

    skill_parts = (
        skills.get("languages", [])
        + skills.get("frameworks", [])
        + skills.get("tools", [])
        + skills.get("etc", [])
    )

    cert_parts = [item.get("name", "") for item in certifications if item.get("name")]

    experience_parts = []
    for item in experience:
        org = clean_text(item.get("organization", ""))
        pos = clean_text(item.get("position", ""))
        resp = clean_text(" ".join(item.get("responsibilities", [])))

        part = " / ".join([x for x in [org, pos, resp] if x])
        part = clean_text(part)
        if part:
            experience_parts.append(part)

    project_parts = []
    for project in projects:
        project_parts.extend(project.get("responsibilities", []))
        project_parts.extend(project.get("techStack", []))

    summary_parts = [
        basic.get("name", ""),
        " / ".join(education_parts),
        ", ".join(skill_parts),
        ", ".join(cert_parts)
    ]

    summary = clean_text(" / ".join([x for x in summary_parts if clean_text(x)]))
    experience_text = clean_text(" / ".join(unique_preserve_order(experience_parts + project_parts)))
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