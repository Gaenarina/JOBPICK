"""Synchronize the approved HRDKorea NCS unit API into one local dictionary."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable
from urllib.parse import unquote, urlencode
from urllib.request import Request, urlopen

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_URL = "https://c.q-net.or.kr/openapi/Ncs1info/ncsinfo.do"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "ncs_units.json"


def parse_ncs_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("message"):
        raise RuntimeError(f"NCS API error: {payload['message']}")

    root = payload.get("root", payload) or {}
    info = root.get("info", {}) or {}
    raw_items = root.get("items", []) or []
    if isinstance(raw_items, dict):
        raw_items = raw_items.get("item", raw_items)
    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    units = []
    for item in raw_items if isinstance(raw_items, list) else []:
        if not isinstance(item, dict):
            continue
        versioned_code = str(item.get("ncsClCd", "") or "").strip()
        stable_code = str(item.get("ncsCompeUnitCd", "") or "").strip()
        if not stable_code:
            stable_code = versioned_code.split("_", 1)[0]
        if not stable_code:
            continue

        unit_name = str(item.get("compeUnitName", "") or "").strip()
        definition = str(item.get("compeUnitDef", "") or "").strip()
        hierarchy = {
            "majorName": str(item.get("ncsLclasCdnm", "") or "").strip(),
            "middleName": str(item.get("ncsMclasCdnm", "") or "").strip(),
            "minorName": str(item.get("ncsSclasCdnm", "") or "").strip(),
            "subName": str(item.get("ncsSubdCdnm", "") or "").strip(),
        }
        classification_code = re.sub(r"\D", "", stable_code)[:8]
        match_text = " ".join(filter(None, [*hierarchy.values(), unit_name, definition]))
        units.append({
            "unitCode": stable_code,
            "versionedCode": versioned_code,
            "classificationCode": classification_code,
            "unitName": unit_name,
            "level": item.get("compeUnitLevel", ""),
            **hierarchy,
            "definition": definition,
            "matchText": match_text,
            "ncsLastLinkedAt": item.get("ncsLastLinkDt", ""),
            "hrdnetLastLinkedAt": item.get("hrdnetLastLinkDt", ""),
        })

    return {
        "units": units,
        "pageNo": int(info.get("pageNo", 1) or 1),
        "numOfRows": int(info.get("numOfRows", len(units)) or len(units)),
        "totalCount": int(info.get("totalCount", len(units)) or len(units)),
    }


def fetch_page(api_key: str, page_no: int, rows: int, api_url: str = DEFAULT_URL) -> Dict[str, Any]:
    normalized_key = unquote(api_key) if re.search(r"%[0-9a-fA-F]{2}", api_key) else api_key
    query = urlencode({
        # The live service requires lowercase serviceKey although the portal
        # documentation currently displays ServiceKey.
        "serviceKey": normalized_key,
        "type": "json",
        "pageNo": page_no,
        "numOfRows": rows,
    })
    request = Request(f"{api_url}?{query}", headers={"Accept": "application/json", "User-Agent": "JOBPICK/1.0"})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8-sig"))
    return parse_ncs_response(payload)


def iter_all_units(api_key: str, rows: int = 100, api_url: str = DEFAULT_URL) -> Iterable[Dict[str, Any]]:
    page_no = 1
    received = 0
    while True:
        payload = fetch_page(api_key, page_no, rows, api_url)
        units = payload["units"]
        if not units:
            break
        yield from units
        received += len(units)
        if received >= payload["totalCount"] or len(units) < rows:
            break
        page_no += 1


def _version_rank(unit: Dict[str, Any]):
    versioned_code = str(unit.get("versionedCode", ""))
    match = re.search(r"_(\d+)v(\d+)", versioned_code, re.IGNORECASE)
    version = (int(match.group(1)), int(match.group(2))) if match else (0, 0)
    return (str(unit.get("ncsLastLinkedAt", "")), version)


def sync_ncs_units(api_key: str, output_path: Path = DEFAULT_OUTPUT, rows: int = 100, api_url: str = DEFAULT_URL):
    latest_by_code = {}
    received_count = 0
    for unit in iter_all_units(api_key, rows=rows, api_url=api_url):
        received_count += 1
        key = unit["unitCode"]
        previous = latest_by_code.get(key)
        if previous is None or _version_rank(unit) > _version_rank(previous):
            latest_by_code[key] = unit

    units = sorted(latest_by_code.values(), key=lambda unit: (unit["classificationCode"], unit["unitCode"]))
    payload = {
        "metadata": {
            "source": "한국산업인력공단_NCS 관련 정보 서비스",
            "sourceUrl": api_url,
            "syncedAt": datetime.now(timezone.utc).isoformat(),
            "receivedCount": received_count,
            "count": len(units),
        },
        "units": units,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_path.replace(output_path)
    return payload["metadata"]


def main():
    parser = argparse.ArgumentParser(description="Synchronize all approved NCS units")
    parser.add_argument("--rows", type=int, default=100)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    api_key = os.getenv("NCS_INFO_API_KEY", "").strip() or os.getenv("MOEF_RECRUITMENT_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("NCS_INFO_API_KEY is required")
    metadata = sync_ncs_units(
        api_key,
        output_path=args.output,
        rows=max(1, min(args.rows, 1000)),
        api_url=os.getenv("NCS_INFO_API_URL", DEFAULT_URL).strip(),
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

