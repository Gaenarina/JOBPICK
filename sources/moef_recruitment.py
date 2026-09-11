"""Client and normalizer for the MOEF public-institution recruitment API.

The API is published through data.go.kr and backed by JOB-ALIO.
This module does not know about Firestore so that fetching and
normalization can be tested without credentials or network access.
"""

from __future__ import annotations

import json
import os
import re

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import unquote, urlencode
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://apis.data.go.kr/1051000/recruitment/list"


# ============================================================
# JOBPICK 최종 카테고리
# ============================================================

NORMALIZED_CATEGORIES = {
    "IT/개발",
    "의료/바이오",
    "디자인",
    "마케팅",
    "영업·고객상담",
    "교육",
    "운전/운송/배송",
    "건축/시설",
    "사무·총무",
    "기타",
}


def map_moef_category(*values: Any) -> str:
    """
    JOB-ALIO NCS 정보 등을 JOBPICK 카테고리로 변환한다.

    하나의 공고에서 여러 JOBPICK 카테고리가 동시에 발견되면
    특정 하나로 억지 분류하지 않고 '기타'로 처리한다.

    이미 JOBPICK 카테고리로 정규화된 값이 들어온 경우에는
    그 값을 그대로 반환한다.
    """

    flattened_values: List[str] = []

    for value in values:
        if isinstance(value, (list, tuple, set)):
            flattened_values.extend(
                _text(item)
                for item in value
                if _text(item)
            )
        else:
            value_text = _text(value)
            if value_text:
                flattened_values.append(value_text)

    # route.js 등에서 이미 정규화된 category가 다시 넘어오는 경우
    for value in flattened_values:
        if value in NORMALIZED_CATEGORIES:
            return value

    source = " ".join(flattened_values).lower()

    rules = [
        (
            "IT/개발",
            [
                "정보통신",
                "정보기술",
                "소프트웨어",
                "데이터",
                "인공지능",
                "전산",
                "개발",
            ],
        ),
        (
            "의료/바이오",
            [
                "보건·의료",
                "보건.의료",
                "보건의료",
                "의료",
                "바이오",
                "생명과학",
                "제약",
            ],
        ),
        (
            "디자인",
            [
                "문화·예술·디자인·방송",
                "문화.예술.디자인.방송",
                "디자인",
                "문화예술",
                "방송",
                "콘텐츠",
                "섬유·의복",
                "섬유.의복",
            ],
        ),
        (
            "마케팅",
            [
                "마케팅",
                "광고",
                "홍보",
                "시장조사",
            ],
        ),
        (
            "영업·고객상담",
            [
                "영업판매",
                "영업·판매",
                "영업.판매",
                "고객상담",
                "판매",
            ],
        ),
        (
            "교육",
            [
                "교육·자연·사회과학",
                "교육.자연.사회과학",
                "교육",
                "교사",
                "강사",
            ],
        ),
        (
            "운전/운송/배송",
            [
                "운전·운송",
                "운전.운송",
                "운전운송",
                "운송",
                "물류",
                "배송",
            ],
        ),
        (
            "건축/시설",
            [
                "건설",
                "건축",
                "시설",
                "기계",
                "전기·전자",
                "전기.전자",
                "전기전자",
                "환경·에너지·안전",
                "환경.에너지.안전",
            ],
        ),
        (
            "사무·총무",
            [
                "사업관리",
                "경영·회계·사무",
                "경영.회계.사무",
                "경영회계사무",
                "금융·보험",
                "금융.보험",
                "금융보험",
                "행정",
                "총무",
                "회계",
            ],
        ),
    ]

    matched_categories = []

    for category, keywords in rules:
        if any(
            keyword.lower() in source
            for keyword in keywords
        ):
            matched_categories.append(category)

    matched_categories = list(
        dict.fromkeys(matched_categories)
    )

    if len(matched_categories) == 1:
        return matched_categories[0]

    # 여러 분야가 섞인 통합공고
    if len(matched_categories) > 1:
        return "기타"

    return "기타"


# ============================================================
# 기본 텍스트 처리
# ============================================================

def _text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, dict):
        for key in (
            "name",
            "value",
            "text",
            "title",
        ):
            if value.get(key):
                return _text(value[key])

        return " ".join(
            _text(item)
            for item in value.values()
            if _text(item)
        )

    if isinstance(value, list):
        return ", ".join(
            _text(item)
            for item in value
            if _text(item)
        )

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()


