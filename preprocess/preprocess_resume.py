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
# 점(.) 전체 치환은 하지 않음
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
# 예: 이 \n 력서  -> 이력서
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

            # 현재 줄이 한 글자 한글이고 다음 줄이 한글로 시작하는 짧은 줄이면 결합
            if re.fullmatch(r"[가-힣]", current_line) and re.match(r"^[가-힣]{1,5}$", next_line):
                merged_lines.append(current_line + next_line)
                index += 2
                continue

            # 현재 줄이 1~2글자, 다음 줄도 짧은 한글이면 결합
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
    replacements = {
        "이력 서": "이력서",
        "자기 소개서": "자기소개서",
        "경력 사항": "경력사항",
        "수상 경력": "수상경력",
        "보유 기술": "보유기술",
        "지원 분야": "지원분야",
        "희망 직무": "희망직무",
        "생 년월일": "생년월일",
    }

    for before, after in replacements.items():
        text = text.replace(before, after)

    return text


# -----------------------------
# 8. 전체 전처리
# -----------------------------
def preprocess_text(text: str) -> str:
    text = normalize_whitespace(text)
    text = remove_ocr_noise(text)
    text = normalize_line_format(text)
    text = normalize_inline_text_patterns(text)
    text = normalize_email_and_url(text)
    text = merge_broken_korean_lines(text)
    text = normalize_section_headers(text)

    return text