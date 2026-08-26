"""Client and normalizer for the MOEF public-institution recruitment API.

The API is published through data.go.kr and backed by JOB-ALIO.  This module
does not know about Firestore so that fetching and normalization can be tested
without credentials or network access.
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


def map_moef_category(*values: Any) -> str:
    source = " ".join(_text(value) for value in values if _text(value)).lower()
    rules = [
        ("IT/개발", ["정보통신", "정보기술", "소프트웨어", "데이터", "인공지능", "전산", "개발"]),
        ("의료/바이오", ["보건·의료", "보건의료", "의료", "바이오", "생명과학", "제약"]),
        ("디자인", ["문화·예술·디자인·방송", "디자인", "문화예술", "방송", "콘텐츠", "섬유·의복"]),
        ("마케팅", ["마케팅", "광고", "홍보", "시장조사"]),
        ("영업·고객상담", ["영업판매", "영업·판매", "고객상담", "판매"]),
        ("교육", ["교육·자연·사회과학", "교육", "교사", "강사"]),
        ("운전/운송/배송", ["운전·운송", "운전운송", "운송", "물류", "배송"]),
        ("건축/시설", ["건설", "건축", "시설", "기계", "전기·전자", "전기전자", "환경·에너지·안전"]),
        ("사무·총무", ["사업관리", "경영·회계·사무", "경영회계사무", "금융·보험", "금융보험", "행정", "총무", "회계"]),
    ]
    for category, keywords in rules:
        if any(keyword.lower() in source for keyword in keywords):
            return category
    return "기타"


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("name", "value", "text", "title"):
            if value.get(key):
                return _text(value[key])
        return " ".join(_text(item) for item in value.values() if _text(item))
    if isinstance(value, list):
        return ", ".join(_text(item) for item in value if _text(item))
    return re.sub(r"\s+", " ", str(value)).strip()


def _list(value: Any) -> List[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        result: List[str] = []
        for item in value:
            result.extend(_list(item))
        return list(dict.fromkeys(result))
    if isinstance(value, dict):
        return _list(value.get("name") or value.get("text") or value.get("value") or list(value.values()))
    parts = re.split(r"[\r\n|;,]+", str(value))
    return list(dict.fromkeys(part.strip() for part in parts if part.strip()))


def _line_list(value: Any) -> List[str]:
    """
    자격요건/우대조건처럼 '한 줄 = 한 조건' 성격의 필드를 안전하게 분리한다.

    기존 _list()는 쉼표(,)와 세미콜론(;)까지 분리하기 때문에
    하나의 조건 문장이 여러 개의 자격요건으로 과도하게 쪼개질 수 있다.

    여기서는 줄바꿈과 | 만 구분자로 사용하고,
    목록 기호(-, •, · 등)는 앞뒤에서 제거한다.
    """
    if value is None or value == "":
        return []

    if isinstance(value, list):
        result: List[str] = []
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

    parts = re.split(r"[\r\n|]+", str(value))

    result = []
    for part in parts:
        cleaned = re.sub(r"^[\s\-–—•·ㆍ※○O]+", "", part).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)

        if cleaned:
            result.append(cleaned)

    return list(dict.fromkeys(result))


def _steps(value: Any) -> List[str]:
    """
    API가 실제 전형 단계명을 제공하는 경우에만 단계명으로 사용한다.

    단계명 필드가 없는 dict 전체를 문자열로 변환하면
    채용공고명, 내부 ID, 정렬번호 등이 전형절차처럼 저장될 수 있으므로
    그런 fallback은 사용하지 않는다.
    """
    if not value:
        return []

    values = value if isinstance(value, list) else [value]
    result = []

    for item in values:
        if isinstance(item, dict):
            label = _text(
                item.get("recrutStepNm")
                or item.get("stepNm")
                or item.get("name")
                or item.get("recrutStepExpln")
            )
        else:
            label = _text(item)

        if label:
            result.append(label)

    return list(dict.fromkeys(result))


def _files(value: Any) -> List[Dict[str, str]]:
    if not value:
        return []
    values = value if isinstance(value, list) else [value]
    result = []
    for item in values:
        if isinstance(item, dict):
            result.append({
                "name": _text(item.get("atchFileNm") or item.get("fileNm") or item.get("name")),
                "url": _text(item.get("url") or item.get("fileUrl") or item.get("atchFileUrl")),
                "type": _text(item.get("atchFileTypeNm") or item.get("fileType") or item.get("type")),
            })
        elif _text(item):
            result.append({"name": _text(item), "url": "", "type": ""})
    return result


def _get_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Accept both the current flat response and common data.go.kr wrappers."""
    candidates: Iterable[Any] = (
        payload.get("result"),
        payload.get("items"),
        (payload.get("response") or {}).get("body", {}).get("items")
        if isinstance(payload.get("response"), dict)
        else None,
    )
    for candidate in candidates:
        if isinstance(candidate, dict):
            candidate = candidate.get("item") or candidate.get("items")
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
        if isinstance(candidate, dict):
            return [candidate]
    return []