def _list(value: Any) -> List[str]:
    """
    코드, 지역, NCS 등 단순 목록용.
    쉼표도 구분자로 사용한다.
    """

    if value is None or value == "":
        return []

    if isinstance(value, list):
        result = []

        for item in value:
            result.extend(_list(item))

        return list(dict.fromkeys(result))

    if isinstance(value, dict):
        return _list(
            value.get("name")
            or value.get("text")
            or value.get("value")
            or list(value.values())
        )

    parts = re.split(
        r"[\r\n|;,]+",
        str(value),
    )

    return list(
        dict.fromkeys(
            part.strip()
            for part in parts
            if part.strip()
        )
    )


LIST_MARKER_PATTERN = re.compile(
    r"^\s*(?:"
    r"[-–—•·ㆍ※○?]+"
    r"|[oOㅇ](?=\s|[가-힣])"
    r"|[가-하][.)]"
    r"|(?:\d+)[.)]"
    r"|[①-⑳]"
    r")\s*"
)


def _strip_list_marker(value: str) -> str:
    value = LIST_MARKER_PATTERN.sub(
        "",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def _line_list(value: Any) -> List[str]:
    """
    전형절차처럼 줄 단위 의미가 있는 필드용.
    쉼표는 분리하지 않는다.
    """

    if value is None or value == "":
        return []

    if isinstance(value, list):
        result = []

        for item in value:
            result.extend(_line_list(item))

        return list(dict.fromkeys(result))

    if isinstance(value, dict):
        return _line_list(
            value.get("name")
            or value.get("text")
            or value.get("value")
            or list(value.values())
        )

    parts = re.split(
        r"[\r\n|]+",
        str(value),
    )

    result = []

    for part in parts:
        cleaned = _strip_list_marker(
            part
        )

        if cleaned:
            result.append(cleaned)

    return list(dict.fromkeys(result))


# ============================================================
# 자격요건 전용 처리
# ============================================================

def _clean_qualification_text(
    value: Any,
) -> str:
    """
    자격조건 뒤에 붙는
    '자세한 사항은 공고문 참조' 등의 안내문만 제거한다.

    앞에 실제 조건이 존재하면 실제 조건은 유지한다.
    """

    cleaned = _text(value)

    if not cleaned:
        return ""

    detail_match = re.search(
        r"(?:\(\*?\s*|※\s*)?"
        r"(?:보다\s+)?자세한\s+사항은",
        cleaned,
        flags=re.IGNORECASE,
    )

    if detail_match:
        cleaned = cleaned[
            : detail_match.start()
        ]

    cleaned = cleaned.strip(
        " \t\r\n,;:*()"
    )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    ).strip()

    compact = re.sub(
        r"\s+",
        "",
        cleaned,
    )

    # 안내문을 잘라내고 의미 없는 말만 남은 경우
    vague_patterns = {
        "제한경쟁요건",
        "제한경쟁요건등",
        "모집분야별응시자격",
        "모집분야별응시자격등",
        "응시자격",
        "응시자격등",
        "지원자격",
        "지원자격등",
    }

    if compact in vague_patterns:
        return ""

    if compact in {
        "가점사항",
        "우대사항",
        "우대조건",
        "우대자격",
    }:
        return ""

    # 문장 전체가 단순 공고문 참조 안내인 경우
    if (
        ("공고문" in compact or "첨부파일" in compact)
        and (
            "참조" in compact
            or "참고" in compact
        )
    ):
        return ""

    return cleaned


