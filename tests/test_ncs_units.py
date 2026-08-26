import tempfile
import unittest
from pathlib import Path

from main.main_ncs_units import parse_ncs_response
from matching import ncs_matcher


SAMPLE_PAYLOAD = {
    "root": {
        "info": {"pageNo": 1, "totalCount": 1, "numOfRows": 10},
        "items": [{
            "ncsClCd": "2001020206_23v6",
            "ncsCompeUnitCd": "2001020206",
            "compeUnitName": "서버프로그램 구현",
            "compeUnitLevel": "5",
            "ncsLclasCdnm": "정보통신",
            "ncsMclasCdnm": "정보기술",
            "ncsSclasCdnm": "정보기술개발",
            "ncsSubdCdnm": "응용SW엔지니어링",
            "compeUnitDef": "Java와 데이터베이스를 활용하여 서버 프로그램을 구현하는 능력이다.",
        }],
    }
}


class NcsUnitTests(unittest.TestCase):
    def test_parses_live_response_shape(self):
        result = parse_ncs_response(SAMPLE_PAYLOAD)
        unit = result["units"][0]
        self.assertEqual(result["totalCount"], 1)
        self.assertEqual(unit["classificationCode"], "20010202")
        self.assertEqual(unit["unitName"], "서버프로그램 구현")
        self.assertEqual(unit["level"], "5")

    def test_prefers_synced_units_for_matching_codes(self):
        payload = '{"units": [{"classificationCode":"20010202","subName":"응용SW엔지니어링","unitCode":"2001020206","unitName":"서버프로그램 구현","matchText":"Java 서버 데이터베이스"}]}'
        with tempfile.TemporaryDirectory() as directory:
            original = ncs_matcher.NCS_UNIT_PATH
            try:
                ncs_matcher.NCS_UNIT_PATH = Path(directory) / "ncs_units.json"
                ncs_matcher.NCS_UNIT_PATH.write_text(payload, encoding="utf-8")
                units = ncs_matcher.get_ncs_units("IT/개발", ["20010202"], ["응용SW엔지니어링"])
            finally:
                ncs_matcher.NCS_UNIT_PATH = original
        self.assertEqual(units[0]["unitName"], "서버프로그램 구현")

    def test_uses_api_classification_for_non_it_categories(self):
        original_loader = ncs_matcher.load_ncs_units
        try:
            ncs_matcher.load_ncs_units = lambda: [{
                "classificationCode": "02010101",
                "majorName": "경영·회계·사무",
                "middleName": "기획사무",
                "minorName": "경영기획",
                "subName": "경영기획",
                "unitCode": "0201010101",
                "unitName": "사업환경 분석",
                "matchText": "경영기획 사업환경 분석 시장 자료 조사",
            }]
            result = ncs_matcher.calculate_ncs_score(
                "시장 자료 조사 경험",
                "사업환경 분석 담당",
                category="사무·총무",
                ncs_names=["경영기획"],
            )
        finally:
            ncs_matcher.load_ncs_units = original_loader
        self.assertTrue(result["ncs_used"])
        self.assertEqual(result["matched_unit_name"], "사업환경 분석")



if __name__ == "__main__":
    unittest.main()
