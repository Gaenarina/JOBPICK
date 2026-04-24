# preprocess_resume.py

import re


# -----------------------------
# 1. 기본 공백 정리
# -----------------------------
def normalize_whitespace(text: str) -> str:
    if not text:
        return ""

    text = str(text)
    text = text.replace("\u200b", " ")
    text = text.replace("\xa0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# -----------------------------
# 2. OCR 노이즈 제거
# -----------------------------
def remove_ocr_noise(text: str) -> str:
    if not text:
        return ""

    noise_patterns = [
        r"[■□▪▫◆◇○●◦]+",
        r"[‧•·ㆍ]+",
        r"[‖│┃]+",
        r"[〈〉《》「」『』]+",
        r"Page\s*\d+",
    ]

    for pattern in noise_patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


# -----------------------------
# 3. 줄 단위 기호 정리
# -----------------------------
def normalize_line_format(text: str) -> str:
    if not text:
        return ""

    cleaned_lines = []

    for line in text.split("\n"):
        line = line.strip()

        if not line:
            cleaned_lines.append("")
            continue

        if re.fullmatch(r"[-=+_/\\|.,:;]+", line):
            continue

        line = re.sub(r"^\s*[-•·▪▫◦]+\s*", "- ", line)
        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# -----------------------------
# 4. 전화번호/날짜 최소 정리
# -----------------------------
def normalize_inline_text_patterns(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r"(01[016789])[\s\.]+(\d{3,4})[\s\.]+(\d{4})", r"\1-\2-\3", text)
    text = re.sub(r"(\d{2,3})[\s\.]+(\d{3,4})[\s\.]+(\d{4})", r"\1-\2-\3", text)

    text = re.sub(r"(\d{4})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{1,2})", r"\1-\2-\3", text)
    text = re.sub(r"(\d{4})\s*[./-]\s*(\d{1,2})", r"\1-\2", text)

    text = re.sub(r"\s*~\s*", " ~ ", text)

    return text.strip()


# -----------------------------
# 5. 이메일/URL 최소 복원
# -----------------------------
def normalize_email_and_url(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r"\s*@\s*", "@", text)
    text = re.sub(r"https?\s*:\s*/\s*/", "https://", text)
    text = re.sub(r"http\s*:\s*/\s*/", "http://", text)
    text = re.sub(
        r"([A-Za-z0-9._%+-]+)\s*@\s*([A-Za-z0-9.-]+\.[A-Za-z]{2,})",
        r"\1@\2",
        text
    )

    return text.strip()


# -----------------------------
# 6. 한 글자 줄 붙이기
# -----------------------------
def merge_broken_korean_lines(text: str) -> str:
    if not text:
        return ""

    lines = [line.strip() for line in text.split("\n")]
    merged_lines = []
    index = 0

    while index < len(lines):
        current_line = lines[index]

        if not current_line:
            merged_lines.append("")
            index += 1
            continue

        if index < len(lines) - 1:
            next_line = lines[index + 1]

            if re.fullmatch(r"[가-힣]", current_line) and re.match(r"^[가-힣]{1,5}$", next_line):
                merged_lines.append(current_line + next_line)
                index += 2
                continue

            if re.fullmatch(r"[가-힣]{1,2}", current_line) and re.fullmatch(r"[가-힣]{1,3}", next_line):
                merged_lines.append(current_line + next_line)
                index += 2
                continue

        merged_lines.append(current_line)
        index += 1

    return "\n".join(merged_lines).strip()


# -----------------------------
# 7. 자주 쓰는 섹션명 보정
# -----------------------------
def normalize_section_headers(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "이력 서": "이력서",
        "이 력 서": "이력서",
        "자기 소개서": "자기소개서",
        "자 기 소 개 서": "자기소개서",
        "경력 사항": "경력사항",
        "경력사 항": "경력사항",
        "경력 항": "경력사항",
        "수상 경력": "수상경력",
        "상벌 경력": "상벌경력",
        "보유 기술": "보유기술",
        "지원 분야": "지원분야",
        "희망 직무": "희망직무",
        "생 년월일": "생년월일",
        "생 년 월 일": "생년월일",
        "병역 사항": "병역사항",
        "병 역 사 항": "병역사항",
        "회 혁": "회사연혁",
        "사 혁": "회사연혁",
        "회사 연혁": "회사연혁",
        "사업 목적": "사업목적",
        "기대 효과": "기대효과",
        "내용 기술": "내용기술",
        "내 기술": "내용기술",
        "내기술": "내용기술",
        "내 용 기 술": "내용기술",
        "자 격 증": "자격증",
        "격 증": "자격증",
        "자 격 및 면 허": "자격 및 면허",
        "컴퓨터 사용 능력": "컴퓨터 사용능력",
        "컴퓨터사용 능력": "컴퓨터 사용능력",
        "컴퓨터 활용능력": "컴퓨터활용능력",
        "컴퓨터활 용능력": "컴퓨터활용능력",
        "사용가능 언어 및 TOOL": "사용가능언어및TOOL",
        "부서 / 직위": "부서/직위",
        "성적기간": "성적 기간",
        "기간직장명": "기간 직장명",
    }

    for before, after in replacements.items():
        text = text.replace(before, after)

    return text


# -----------------------------
# 8. 이력서 표 헤더 복원
# -----------------------------
def normalize_resume_table_headers(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "기간 직장 명": "기간 직장명",
        "직장 명": "직장명",
        "근무 회사": "근무회사",
        "직장명부서/직위": "직장명 부서/직위",
        "부서/직위담당업무": "부서/직위 담당업무",
        "담당업무이직사유": "담당업무 이직사유",
        "외국어명시험명": "외국어명 시험명",
        "시험명응시년월": "시험명 응시년월",
        "응시년월점수": "응시년월 점수",
        "응시년월점": "응시년월 점수",
        "자격및면허": "자격 및 면허",
        "취 득 일": "취득일",
        "등급취득": "등급 취득",
        "급취득": "급 취득",
    }

    for before, after in replacements.items():
        text = text.replace(before, after)

    text = re.sub(r"기간\s*직장명\s*부서/?직위\s*담당업무\s*이직사유", "기간 직장명 부서/직위 담당업무 이직사유", text)
    text = re.sub(r"외국어명\s*시험명\s*응시년월\s*점수?", "외국어명 시험명 응시년월 점수", text)
    text = re.sub(r"자격\s*및\s*면허\s*등급\s*취득일?", "자격 및 면허 등급 취득일", text)

    return text


# -----------------------------
# 9. 주요 섹션 앞뒤 줄바꿈 추가
# -----------------------------
def add_newlines_around_resume_headers(text: str) -> str:
    if not text:
        return ""

    headers = [
        "자기소개서",
        "내용기술",
        "경력사항",
        "병역사항",
        "회사연혁",
        "사업목적",
        "기대효과",
        "상벌경력",
        "자격 및 면허",
        "자격증",
        "컴퓨터 사용능력",
        "외국어",
        "성적",
        "학력",
        "활용능력",
        "수행 프로젝트",
        "교육/연수",
        "기타",
    ]

    for header in sorted(headers, key=len, reverse=True):
        text = re.sub(rf"(?<![가-힣A-Za-z0-9]){re.escape(header)}(?![가-힣A-Za-z0-9])", f"\n{header}\n", text)

    text = re.sub(
        r"기간\s*\n?\s*직장명\s*\n?\s*부서/직위\s*\n?\s*담당업무\s*\n?\s*이직사유",
        "\n기간 직장명 부서/직위 담당업무 이직사유\n",
        text
    )

    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# -----------------------------
# 10. 날짜 시작 행 분리
# -----------------------------
def separate_date_started_rows(text: str) -> str:
    if not text:
        return ""

    # 학력/경력 표 행에는 도움이 되지만, TOEIC/HSK 같은 외국어 날짜는 쪼개지 않도록 보호한다.
    protected_tests = {"TOEIC", "TOEFL", "OPIC", "OPIc", "IELTS", "TEPS", "JLPT", "HSK"}

    def repl(match):
        start = match.start(1)
        prev = text[max(0, start - 16):start]
        if any(test.lower() in prev.lower() for test in protected_tests):
            return match.group(1)
        return "\n" + match.group(1)

    text = re.sub(r"(?<![\n\-\d])(\b20\d{2}-\d{1,2}\b)", repl, text)
    text = re.sub(r"(\d{4}-\d{1,2})-(\d{4}-\d{1,2})", r"\1 ~ \2", text)
    text = re.sub(r"\s*~\s*", " ~ ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# -----------------------------
# 11. 경력표 뒤 자기소개 경계 보정
# -----------------------------
def separate_resume_body_boundaries(text: str) -> str:
    if not text:
        return ""

    boundary_words = [
        "경력사항",
        "내용기술",
        "자기소개서상의 모든 기재사항",
        "자기소개서 상의 모든 기재사항",
        "위에 기재한 사항은 사실과 틀림이 없습니다",
        "작성자",
        "기타",
    ]

    for word in boundary_words:
        text = re.sub(rf"\s*{re.escape(word)}\s*", f"\n{word}\n", text)

    text = re.sub(r"(계약 만기|인턴 종료 및 학업 복귀|인턴 종료|학업 복귀)\s+(저는|제가)", r"\1\n\2", text)
    text = re.sub(r"(이직)\s+(저는|제가)", r"\1\n\2", text)

    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# -----------------------------
# 12. 빈 표 헤더 노이즈 정리
# -----------------------------
def normalize_empty_table_header_noise(text: str) -> str:
    if not text:
        return ""

    text = re.sub(
        r"병역구분\s*계급\s*병과\(주특기\)\s*\|?\s*제대구분\s*기간\s*(특이사항|사항)?",
        "병역사항",
        text
    )
    text = re.sub(
        r"구분\s*계급\s*병과\(주특기\)\s*\|?\s*제대구분\s*기간\s*(특이사항|사항)?",
        "병역사항",
        text
    )

    text = re.sub(
        r"명\s*칭\s*기관\(단체\)명\s*일\s*자\s*내\s*용",
        "명칭 기관(단체)명 일자 내용",
        text
    )

    return text.strip()


# -----------------------------
# 13. 이력서 특화 깨짐 보정
# -----------------------------
def normalize_resume_specific_words(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "참 여": "참여",
        "능 력": "능력",
        "모 델": "모델",
        "실 |용적인": "실용적인",
        "타 기": "기타",
        "타기": "기타",
        "간 특이사항": "특이사항",
        "간특이사항": "특이사항",
        "보병전역": "보병 전역",
        "경 험": "경험",
        "미디어커뮤니 케이션": "미디어커뮤니케이션",
        "데이터사이언": "데이터사이언스",
        "ADSP": "ADsP",
        "1 급": "1급",
        "2 급": "2급",
    }

    for before, after in replacements.items():
        text = text.replace(before, after)

    return text


# -----------------------------
# 14. 최종 공백 정리
# -----------------------------
def final_cleanup(text: str) -> str:
    if not text:
        return ""

    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]{2,}", " ", line).strip()
        lines.append(line)

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# -----------------------------
# 15. 전체 전처리
# -----------------------------
def preprocess_text(text: str) -> str:
    text = normalize_whitespace(text)
    text = remove_ocr_noise(text)
    text = normalize_line_format(text)
    text = normalize_inline_text_patterns(text)
    text = normalize_email_and_url(text)
    text = merge_broken_korean_lines(text)

    text = normalize_section_headers(text)
    text = normalize_resume_table_headers(text)
    text = normalize_resume_specific_words(text)
    text = normalize_empty_table_header_noise(text)
    text = add_newlines_around_resume_headers(text)
    text = separate_date_started_rows(text)
    text = separate_resume_body_boundaries(text)

    text = final_cleanup(text)
    return text