def _qualification_list(
    value: Any,
) -> List[str]:
    """
    자격요건 전용 파서.

    - 쉼표는 자르지 않는다.
    - 목록기호가 있는 줄은 새로운 조건으로 본다.
    - 목록기호 없이 이어지는 줄은 바로 앞 조건의 연속문장으로 본다.

    예:
      - (...) 보호조치가 종료되거나 5년이 지나지 않은
        자립준비청년 (보호종료아동)

    -> 하나의 조건으로 합쳐진다.
    """

    if value is None or value == "":
        return []

    if isinstance(value, list):
        result = []

        for item in value:
            result.extend(
                _qualification_list(item)
            )

        return list(dict.fromkeys(result))

    if isinstance(value, dict):
        return _qualification_list(
            value.get("name")
            or value.get("text")
            or value.get("value")
            or list(value.values())
        )

    raw_lines = re.split(
        r"[\r\n|]+",
        str(value),
    )

    result = []
    current = ""

    for raw_line in raw_lines:
        raw_line = raw_line.strip()

        if not raw_line:
            continue

        has_marker = bool(
            LIST_MARKER_PATTERN.match(
                raw_line
            )
        )

        cleaned = _strip_list_marker(
            raw_line
        )

        if not cleaned:
            continue

        # (공통사항), (체험형 청년인턴_장애인) 등
        # 구분명이 새로 시작하면 새로운 조건
        starts_labeled_condition = bool(
            re.match(
                r"^\([^)]{1,100}\)",
                cleaned,
            )
        )

        if (
            not current
            or has_marker
            or starts_labeled_condition
        ):
            if current:
                normalized = (
                    _clean_qualification_text(
                        current
                    )
                )

                if normalized:
                    result.append(
                        normalized
                    )

            current = cleaned

        else:
            current = (
                f"{current} {cleaned}"
            ).strip()

    if current:
        normalized = (
            _clean_qualification_text(
                current
            )
        )

        if normalized:
            result.append(normalized)

    return list(
        dict.fromkeys(result)
    )


# ============================================================
# 특정 모집분야 전용 조건 판단
# ============================================================

def _is_conditional_qualification(
    value: Any,
) -> bool:
    """
    전체 지원자 공통 조건이 아니라
    특정 모집유형/제한경쟁 대상자에게만 적용되는 조건인지 판단.

    보수적으로 분리해서 전체 공고의 필수 룰 점수에
    잘못 들어가지 않도록 한다.
    """

    cleaned = _text(value)

    match = re.match(
        r"^\(([^)]+)\)",
        cleaned,
    )

    if not match:
        return False

    label = re.sub(
        r"\s+",
        "",
        match.group(1),
    ).lower()

    # 공통사항은 모든 지원자에게 적용
    if (
        "공통" in label
        or "전체" in label
    ):
        return False

    conditional_markers = [
        "_",
        "제한경쟁",
        "장애인",
        "자립준비",
        "북한이탈",
        "다문화",
        "보훈",
        "취업지원",
        "지역인재",
        "고졸",
        "특성화고",
        "체험형청년인턴",
        "채용형인턴",
        "기간제",
        "무기계약",
        "직무",
        "직종",
        "분야",
    ]

    return any(
        marker in label
        for marker
        in conditional_markers
    )


def _split_required_qualifications(
    value: Any,
) -> tuple[List[str], List[str]]:
    required = []
    conditional = []

    for qualification in _qualification_list(
        value
    ):
        if _is_conditional_qualification(
            qualification
        ):
            conditional.append(
                qualification
            )
        else:
            required.append(
                qualification
            )

    return (
        list(dict.fromkeys(required)),
        list(dict.fromkeys(conditional)),
    )