def get_total_count(payload: Dict[str, Any]) -> int:
    for value in (
        payload.get("totalCount"),
        (payload.get("response") or {}).get("body", {}).get("totalCount")
        if isinstance(payload.get("response"), dict)
        else None,
    ):
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return len(_get_items(payload))


def normalize_recruitment(item: Dict[str, Any]) -> Dict[str, Any]:
    external_id = _text(item.get("recrutPblntSn") or item.get("recruitmentId") or item.get("id"))
    if not external_id:
        raise ValueError("Recruitment item has no recrutPblntSn")

    title = _text(item.get("recrutPbancTtl"))
    company = _text(item.get("instNm"))
    source_url = _text(item.get("srcUrl"))
    ncs_names = _list(item.get("ncsCdNmLst"))
    ncs_codes = _list(item.get("ncsCdLst"))
    locations = _list(item.get("workRgnNmLst"))
    education_names = _list(item.get("acbgCondNmLst"))
    hire_types = _list(item.get("hireTypeNmLst"))
    recruitment_types = _list(item.get("recrutSeNm"))
    # 지원자격은 API의 aplyQlfcCn만 사용한다.
    # 쉼표 단위로 쪼개지 않고 줄 단위로만 조건을 분리한다.
    required_qualifications = _line_list(item.get("aplyQlfcCn"))

    # JOB-ALIO는 우대조건을 prefCondCn / prefCn 두 필드로 제공할 수 있으므로
    # 둘 다 합쳐 중복 제거한다.
    preferred_qualifications = list(dict.fromkeys([
        *_line_list(item.get("prefCondCn")),
        *_line_list(item.get("prefCn")),
    ]))

    # 전형절차는 담당업무가 아니므로 responsibilities에 넣지 않는다.
    screening = _line_list(item.get("scrnprcdrMthdExpln"))
    steps = _steps(item.get("steps"))

    # API가 별도 직무기술서를 제공하지 않는 경우,
    # 담당업무에는 NCS 대분류 힌트만 최소한으로 둔다.
    responsibilities = list(dict.fromkeys(ncs_names))
    raw_category = ", ".join(ncs_names) or ", ".join(recruitment_types)
    category = map_moef_category(ncs_names, title, recruitment_types)
    employment_type = ", ".join(hire_types)
    education = ", ".join(education_names)
    location = ", ".join(locations)
    recruitment_type = ", ".join(recruitment_types)

    embedding_parts = [
        title,
        company,
        category,
        location,
        employment_type,
        recruitment_type,
        *responsibilities,
        *required_qualifications,
        *preferred_qualifications,
    ]
    embedding_text = " / ".join(part for part in embedding_parts if part)

    job_posting = {
        "title": title,
        "companyName": company,
        "category": category,
        "sourceUrl": source_url,
        "sourceSite": "moef_job_alio",
        "postingType": "open_api",
        "job": {
            "department": category,
            "employmentType": employment_type,
            "hiringCount": item.get("recrutNope", ""),
            "recruitmentType": recruitment_type,
        },
        "responsibilities": responsibilities,
        "requirements": {
            "requiredSkills": [],
            "preferredSkills": [],
            "requiredQualifications": required_qualifications,
            "preferredQualifications": preferred_qualifications,
            "coreCompetencies": ncs_names,
            "certifications": [],
            "education": {"minimum": education, "raw": education},
            "experience": {"type": recruitment_type, "raw": recruitment_type},
        },
        "workConditions": {"location": location, "salary": ""},
        "recruitment": {
            "startDate": _text(item.get("pbancBgngYmd")),
            "endDate": _text(item.get("pbancEndYmd")),
            "isActive": _text(item.get("ongoingYn")).upper() == "Y",
            "steps": steps,
            "screeningProcedure": screening,
            "applicationMethod": _text(item.get("scrnprcdrMthdExpln")),
        },
        "ncs": {
            # JOB-ALIO의 R6000xx는 실제 NCS 능력단위 코드가 아니라
            # NCS 대분류용 공통상세코드이므로 matcher의 코드 필터에 넘기지 않는다.
            "codes": [],
            "names": ncs_names,
            "sourceCodes": ncs_codes,
        },
        "sourceCategory": raw_category,
        "attachments": _files(item.get("files")),
        "embeddingText": {
            "fullForEmbedding": embedding_text,
            "responsibilitiesForEmbedding": " / ".join(responsibilities),
            "qualificationsForEmbedding": " / ".join(
                [*required_qualifications, *preferred_qualifications]
            ),
        },
    }

    return {
        "externalId": external_id,
        "documentId": f"moef_{external_id}",
        "jobPosting": job_posting,
        "meta": {
            "source": "moef_job_alio",
            "sourceUrl": source_url,
            "companyName": company,
            "title": title,
            "postingType": "open_api",
            "externalId": external_id,
        },
        "rawApiData": item,
    }


