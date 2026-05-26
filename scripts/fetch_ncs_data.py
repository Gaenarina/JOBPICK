'''
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

import requests
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]

ENV_LOCAL_PATH = ROOT_DIR / ".env.local"
ENV_PATH = ROOT_DIR / ".env"

if ENV_LOCAL_PATH.exists():
    load_dotenv(dotenv_path=ENV_LOCAL_PATH, override=True)
elif ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH, override=True)
else:
    load_dotenv()

STANDARD_BASE_URL = "http://www.ncs.go.kr/api"

CLASSIFICATION_OUT_PATH = ROOT_DIR / "data" / "ncs_classification.json"
CATEGORY_CODES_OUT_PATH = ROOT_DIR / "data" / "ncs_category_duty_codes.json"
CATEGORY_DICTIONARY_OUT_PATH = ROOT_DIR / "data" / "ncs_dictionary_by_category.json"
FLAT_DICTIONARY_OUT_PATH = ROOT_DIR / "data" / "ncs_dictionary.json"
DEBUG_DIR = ROOT_DIR / "data" / "debug"


JOB_CATEGORY_TO_NCS_KEYWORDS = {
    "IT/개발": [
        "정보기술", "정보기술개발", "소프트웨어", "SW", "응용SW",
        "시스템", "프로그래밍", "데이터", "인공지능", "정보보호", "보안",
        "네트워크", "DB", "데이터베이스"
    ],
    "디자인": [
        "디자인", "시각디자인", "제품디자인", "디지털디자인",
        "문화콘텐츠", "콘텐츠", "멀티미디어", "영상", "그래픽"
    ],
    "마케팅": [
        "마케팅", "광고", "홍보", "시장조사", "브랜드", "상품기획",
        "전자상거래", "온라인", "유통관리"
    ],
    "영업·고객상담": [
        "영업", "판매", "고객관리", "고객상담", "상담", "CS",
        "매장판매", "영업관리", "유통", "서비스"
    ],
    "사무·총무": [
        "사무", "총무", "인사", "회계", "경영", "기획", "재무",
        "문서관리", "비서", "세무", "행정"
    ],
    "교육": [
        "교육", "훈련", "교수", "학습", "강의", "직업교육",
        "평생교육", "교육운영"
    ],
    "의료/바이오": [
        "의료", "보건", "바이오", "임상", "간호", "의약", "제약",
        "생명과학", "보건의료"
    ],
    "운전/운송/배송": [
        "운전", "운송", "배송", "물류", "택배", "화물", "운수",
        "창고", "보관", "하역"
    ],
    "건축/시설": [
        "건축", "시설", "설비", "전기", "전자", "기계", "유지보수",
        "시공", "안전관리", "자동제어", "시설관리"
    ],
}


REQUIRED_DUTY_CODES_BY_CATEGORY = {
    "IT/개발": [
        "20010201",
        "20010202",
        "20010703",
    ],
}


def normalize_key(value):
    if value is None:
        return ""

    text = str(value).strip()
    text = text.strip('"').strip("'")
    text = unquote(text)

    return text.strip()


STANDARD_KEY = normalize_key(os.getenv("NCS_STANDARD_SERVICE_KEY"))


try:
    MAX_DUTY_CODES_PER_CATEGORY = int(
        os.getenv("NCS_MAX_DUTY_CODES_PER_CATEGORY", "2")
    )
except ValueError:
    MAX_DUTY_CODES_PER_CATEGORY = 2


def clean_text(value):
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"^\d+\.", "", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def local_name(tag):
    if tag is None:
        return ""

    if "}" in tag:
        return tag.split("}", 1)[1]

    return tag


def find_all_by_name(node, name):
    if node is None:
        return []

    return [
        child
        for child in node.iter()
        if local_name(child.tag) == name
    ]


def find_first_by_name(node, name):
    items = find_all_by_name(node, name)

    if not items:
        return None

    return items[0]


def get_text(node, *names):
    if node is None:
        return ""

    if not names:
        return clean_text(node.text)

    target_names = set(names)

    for child in list(node):
        if local_name(child.tag) in target_names and child.text:
            return clean_text(child.text)

    return ""


def to_int(value, default=1):
    try:
        return int(str(value).replace(",", "").strip())
    except Exception:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def save_debug_response(name, text):
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    path = DEBUG_DIR / name

    with path.open("w", encoding="utf-8") as file:
        file.write(text)

    return path


def check_key():
    if not STANDARD_KEY:
        loaded_env_path = ENV_LOCAL_PATH if ENV_LOCAL_PATH.exists() else ENV_PATH

        raise RuntimeError(
            "NCS_STANDARD_SERVICE_KEY를 읽지 못했습니다."
            + f"\n확인 경로: {loaded_env_path}"
        )


def get_api_error_message(root):
    messages = find_all_by_name(root, "message")

    for message_node in reversed(messages):
        text = clean_text(message_node.text)

        if text:
            return text

    return ""


def request_standard_rows(api_no, params=None, debug_name=None):
    if params is None:
        params = {}

    rows = []
    page_no = 1
    total_page = 1

    while page_no <= total_page:
        query = {
            **params,
            "serviceKey": STANDARD_KEY,
            "returnType": "xml",
            "pageNo": page_no,
            "numOfRows": 100,
        }

        url = f"{STANDARD_BASE_URL}/openapi{api_no}.do"

        response = requests.get(url, params=query, timeout=20)
        response.raise_for_status()

        if page_no == 1 and debug_name:
            debug_path = save_debug_response(debug_name, response.text)
            print(f"openapi{api_no} 응답 저장: {debug_path}")
            print("응답 앞부분:")
            print(response.text[:700])

        root = ET.fromstring(response.content)

        api_error_message = get_api_error_message(root)

        if api_error_message and "정상" not in api_error_message:
            raise RuntimeError(
                f"국가직무능력표준 API 인증 또는 호출 실패: {api_error_message}"
            )

        data_info = find_first_by_name(root, "dataInfo")
        code = get_text(data_info, "code")
        message = get_text(data_info, "message")

        if code and code != "000":
            raise RuntimeError(
                f"국가직무능력표준 API 호출 실패: openapi{api_no}, {code}, {message}"
            )

        page_rows = find_all_by_name(root, "row")
        rows.extend(page_rows)

        total_page = to_int(get_text(data_info, "totalPage"), 1)

        print(
            f"openapi{api_no} 수집 중: "
            f"{page_no}/{total_page} page / 누적 {len(rows)}개"
        )

        page_no += 1
        time.sleep(0.1)

    return rows


def build_duty_code(row):
    duty_cd = get_text(row, "dutyCd")

    if duty_cd:
        return duty_cd

    large_code = get_text(row, "ncsLclasCd")
    middle_code = get_text(row, "ncsMclasCd")
    small_code = get_text(row, "ncsSclasCd")
    detail_code = get_text(row, "ncsSubdCd")

    return f"{large_code}{middle_code}{small_code}{detail_code}"


def fetch_classification():
    rows = request_standard_rows(
        api_no=1,
        debug_name="debug_openapi1_classification.xml",
    )

    classifications = []

    for row in rows:
        duty_cd = build_duty_code(row)

        if not duty_cd:
            continue

        item = {
            "dutyCd": duty_cd,
            "ncsDegree": get_text(row, "ncsDegr"),
            "largeCode": get_text(row, "ncsLclasCd"),
            "largeName": get_text(row, "ncsLclasCdNm"),
            "middleCode": get_text(row, "ncsMclasCd"),
            "middleName": get_text(row, "ncsMclasCdNm"),
            "smallCode": get_text(row, "ncsSclasCd"),
            "smallName": get_text(row, "ncsSclasCdNm"),
            "detailCode": get_text(row, "ncsSubdCd"),
            "detailName": get_text(row, "ncsSubdCdNm"),
        }

        classifications.append(item)

    return classifications


def get_classification_search_text(item):
    return clean_text(" ".join([
        item.get("largeName", ""),
        item.get("middleName", ""),
        item.get("smallName", ""),
        item.get("detailName", ""),
    ]))


def append_unique(target, value):
    if value and value not in target:
        target.append(value)


def select_duty_codes_by_category(classifications):
    result = {}

    for category, keywords in JOB_CATEGORY_TO_NCS_KEYWORDS.items():
        fixed_codes = REQUIRED_DUTY_CODES_BY_CATEGORY.get(category, [])
        selected_codes = []

        for duty_cd in fixed_codes:
            append_unique(selected_codes, duty_cd)

        for item in classifications:
            duty_cd = item.get("dutyCd", "")
            search_text = get_classification_search_text(item)

            if not duty_cd or not search_text:
                continue

            matched = any(
                keyword and keyword in search_text
                for keyword in keywords
            )

            if matched:
                append_unique(selected_codes, duty_cd)

            if (
                MAX_DUTY_CODES_PER_CATEGORY > 0
                and len(selected_codes) >= max(
                    len(fixed_codes),
                    MAX_DUTY_CODES_PER_CATEGORY
                )
            ):
                break

        result[category] = selected_codes

    return result


def fetch_job_info(duty_cd):
    rows = request_standard_rows(
        api_no=2,
        params={"dutyCd": duty_cd},
        debug_name=f"debug_openapi2_job_{duty_cd}.xml",
    )

    if not rows:
        return {
            "dutyCd": duty_cd,
            "dutyName": "",
            "dutyDef": "",
        }

    row = rows[0]

    return {
        "dutyCd": get_text(row, "dutyCd") or duty_cd,
        "dutyName": get_text(row, "dutyNm"),
        "dutySvcNo": get_text(row, "dutySvcNo"),
        "dutyDef": get_text(row, "dutyDef"),
    }


def fetch_units(duty_cd):
    rows = request_standard_rows(
        api_no=3,
        params={"dutyCd": duty_cd},
        debug_name=f"debug_openapi3_units_{duty_cd}.xml",
    )

    units = []

    for row in rows:
        comp_unit_cd = get_text(row, "compUnitCd", "compeUnitCd")

        if not comp_unit_cd:
            continue

        units.append({
            "ncsClCd": get_text(row, "ncsClCd"),
            "compUnitCd": comp_unit_cd,
            "unitName": get_text(row, "compUnitName", "compeUnitName"),
            "unitDef": get_text(row, "compUnitDef", "compeUnitDef"),
            "level": get_text(row, "compUnitLevel", "compeUnitLevel"),
        })

    return units


def fetch_ksa(duty_cd, comp_unit_cd):
    rows = request_standard_rows(
        api_no=5,
        params={
            "dutyCd": duty_cd,
            "compUnitCd": comp_unit_cd,
        },
        debug_name=f"debug_openapi5_ksa_{duty_cd}_{comp_unit_cd}.xml",
    )

    result = {
        "elements": [],
        "criteria": [],
        "knowledge": [],
        "skills": [],
        "attitudes": [],
    }

    element_seen = set()

    for row in rows:
        element_name = get_text(row, "compUnitFactrName", "compeUnitFactrName")

        if element_name and element_name not in element_seen:
            element_seen.add(element_name)
            result["elements"].append(element_name)

        gbn_name = get_text(row, "gbnName")
        gbn_val = get_text(row, "gbnVal")

        if not gbn_val:
            continue

        if "수행" in gbn_name:
            result["criteria"].append(gbn_val)
        elif "지식" in gbn_name:
            result["knowledge"].append(gbn_val)
        elif "기술" in gbn_name:
            result["skills"].append(gbn_val)
        elif "태도" in gbn_name:
            result["attitudes"].append(gbn_val)

    return result


def build_unit_match_text(job_info, unit):
    return clean_text(" ".join([
        job_info.get("dutyName", ""),
        job_info.get("dutyDef", ""),
        unit.get("unitName", ""),
        unit.get("unitDef", ""),
        " ".join(unit.get("elements", [])),
        " ".join(unit.get("criteria", [])),
        " ".join(unit.get("knowledge", [])),
        " ".join(unit.get("skills", [])),
    ]))


def build_duty_match_text(job_info, units):
    return clean_text(" ".join([
        job_info.get("dutyName", ""),
        job_info.get("dutyDef", ""),
        " ".join(unit.get("matchText", "") for unit in units),
    ]))


def fetch_duty_detail(duty_cd, classification_by_code):
    classification = classification_by_code.get(duty_cd, {})

    job_info = fetch_job_info(duty_cd)
    units = fetch_units(duty_cd)
    enriched_units = []

    for unit in units:
        comp_unit_cd = unit.get("compUnitCd")

        if not comp_unit_cd:
            continue

        print(f"- 능력단위 상세 수집: {duty_cd}-{comp_unit_cd} {unit.get('unitName')}")

        ksa = fetch_ksa(duty_cd, comp_unit_cd)
        unit.update(ksa)
        unit["matchText"] = build_unit_match_text(job_info, unit)

        enriched_units.append(unit)

    return {
        **job_info,
        "classification": classification,
        "units": enriched_units,
        "matchText": build_duty_match_text(job_info, enriched_units),
    }


def build_dictionary_by_category(category_codes, classifications):
    classification_by_code = {
        item["dutyCd"]: item
        for item in classifications
        if item.get("dutyCd")
    }

    category_dictionary = {}
    flat_dictionary = {}
    duty_cache = {}

    for category, duty_codes in category_codes.items():
        print(f"\n[{category}] 상세 수집 시작")
        print(f"대상 직무코드: {duty_codes}")

        category_dictionary[category] = {
            "category": category,
            "keywords": JOB_CATEGORY_TO_NCS_KEYWORDS.get(category, []),
            "dutyCodes": duty_codes,
            "duties": {},
        }

        for duty_cd in duty_codes:
            if duty_cd in duty_cache:
                detail = duty_cache[duty_cd]
            else:
                try:
                    print(f"[{category}] NCS 직무 상세 수집: {duty_cd}")
                    detail = fetch_duty_detail(duty_cd, classification_by_code)
                    duty_cache[duty_cd] = detail
                    flat_dictionary[duty_cd] = detail
                except Exception as error:
                    print(f"[{category}] {duty_cd} 수집 실패: {error}")
                    detail = {
                        "dutyCd": duty_cd,
                        "error": str(error),
                        "classification": classification_by_code.get(duty_cd, {}),
                        "units": [],
                        "matchText": "",
                    }
                    duty_cache[duty_cd] = detail
                    flat_dictionary[duty_cd] = detail

            category_dictionary[category]["duties"][duty_cd] = detail

        save_json(CATEGORY_DICTIONARY_OUT_PATH, category_dictionary)
        save_json(FLAT_DICTIONARY_OUT_PATH, flat_dictionary)

    return category_dictionary, flat_dictionary


def main():
    check_key()

    loaded_env_path = ENV_LOCAL_PATH if ENV_LOCAL_PATH.exists() else ENV_PATH

    print(f".env 경로: {loaded_env_path}")
    print(f"NCS_STANDARD_SERVICE_KEY 읽힘: {bool(STANDARD_KEY)} / 길이: {len(STANDARD_KEY)}")
    print(f"분야별 최대 직무코드 수: {MAX_DUTY_CODES_PER_CATEGORY}")

    print("\nNCS 분류체계 호출 시작")
    classifications = fetch_classification()

    save_json(CLASSIFICATION_OUT_PATH, classifications)

    print(f"NCS 분류체계 저장 완료: {CLASSIFICATION_OUT_PATH}")
    print(f"NCS 분류체계 수: {len(classifications)}")

    print("\nJOBPICK 분야 기준 NCS 직무코드 분류 시작")
    category_codes = select_duty_codes_by_category(classifications)

    save_json(CATEGORY_CODES_OUT_PATH, category_codes)

    print(f"분야별 직무코드 저장 완료: {CATEGORY_CODES_OUT_PATH}")

    for category, codes in category_codes.items():
        print(f"{category}: {codes}")

    print("\n분야별 NCS 상세 사전 생성 시작")
    category_dictionary, flat_dictionary = build_dictionary_by_category(
        category_codes,
        classifications,
    )

    if not category_dictionary:
        raise RuntimeError("분야별 NCS 사전이 비어 있습니다.")

    save_json(CATEGORY_DICTIONARY_OUT_PATH, category_dictionary)
    save_json(FLAT_DICTIONARY_OUT_PATH, flat_dictionary)

    print(f"\n분야별 NCS 사전 저장 완료: {CATEGORY_DICTIONARY_OUT_PATH}")
    print(f"전체 NCS 사전 저장 완료: {FLAT_DICTIONARY_OUT_PATH}")


if __name__ == "__main__":
    main()

    '''