def _parse_application_requirements(
    value: Any,
) -> tuple[List[str], List[str], List[str]]:
    """
    JOB-ALIO aplyQlfcCn을 분석하여 다음을 분리한다.

    1. requiredQualifications
       - 전체 지원자에게 적용되는 공통조건

    2. conditionalQualifications
       - 특정 직종/모집분야에만 적용되는 조건

    3. responsibilities
       - 원문에 '담당업무:'가 명시된 경우에만 추출

    담당업무/계약기간을 자격요건으로 잘못 저장하지 않는다.
    """

    if value is None or value == "":
        return [], [], []

    raw_lines = re.split(
        r"[\r\n|]+",
        str(value),
    )

    raw_lines = [
        line.strip()
        for line in raw_lines
        if line.strip()
    ]

    required: List[str] = []
    conditional: List[str] = []
    responsibilities: List[str] = []

    current_scope = "common"
    current_group = ""

    def add_required(text_value: str):
        cleaned = _clean_qualification_text(
            text_value
        )

        if cleaned:
            required.append(cleaned)

    def add_conditional(
        text_value: str,
        group: str = "",
    ):
        cleaned = _clean_qualification_text(
            text_value
        )

        if not cleaned:
            return

        if group:
            cleaned = (
                f"({group}) {cleaned}"
            )

        conditional.append(cleaned)

    def add_responsibility(
        text_value: str,
        group: str = "",
    ):
        cleaned = _text(text_value)

        if not cleaned:
            return

        if group:
            cleaned = (
                f"({group}) {cleaned}"
            )

        responsibilities.append(cleaned)

    for index, raw_line in enumerate(
        raw_lines
    ):
        cleaned_line = (
            _strip_list_marker(
                raw_line
            )
        )

        if not cleaned_line:
            continue

        compact = re.sub(
            r"\s+",
            "",
            cleaned_line,
        ).lower()

        # ----------------------------------------------------
        # 공통 조건 섹션
        # ----------------------------------------------------

        if compact in {
            "공통",
            "공통사항",
            "공통자격",
            "공통자격요건",
        }:
            current_scope = "common"
            current_group = ""
            continue

        # ----------------------------------------------------
        # 직종/모집분야별 조건 섹션
        # ----------------------------------------------------

        if any(
            keyword in compact
            for keyword in [
                "직종별자격",
                "직종별자격요건",
                "모집분야별자격",
                "모집분야별자격요건",
                "분야별자격",
                "분야별자격요건",
            ]
        ):
            current_scope = "conditional"
            current_group = ""
            continue

        # ----------------------------------------------------
        # 1. 청년인턴(채용형-일반행정) 1명
        #
        # 바로 뒤에 담당업무/자격요건이 나오면
        # 모집분야 제목으로 판단
        # ----------------------------------------------------

        numbered_header = bool(
            re.match(
                r"^\s*\d+[.)]\s*",
                raw_line,
            )
        )

        if numbered_header:
            next_lines = " ".join(
                raw_lines[
                    index + 1:
                    index + 4
                ]
            )

            has_structured_fields = (
                "담당업무" in next_lines
                or "자격요건" in next_lines
            )

            if has_structured_fields:
                group_name = re.sub(
                    r"\s+\d+\s*명\s*$",
                    "",
                    cleaned_line,
                ).strip()

                current_scope = (
                    "conditional"
                )
                current_group = (
                    group_name
                )
                continue

        # ----------------------------------------------------
        # 직종별 자격 섹션:
        #
        # 1) KDN조공: 해당분야 ...
        # 2) 현장보조원
        # ----------------------------------------------------

        if (
            current_scope
            == "conditional"
            and numbered_header
        ):
            body = cleaned_line

            if ":" in body or "：" in body:
                parts = re.split(
                    r"[:：]",
                    body,
                    maxsplit=1,
                )

                group_name = (
                    parts[0].strip()
                )

                condition_text = (
                    parts[1].strip()
                    if len(parts) > 1
                    else ""
                )

                if group_name:
                    current_group = (
                        group_name
                    )

                if condition_text:
                    add_conditional(
                        condition_text,
                        current_group,
                    )

                continue

            current_group = re.sub(
                r"\s+\d+\s*명\s*$",
                "",
                body,
            ).strip()

            continue

        # ----------------------------------------------------
        # 담당업무
        # ----------------------------------------------------

        responsibility_match = re.search(
            r"(?:담당업무|담당 업무)"
            r"\s*[:：]\s*(.+)$",
            cleaned_line,
            flags=re.IGNORECASE,
        )

        if responsibility_match:
            add_responsibility(
                responsibility_match.group(
                    1
                ),
                current_group,
            )
            continue

        # ----------------------------------------------------
        # 계약기간은 자격요건에서 제외
        # ----------------------------------------------------

        if re.search(
            r"(?:계약기간|근무기간)"
            r"\s*[:：]",
            cleaned_line,
            flags=re.IGNORECASE,
        ):
            continue

        # ----------------------------------------------------
        # 자격요건:
        # ----------------------------------------------------

        qualification_match = re.search(
            r"(?:자격요건|지원자격|응시자격)"
            r"\s*[:：]\s*(.+)$",
            cleaned_line,
            flags=re.IGNORECASE,
        )

        if qualification_match:
            qualification_text = (
                qualification_match.group(
                    1
                )
            )

            if current_group:
                add_conditional(
                    qualification_text,
                    current_group,
                )
            else:
                add_required(
                    qualification_text
                )

            continue

        # ----------------------------------------------------
        # 특정 모집그룹 안에 있는 후속 조건
        # ----------------------------------------------------

        if current_group:
            add_conditional(
                cleaned_line,
                current_group,
            )
            continue

        # ----------------------------------------------------
        # 직종별 조건 섹션
        # ----------------------------------------------------

        if (
            current_scope
            == "conditional"
        ):
            add_conditional(
                cleaned_line,
                current_group,
            )
            continue

        # ----------------------------------------------------
        # 일반 공통 자격요건
        # ----------------------------------------------------

        add_required(
            cleaned_line
        )

    return (
        list(
            dict.fromkeys(required)
        ),
        list(
            dict.fromkeys(conditional)
        ),
        list(
            dict.fromkeys(
                responsibilities
            )
        ),
    )