@dataclass
class MoefRecruitmentClient:
    service_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "MoefRecruitmentClient":
        service_key = os.getenv("MOEF_RECRUITMENT_API_KEY", "").strip()
        if not service_key:
            raise RuntimeError(
                "MOEF_RECRUITMENT_API_KEY is required. Use the decoding service key "
                "issued by data.go.kr."
            )
        return cls(
            service_key=service_key,
            base_url=os.getenv("MOEF_RECRUITMENT_API_URL", DEFAULT_BASE_URL).strip(),
        )

    def fetch_page(self, page_no: int = 1, num_of_rows: int = 100, **filters: Any) -> Dict[str, Any]:
        service_key = unquote(self.service_key) if re.search(r"%[0-9a-fA-F]{2}", self.service_key) else self.service_key
        params = {
            "serviceKey": service_key,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
            **{key: value for key, value in filters.items() if value not in (None, "")},
        }
        request = Request(
            f"{self.base_url}?{urlencode(params)}",
            headers={"Accept": "application/json", "User-Agent": "JOBPICK/1.0"},
        )
        with urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8-sig"))

        result_code = payload.get("resultCode")
        if result_code not in (None, 0, "0", "00", 200, "200"):
            raise RuntimeError(f"MOEF API error {result_code}: {payload.get('resultMsg', '')}")
        return payload

    def iter_recruitments(
        self,
        num_of_rows: int = 100,
        max_pages: Optional[int] = None,
        **filters: Any,
    ) -> Iterable[Dict[str, Any]]:
        page_no = 1
        yielded = 0
        while max_pages is None or page_no <= max_pages:
            payload = self.fetch_page(page_no=page_no, num_of_rows=num_of_rows, **filters)
            items = _get_items(payload)
            if not items:
                break
            yield from items
            yielded += len(items)
            if yielded >= get_total_count(payload) or len(items) < num_of_rows:
                break
            page_no += 1
