# structure_resume.py

import re
import uuid


# -----------------------------
# 1. 기본 정리
# -----------------------------
def clean_text(text):
    if text is None:
        return ""
    return " ".join(str(text).split()).strip()


def split_lines(text):
    if not text:
        return []
    return [line.strip() for line in str(text).split("\n") if line.strip()]


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
            return clean_text(match.group())
    return ""


def extract_name(text):
    lines = split_lines(text)

    ignore_keywords = [
        "이력서", "resume", "지원자", "성명", "이름", "연락처", "주소",
        "email", "e-mail", "학력", "경력", "자격증", "기술", "보유", "프로필"
    ]

    for line in lines[:10]:
        line_clean = clean_text(line)
        if not line_clean:
            continue

        if any(keyword.lower() in line_clean.lower() for keyword in ignore_keywords):
            continue

        if re.fullmatch(r"[가-힣]{2,4}", line_clean):
            return line_clean

    name_match = re.search(r"(성명|이름)\s*[:：]?\s*([가-힣]{2,4})", text)
    if name_match:
        return clean_text(name_match.group(2))

    return ""


def extract_address(text):
    lines = split_lines(text)

    address_keywords = ["서울", "경기", "인천", "부산", "대구", "대전", "광주", "울산", "세종", "제주", "충북", "충남", "전북", "전남", "경북", "경남", "강원"]
    for line in lines:
        if any(keyword in line for keyword in address_keywords):
            if len(line) >= 5:
                return clean_text(line)

    address_match = re.search(r"(주소)\s*[:：]?\s*(.+)", text)
    if address_match:
        return clean_text(address_match.group(2))

    return ""


def extract_education(text):
    lines = split_lines(text)
    education_keywords = [
        "학력", "학사", "석사", "박사", "대학교", "대학", "고등학교",
        "졸업", "졸업예정", "재학", "휴학", "전공"
    ]

    results = []
    for line in lines:
        if any(keyword in line for keyword in education_keywords):
            results.append(line)

    return unique_preserve_order(results)


def extract_experience(text):
    lines = split_lines(text)
    experience_keywords = [
        "경력", "인턴", "근무", "재직", "프로젝트", "업무", "담당",
        "회사", "기업", "아르바이트", "실습"
    ]

    results = []
    for line in lines:
        if any(keyword in line for keyword in experience_keywords):
            results.append(line)

    return unique_preserve_order(results)


def extract_skills(text):
    lines = split_lines(text)

    skill_keywords = [
        "Python", "Java", "C", "C++", "C#", "JavaScript", "TypeScript",
        "React", "Next.js", "Node.js", "Spring", "Django", "Flask",
        "SQL", "MySQL", "Oracle", "MongoDB", "Firebase",
        "AWS", "Docker", "Kubernetes", "Git", "Linux",
        "HTML", "CSS", "TensorFlow", "PyTorch", "Pandas", "NumPy",
        "머신러닝", "딥러닝", "데이터분석", "웹개발", "백엔드", "프론트엔드"
    ]

    results = []

    for line in lines:
        lower_line = line.lower()
        for keyword in skill_keywords:
            if keyword.lower() in lower_line:
                results.append(line)
                break

    return unique_preserve_order(results)


def extract_certifications(text):
    lines = split_lines(text)
    cert_keywords = [
        "자격증", "정보처리기사", "SQLD", "ADsP", "컴퓨터활용능력",
        "토익", "오픽", "TOEIC", "OPIc", "한국사", "기사", "산업기사"
    ]

    results = []
    for line in lines:
        lower_line = line.lower()
        for keyword in cert_keywords:
            if keyword.lower() in lower_line:
                results.append(line)
                break

    return unique_preserve_order(results)


def extract_portfolio_url(text):
    patterns = [
        r"https?://[^\s]+",
        r"github\.com/[^\s]+",
        r"notion\.so/[^\s]+",
        r"velog\.io/@[^\s]+",
    ]

    urls = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        urls.extend(matches)

    urls = [clean_text(url.rstrip(".,);]")) for url in urls]
    return unique_preserve_order(urls)


def extract_self_introduction(text):
    lines = split_lines(text)

    intro_keywords = ["자기소개", "소개", "지원동기", "성장과정", "포부"]
    start_idx = -1

    for i, line in enumerate(lines):
        if any(keyword in line for keyword in intro_keywords):
            start_idx = i
            break

    if start_idx == -1:
        return ""

    intro_lines = lines[start_idx:start_idx + 15]
    return "\n".join(intro_lines)


def guess_target_job(text):
    target_keywords = [
        "백엔드", "프론트엔드", "풀스택", "데이터 분석가", "데이터사이언티스트",
        "AI", "머신러닝", "앱 개발", "웹 개발", "서버 개발", "기획", "마케팅", "디자인"
    ]

    for keyword in target_keywords:
        if keyword.lower() in text.lower():
            return keyword

    return ""


def build_resume(preprocessed_text):
    text = preprocessed_text if preprocessed_text else ""

    name = extract_name(text)
    phone = extract_phone(text)
    email = extract_email(text)
    birth = extract_birth(text)
    address = extract_address(text)

    education = extract_education(text)
    experience = extract_experience(text)
    skills = extract_skills(text)
    certifications = extract_certifications(text)
    portfolio_urls = extract_portfolio_url(text)
    self_introduction = extract_self_introduction(text)
    target_job = guess_target_job(text)

    return {
        "userProfile": {
            "name": name,
            "phone": phone,
            "email": email,
            "birth": birth,
            "address": address,
            "targetJob": target_job,
            "education": education,
            "experience": experience,
            "skills": skills,
            "certifications": certifications,
            "portfolioUrl": portfolio_urls[0] if portfolio_urls else "",
            "selfIntroduction": self_introduction,
            "resumeText": text,
        }
    }

def structure_resume(preprocessed_text):
    return build_resume(preprocessed_text)