# ============================================================
# 전형단계
# ============================================================

def _steps(value: Any) -> List[str]:
    """
    API가 실제 전형 단계명을 제공할 때만 저장한다.

    내부 ID, 경쟁률, 모집인원 등의 객체 전체를
    문자열로 변환하지 않는다.
    """

    if not value:
        return []

    values = (
        value
        if isinstance(value, list)
        else [value]
    )

    result = []

    for item in values:
        if isinstance(item, dict):
            label = _text(
                item.get("recrutStepNm")
                or item.get("stepNm")
                or item.get("name")
                or item.get(
                    "recrutStepExpln"
                )
            )
        else:
            label = _text(item)

        if label:
            result.append(label)

    return list(dict.fromkeys(result))


# ============================================================
# 첨부파일
# ============================================================

def _files(
    value: Any,
) -> List[Dict[str, str]]:

    if not value:
        return []

    values = (
        value
        if isinstance(value, list)
        else [value]
    )

    result = []

    for item in values:
        if isinstance(item, dict):
            file_data = {
                "name": _text(
                    item.get("atchFileNm")
                    or item.get("fileNm")
                    or item.get("name")
                ),

                "url": _text(
                    item.get("url")
                    or item.get("fileUrl")
                    or item.get(
                        "atchFileUrl"
                    )
                ),

                "type": _text(
                    item.get(
                        "atchFileTypeNm"
                    )
                    or item.get(
                        "atchFileType"
                    )
                    or item.get(
                        "fileType"
                    )
                    or item.get("type")
                ),
            }

        else:
            file_data = {
                "name": _text(item),
                "url": "",
                "type": "",
            }

        if (
            file_data["name"]
            or file_data["url"]
        ):
            result.append(file_data)

    return result


# ============================================================
# 접수방법 추출
# ============================================================

def _extract_application_method(
    value: Any,
) -> str:

    if not value:
        return ""

    match = re.search(
        r"(?:접수방법|접수 방법)"
        r"\s*[:：]\s*"
        r"([^\r\n※]+)",
        str(value),
    )

    if not match:
        return ""

    return _text(
        match.group(1)
    )


# ============================================================
# API 응답 구조 처리
# ============================================================

def _get_items(
    payload: Dict[str, Any],
) -> List[Dict[str, Any]]:

    candidates: Iterable[Any] = (
        payload.get("result"),

        payload.get("items"),

        (
            payload.get("response")
            or {}
        )
        .get("body", {})
        .get("items")
        if isinstance(
            payload.get("response"),
            dict,
        )
        else None,
    )

    for candidate in candidates:
        if isinstance(
            candidate,
            dict,
        ):
            candidate = (
                candidate.get("item")
                or candidate.get("items")
                or candidate
            )

        if isinstance(
            candidate,
            list,
        ):
            return [
                item
                for item in candidate
                if isinstance(
                    item,
                    dict,
                )
            ]

        if isinstance(
            candidate,
            dict,
        ):
            return [candidate]

    return []


def get_total_count(
    payload: Dict[str, Any],
) -> int:

    for value in (
        payload.get("totalCount"),

        (
            payload.get("response")
            or {}
        )
        .get("body", {})
        .get("totalCount")
        if isinstance(
            payload.get("response"),
            dict,
        )
        else None,
    ):
        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):
            continue

    return len(
        _get_items(payload)
    )


# ============================================================
# JOB-ALIO → JOBPICK 정규화
# ============================================================

