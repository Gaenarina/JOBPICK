import json
import re
import shutil
from pathlib import Path

import xlrd


ROOT_DIR = Path(__file__).resolve().parents[1]

EXCEL_PATH = ROOT_DIR / "data" / "ncs_excels" / "IT_개발" / "응용SW엔지니어링.xls"
CATEGORY_DICTIONARY_OUT_PATH = ROOT_DIR / "data" / "ncs_dictionary_by_category.json"
FLAT_DICTIONARY_OUT_PATH = ROOT_DIR / "data" / "ncs_dictionary.json"

CATEGORY_NAME = "IT/개발"
DUTY_CD = "20010202"
DUTY_NAME = "응용SW엔지니어링"
DUTY_DEF = "응용소프트웨어 개발에 필요한 요구사항 분석, 설계, 구현, 테스트, 배포 관련 직무역량"

ELEMENT_CODE_PATTERN = re.compile(r"(\d{10,}_\d{2}v\d+\.\d+)")
NOISE_HEADINGS = (
    "□ 적용범위",
    "□ 평가지침",
    "□ 관련기초능력",
    "□ 개발·개선 이력",
)


def clean_text(value):
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\u3000", " ")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)

    return text.strip()


def strip_noise_text(text):
    text = clean_text(text)

    for heading in NOISE_HEADINGS:
        index = text.find(heading)

        if index >= 0:
            text = text[:index]

    return clean_text(text)


def append_unique(target, values):
    for value in values:
        value = strip_noise_text(value)
        value = re.sub(r"^[\-·•\s]+", "", value)
        value = clean_text(value)

        if not value:
            continue

        if value not in target:
            target.append(value)


def parse_bullets(text):
    text = strip_noise_text(text)

    if not text:
        return []

    text = re.sub(r"^【\s*(지식|기술|태도)\s*】", "", text).strip()

    if "•" in text:
        parts = text.split("•")
    else:
        parts = text.split("\n")

    result = []

    for part in parts:
        item = clean_text(part)
        item = re.sub(r"^[\-·•\s]+", "", item)

        if item and item not in result:
            result.append(item)

    return result


def parse_criteria(text):
    text = strip_noise_text(text)

    if not text:
        return []

    text = re.split(r"【\s*(지식|기술|태도)\s*】", text)[0].strip()

    matches = re.findall(
        r"(?:^|\n)\s*\d+\.\d+\s*(.*?)(?=\n\s*\d+\.\d+|\Z)",
        text,
        flags=re.DOTALL,
    )

    result = []

    for match in matches:
        item = clean_text(match)

        if item and item not in result:
            result.append(item)

    return result


def split_element_code_and_name(value):
    text = clean_text(value)
    match = ELEMENT_CODE_PATTERN.search(text)

    if not match:
        return "", ""

    element_cd = match.group(1)
    element_name = text[match.end():]
    element_name = re.sub(r"^[\s\n:：.-]+", "", element_name)
    element_name = strip_noise_text(element_name)

    return element_cd, element_name


def create_element(element_cd, element_name):
    return {
        "elementCd": element_cd,
        "elementName": element_name,
        "criteria": [],
        "knowledge": [],
        "skills": [],
        "attitudes": [],
        "matchText": "",
    }


def add_content_to_element(element, text):
    text = strip_noise_text(text)

    if not text:
        return

    section_matches = list(re.finditer(r"【\s*(지식|기술|태도)\s*】", text))

    if not section_matches:
        append_unique(element["criteria"], parse_criteria(text))
        return

    before_first_section = text[: section_matches[0].start()]
    append_unique(element["criteria"], parse_criteria(before_first_section))

    for index, match in enumerate(section_matches):
        section_name = match.group(1)
        start = match.end()
        end = section_matches[index + 1].start() if index + 1 < len(section_matches) else len(text)
        body = text[start:end]

        if section_name == "지식":
            append_unique(element["knowledge"], parse_bullets(body))
        elif section_name == "기술":
            append_unique(element["skills"], parse_bullets(body))
        elif section_name == "태도":
            append_unique(element["attitudes"], parse_bullets(body))


def rebuild_match_text_for_element(element):
    parts = [
        element.get("elementCd", ""),
        element.get("elementName", ""),
    ]

    parts.extend(element.get("criteria", []))
    parts.extend(element.get("knowledge", []))
    parts.extend(element.get("skills", []))
    parts.extend(element.get("attitudes", []))

    element["matchText"] = clean_text(" ".join(parts))


def rebuild_match_text_for_unit(unit):
    parts = [
        unit.get("unitCd", ""),
        unit.get("unitName", ""),
        unit.get("unitDef", ""),
    ]

    for element in unit.get("elements", []):
        element["criteria"] = [
            item for item in element.get("criteria", [])
            if item != element.get("elementName", "")
        ]

        rebuild_match_text_for_element(element)
        parts.append(element.get("matchText", ""))

    unit["matchText"] = clean_text(" ".join(parts))


