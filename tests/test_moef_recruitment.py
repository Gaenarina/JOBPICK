import unittest

from sources.moef_recruitment import get_total_count, map_moef_category, normalize_recruitment
from main.main_moef_jobposting import sync_moef_job_postings


class FakeSnapshot:
    def __init__(self, exists=False):
        self.exists = exists


class FakeDocument:
    def __init__(self, store, document_id):
        self.store = store
        self.document_id = document_id

    def get(self):
        return FakeSnapshot(self.document_id in self.store)

    def set(self, value, merge=False):
        current = self.store.get(self.document_id, {}) if merge else {}
        self.store[self.document_id] = {**current, **value}


class FakeCollection:
    def __init__(self, store):
        self.store = store

    def document(self, document_id):
        return FakeDocument(self.store, document_id)


class FakeDb:
    def __init__(self):
        self.store = {}

    def collection(self, name):
        assert name == "job_postings"
        return FakeCollection(self.store)


class FakeClient:
    def __init__(self, items):
        self.items = items

    def iter_recruitments(self, **kwargs):
        return iter(self.items)


class MoefRecruitmentNormalizerTests(unittest.TestCase):
    def setUp(self):
        self.item = {
            "recrutPblntSn": 12345,
            "instNm": "한국테스트공사",
            "recrutPbancTtl": "정보시스템 개발자 채용",
            "ncsCdLst": "R600020,R600021",
            "ncsCdNmLst": "정보통신|정보기술",
            "workRgnNmLst": "서울,대전",
            "acbgCondNmLst": "학력무관",
            "hireTypeNmLst": "정규직",
            "recrutSeNm": "신입",
            "aplyQlfcCn": "Python 활용 가능자\n관련 전공자",
            "prefCondCn": "정보처리기사 우대",
            "recrutNope": 2,
            "pbancBgngYmd": "2026-08-01",
            "pbancEndYmd": "2026-08-31",
            "ongoingYn": "Y",
            "srcUrl": "https://job.alio.go.kr/example",
            "steps": [{"stepNm": "서류전형"}, {"stepNm": "면접전형"}],
        }

    def test_normalizes_to_existing_job_posting_schema(self):
        result = normalize_recruitment(self.item)
        posting = result["jobPosting"]

        self.assertEqual(result["documentId"], "moef_12345")
        self.assertEqual(posting["companyName"], "한국테스트공사")
        self.assertEqual(posting["workConditions"]["location"], "서울, 대전")
        self.assertEqual(posting["requirements"]["education"]["minimum"], "학력무관")
        self.assertIn("Python 활용 가능자", posting["requirements"]["requiredQualifications"])
        self.assertIn("정보통신", posting["embeddingText"]["fullForEmbedding"])
        self.assertEqual(posting["category"], "IT/개발")
        self.assertEqual(posting["sourceCategory"], "정보통신, 정보기술")
        self.assertTrue(posting["recruitment"]["isActive"])

    def test_requires_stable_external_id(self):
        self.item.pop("recrutPblntSn")
        with self.assertRaises(ValueError):
            normalize_recruitment(self.item)

    def test_reads_flat_total_count(self):
        self.assertEqual(get_total_count({"totalCount": "17", "result": []}), 17)

    def test_maps_common_ncs_categories_and_other(self):
        self.assertEqual(map_moef_category("경영·회계·사무"), "사무·총무")
        self.assertEqual(map_moef_category("보건·의료"), "의료/바이오")
        self.assertEqual(map_moef_category("농림어업"), "기타")

    def test_sync_upserts_by_stable_document_id(self):
        db = FakeDb()
        client = FakeClient([self.item])

        first = sync_moef_job_postings(db, client)
        second = sync_moef_job_postings(db, client)

        self.assertEqual(first["created"], 1)
        self.assertEqual(second["updated"], 1)
        self.assertEqual(list(db.store), ["moef_12345"])
        self.assertEqual(db.store["moef_12345"]["meta"]["source"], "moef_job_alio")


if __name__ == "__main__":
    unittest.main()