SEMANTIC_EXCLUDE_KEYWORDS = [
    # 법적/행정적 지원조건
    "결격사유",
    "인사규정",
    "국가공무원법",
    "병역",
    "해외여행",
    "징계",
    "채용비리",
    "부정한방법으로채용",

    # 근무 가능 여부
    "즉시근무",
    "바로근무",
    "즉시업무종사",
    "업무종사가능",
    "근무가가능",
    "근무가능",
    "임용예정일부터",
    "채용예정일즉시",

    # 입대/전역
    "전역예정",
    "전역예정자",

    # 연령/신분/정책 가점
    "청년연령",
    "취업지원대상",
    "취업보호대상",
    "장애대상",
    "장애인",
    "지역인재",
    "정부권장정책",
    "국민기초생활수급",
    "차상위",
    "한부모",
    "북한이탈",
    "다문화",
    "경력단절여성",
    "자립준비청년",
    "국가유공자",
    "보훈대상",
    "취업취약계층",

    # 지역/거주 조건
    "주민등록상주소지",
    "거주지",

    # 가점/전형 안내
    "전형별가점",
    "가점적용기준",
    "가산점부여",
    "만점의5%",
    "만점의10%",
    "대상별가산점수가",

    # 계약정보
    "계약기간",
]


def _is_semantic_relevant_qualification(
    value: Any,
) -> bool:

    raw = _text(value)

    if not raw:
        return False

    compact = re.sub(
        r"\s+",
        "",
        raw,
    ).lower()

    # 숫자/퍼센트만 남은 조각
    if not re.search(
        r"[가-힣a-zA-Z]",
        raw,
    ):
        return False

    # 단순 제목
    if compact in {
        "가점사항",
        "가점적용기준",
        "우대사항",
        "우대조건",
        "직종별우대사항",
        "직종별자격",
        "직종별자격요건",
    }:
        return False

    # 학력·연령 등의 제한이 "없다"는 것은
    # 적합도 비교 대상이 아님
    if (
        "제한없음" in compact
        and any(
            keyword in compact
            for keyword in [
                "학력",
                "연령",
                "나이",
                "성별",
                "지역",
                "외국어",
                "경력",
            ]
        )
    ):
        return False

    # 단순 연령조건
    if re.search(
        r"만\s*\d+\s*세",
        raw,
    ):
        return False

    if any(
        keyword.lower()
        in compact
        for keyword
        in SEMANTIC_EXCLUDE_KEYWORDS
    ):
        return False

    return True


def _semantic_qualification_list(
    values: List[str],
) -> List[str]:

    result: List[str] = []

    for value in values:
        original = _text(value)

        if not original:
            continue

        original_compact = re.sub(
            r"\s+",
            "",
            original,
        ).lower()

        # "학력, 연령, 외국어 제한 없음"처럼
        # 문장 전체가 비점수 조건이면 분리하지 않고 제거
        if (
            "제한없음"
            in original_compact
            and any(
                keyword
                in original_compact
                for keyword in [
                    "학력",
                    "연령",
                    "나이",
                    "성별",
                    "지역",
                    "외국어",
                    "경력",
                ]
            )
        ):
            continue

        # embedding용에서만 쉼표/세미콜론 분리
        parts = re.split(
            r"[,;]+",
            original,
        )

        for part in parts:
            cleaned = _text(part)

            if not cleaned:
                continue

            if (
                _is_semantic_relevant_qualification(
                    cleaned
                )
            ):
                result.append(
                    cleaned
                )

    return list(
        dict.fromkeys(result)
    )