def is_noise_sheet(rows):
    first_text = ""

    for row in rows:
        for value in row:
            if value:
                first_text = value
                break

        if first_text:
            break

    return any(first_text.startswith(heading) for heading in NOISE_HEADINGS)


def read_sheet_rows(sheet):
    rows = []

    for row_index in range(sheet.nrows):
        row_values = []

        for col_index in range(sheet.ncols):
            value = clean_text(sheet.cell_value(row_index, col_index))
            row_values.append(value)

        if any(row_values):
            rows.append(row_values)

    return rows


def parse_excel_units():
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"엑셀 파일이 없습니다: {EXCEL_PATH}")

    workbook = xlrd.open_workbook(str(EXCEL_PATH))

    units = []
    current_unit = None
    current_element = None

    def commit_current_unit():
        nonlocal current_unit, current_element

        if current_unit is None:
            return

        rebuild_match_text_for_unit(current_unit)
        units.append(current_unit)

        current_unit = None
        current_element = None

    for sheet in workbook.sheets():
        rows = read_sheet_rows(sheet)

        if not rows:
            continue

        if is_noise_sheet(rows):
            continue

        for row in rows:
            row = row + ["", "", ""]
            first = row[0]
            second = row[1]
            third = row[2]

            if first.startswith("분류번호"):
                commit_current_unit()

                current_unit = {
                    "unitCd": second,
                    "unitName": "",
                    "unitDef": "",
                    "level": None,
                    "elements": [],
                    "matchText": "",
                }

                current_element = None
                continue

            if current_unit is None:
                continue

            if first.startswith("능력단위 명칭"):
                current_unit["unitName"] = second
                continue

            if first.startswith("능력단위 정의"):
                current_unit["unitDef"] = second
                continue

            if "능 력 단 위 요 소" in first or "수 행 준 거" in third:
                continue

            element_cd, element_name = split_element_code_and_name(first)

            if element_cd:
                existing_element = None

                for element in current_unit["elements"]:
                    if element["elementCd"] == element_cd:
                        existing_element = element
                        break

                if existing_element is None:
                    existing_element = create_element(element_cd, element_name)
                    current_unit["elements"].append(existing_element)

                current_element = existing_element

                add_content_to_element(current_element, second)
                add_content_to_element(current_element, third)
                continue

            if current_element is not None:
                for value in row:
                    add_content_to_element(current_element, value)

    commit_current_unit()

    return units


def build_dictionary(units):
    duty = {
        "dutyCd": DUTY_CD,
        "dutyName": DUTY_NAME,
        "dutyDef": DUTY_DEF,
        "sourceFile": str(EXCEL_PATH.relative_to(ROOT_DIR)),
        "units": units,
        "matchText": clean_text(" ".join(unit.get("matchText", "") for unit in units)),
    }

    category_dictionary = {
        CATEGORY_NAME: {
            "category": CATEGORY_NAME,
            "source": "NCS Excel",
            "duties": {
                DUTY_CD: duty,
            },
        }
    }

    flat_dictionary = {
        DUTY_CD: duty,
    }

    return category_dictionary, flat_dictionary


def backup_file(path):
    if not path.exists():
        return

    backup_path = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup_path)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def count_noise(data):
    text = json.dumps(data, ensure_ascii=False)

    return sum(text.count(heading) for heading in NOISE_HEADINGS)


def main():
    units = parse_excel_units()
    category_dictionary, flat_dictionary = build_dictionary(units)

    backup_file(CATEGORY_DICTIONARY_OUT_PATH)
    backup_file(FLAT_DICTIONARY_OUT_PATH)

    save_json(CATEGORY_DICTIONARY_OUT_PATH, category_dictionary)
    save_json(FLAT_DICTIONARY_OUT_PATH, flat_dictionary)

    total_elements = sum(len(unit.get("elements", [])) for unit in units)
    noise_count = count_noise(category_dictionary)

    print(f"능력단위 수: {len(units)}")
    print(f"능력단위요소 수: {total_elements}")
    print(f"불필요한 문서 섹션 포함 수: {noise_count}")
    print(f"분야별 NCS 사전 생성 완료: {CATEGORY_DICTIONARY_OUT_PATH}")
    print(f"전체 NCS 사전 생성 완료: {FLAT_DICTIONARY_OUT_PATH}")
    print()

    for unit in units:
        print(f"- {unit['unitCd']} / {unit['unitName']} / 요소 {len(unit.get('elements', []))}개")


if __name__ == "__main__":
    main()