def normalize_recruitment(
    item: Dict[str, Any],
) -> Dict[str, Any]:

    external_id = _text(
        item.get("recrutPblntSn")
        or item.get(
            "recruitmentId"
        )
        or item.get("id")
    )

    if not external_id:
        raise ValueError(
            "Recruitment item has no recrutPblntSn"
        )

    title = _text(
        item.get(
            "recrutPbancTtl"
        )
    )

    company = _text(
        item.get("instNm")
    )

    source_url = _text(
        item.get("srcUrl")
    )


    # --------------------------------------------------------
    # NCS
    # --------------------------------------------------------

    ncs_names = _list(
        item.get("ncsCdNmLst")
    )

    ncs_source_codes = _list(
        item.get("ncsCdLst")
    )


    # --------------------------------------------------------
    # 기본 채용 조건
    # --------------------------------------------------------

    locations = _list(
        item.get("workRgnNmLst")
    )

    education_names = _list(
        item.get("acbgCondNmLst")
    )

    hire_types = _list(
        item.get("hireTypeNmLst")
    )

    recruitment_types = _list(
        item.get("recrutSeNm")
    )


    # --------------------------------------------------------
    # 필수 / 조건부 자격요건 분리
    # --------------------------------------------------------

    (
        required_qualifications,
        conditional_qualifications,
        responsibilities,
    ) = _parse_application_requirements(
        item.get("aplyQlfcCn")
    )


    # --------------------------------------------------------
    # 우대사항
    #
    # prefCn이 상세 내용인 경우가 많으므로 우선 사용하고,
    # 없을 경우 prefCondCn을 사용한다.
    # --------------------------------------------------------

    preferred_source = (
        item.get("prefCn")
        or item.get("prefCondCn")
    )

    preferred_qualifications = (
        _qualification_list(
            preferred_source
        )
    )


    # --------------------------------------------------------
    # 전형절차
    # --------------------------------------------------------

    screening = _line_list(
        item.get(
            "scrnprcdrMthdExpln"
        )
    )

    steps = _steps(
        item.get("steps")
    )


    # --------------------------------------------------------
    # 카테고리
    # --------------------------------------------------------

    raw_category = (
        ", ".join(ncs_names)
        or ", ".join(
            recruitment_types
        )
    )

    # NCS가 있으면 NCS를 가장 우선적으로 사용
    category_sources = (
        ncs_names
        if ncs_names
        else [
            title,
            *recruitment_types,
        ]
    )

    category = map_moef_category(
        category_sources
    )


    employment_type = ", ".join(
        hire_types
    )

    education = ", ".join(
        education_names
    )

    location = ", ".join(
        locations
    )

    recruitment_type = ", ".join(
        recruitment_types
    )


    # --------------------------------------------------------
    # 모집인원
    # --------------------------------------------------------

    hiring_count = item.get(
        "recrutNope"
    )

    if hiring_count is None:
        hiring_count = item.get(
            "recrutNope2",
            "",
        )


    # --------------------------------------------------------
    # 임베딩 텍스트
    #
    # 특정 모집유형에만 해당하는 conditionalQualifications는
    # 전체 공고 임베딩에서 제외한다.
    # --------------------------------------------------------

    semantic_required_qualifications = (
    _semantic_qualification_list(
        required_qualifications
    )
    )

    semantic_preferred_qualifications = (
    _semantic_qualification_list(
        preferred_qualifications
    )
    )

    embedding_parts = [
        title,
        category,
        *ncs_names,
        education,
        recruitment_type,
        *responsibilities,
        *semantic_required_qualifications,
        *semantic_preferred_qualifications,
    ]

    embedding_text = " / ".join(
        part
        for part in embedding_parts
        if part
    )


    job_posting = {
        "title":
            title,

        "companyName":
            company,

        "category":
            category,

        "sourceUrl":
            source_url,

        "sourceSite":
            "moef_job_alio",

        "postingType":
            "open_api",


        "job": {
            "department":
                category,

            "employmentType":
                employment_type,

            "hiringCount":
                hiring_count,

            "recruitmentType":
                recruitment_type,
        },


        "responsibilities":
            responsibilities,


        "requirements": {
            "education": {
                "minimum":
                    education,

                "raw":
                    education,
            },

            "experience": {
                "type":
                    recruitment_type,

                "raw":
                    recruitment_type,
            },

            "requiredSkills": [],

            "preferredSkills": [],

            # 모든 지원자에게 적용되는 필수조건
            "requiredQualifications":
                required_qualifications,

            # 특정 직무/제한경쟁에만 적용되는 조건
            "conditionalQualifications":
                conditional_qualifications,

            "preferredQualifications":
                preferred_qualifications,

            "coreCompetencies": [],

            "certifications": [],
        },


        "workConditions": {
            "location":
                location,

            "salary":
                "",
        },


        "recruitment": {
            "startDate":
                _text(
                    item.get(
                        "pbancBgngYmd"
                    )
                ),

            "endDate":
                _text(
                    item.get(
                        "pbancEndYmd"
                    )
                ),

            "isActive":
                _text(
                    item.get(
                        "ongoingYn"
                    )
                ).upper() == "Y",

            "steps":
                steps,

            "screeningProcedure":
                screening,

            "applicationMethod":
                _extract_application_method(
                    item.get(
                        "scrnprcdrMthdExpln"
                    )
                ),
        },


        "ncs": {
            # JOB-ALIO의 R6000xx 값은
            # 실제 NCS 능력단위 코드와 분리한다.
            "codes": [],

            "names":
                ncs_names,

            "sourceCodes":
                ncs_source_codes,
        },


        "sourceCategory":
            raw_category,


        "attachments":
            _files(
                item.get("files")
            ),


        "embeddingText": {
            "fullForEmbedding":
                embedding_text,

            "responsibilitiesForEmbedding":
                " / ".join(
                    responsibilities
                ),

            "qualificationsForEmbedding":
                " / ".join(
                    [
                        *semantic_required_qualifications,
                        *semantic_preferred_qualifications,
                    ]
                ),
        },
    }


    return {
        "externalId":
            external_id,

        "documentId":
            f"moef_{external_id}",

        "jobPosting":
            job_posting,

        "meta": {
            "source":
                "moef_job_alio",

            "sourceUrl":
                source_url,

            "companyName":
                company,

            "title":
                title,

            "postingType":
                "open_api",

            "externalId":
                external_id,
        },

        "rawApiData":
            item,
    }


# ============================================================
# API Client
# ============================================================

@dataclass
class MoefRecruitmentClient:
    service_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout: int = 30

    @classmethod
    def from_env(
        cls,
    ) -> "MoefRecruitmentClient":

        service_key = (
            os.getenv(
                "MOEF_RECRUITMENT_API_KEY",
                "",
            ).strip()
        )

        if not service_key:
            raise RuntimeError(
                "MOEF_RECRUITMENT_API_KEY is required. "
                "Use the decoding service key issued by data.go.kr."
            )

        return cls(
            service_key=
                service_key,

            base_url=
                os.getenv(
                    "MOEF_RECRUITMENT_API_URL",
                    DEFAULT_BASE_URL,
                ).strip(),
        )

    def fetch_page(
        self,
        page_no: int = 1,
        num_of_rows: int = 100,
        **filters: Any,
    ) -> Dict[str, Any]:

        service_key = (
            unquote(
                self.service_key
            )
            if re.search(
                r"%[0-9a-fA-F]{2}",
                self.service_key,
            )
            else self.service_key
        )

        params = {
            "serviceKey":
                service_key,

            "pageNo":
                page_no,

            "numOfRows":
                num_of_rows,

            **{
                key: value
                for key, value
                in filters.items()
                if value
                not in (
                    None,
                    "",
                )
            },
        }

        request = Request(
            f"{self.base_url}?{urlencode(params)}",

            headers={
                "Accept":
                    "application/json",

                "User-Agent":
                    "JOBPICK/1.0",
            },
        )

        with urlopen(
            request,
            timeout=self.timeout,
        ) as response:

            payload = json.loads(
                response
                .read()
                .decode(
                    "utf-8-sig"
                )
            )

        result_code = payload.get(
            "resultCode"
        )

        if result_code not in (
            None,
            0,
            "0",
            "00",
            200,
            "200",
        ):
            raise RuntimeError(
                f"MOEF API error {result_code}: "
                f"{payload.get('resultMsg', '')}"
            )

        return payload

    def iter_recruitments(
        self,
        num_of_rows: int = 100,
        max_pages: Optional[int] = None,
        **filters: Any,
    ) -> Iterable[Dict[str, Any]]:

        page_no = 1
        yielded = 0

        while (
            max_pages is None
            or page_no <= max_pages
        ):

            payload = self.fetch_page(
                page_no=
                    page_no,

                num_of_rows=
                    num_of_rows,

                **filters,
            )

            items = _get_items(
                payload
            )

            if not items:
                break

            yield from items

            yielded += len(
                items
            )

            if (
                yielded
                >= get_total_count(
                    payload
                )
                or len(items)
                < num_of_rows
            ):
                break

            page_no += 1