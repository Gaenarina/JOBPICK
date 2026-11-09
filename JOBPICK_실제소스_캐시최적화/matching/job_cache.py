"""Firestore 공고의 사용자 비의존 전처리 결과를 프로세스 메모리에서 재사용한다.

- 공고 원본이 조금이라도 다르면 별개로 계산한다.
- 반환 시 deepcopy하여 이후 직종 scope/점수 계산에서 변경해도 공유 값이 바뀌지 않는다.
- Cloud Run 인스턴스가 다시 시작되면 캐시는 초기화된다.
- 이력서, 개인 정보, 점수, 최종 추천 결과는 저장하지 않는다.
"""

import hashlib
import json
from collections import OrderedDict
from copy import deepcopy

from matching.matchtest import flatten_job, get_job_embedding_text

JOB_CACHE_LIMIT = 512
_job_cache = OrderedDict()


def _fingerprint(job_raw):
    # Firestore에서 가져온 공고 dict의 현재 내용을 기준으로 식별한다.
    # 공고가 변경되면 이전 버전의 캐시를 사용하지 않는다.
    serialized = json.dumps(
        job_raw,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _evict_if_necessary():
    while len(_job_cache) > JOB_CACHE_LIMIT:
        _job_cache.popitem(last=False)


def get_cached_flattened_job(job_raw):
    """원래 flatten_job의 반환값과 캐시 사용 여부를 반환한다."""
    key = _fingerprint(job_raw)
    entry = _job_cache.get(key)
    if entry is not None:
        _job_cache.move_to_end(key)
        return deepcopy(entry["flat"]), True

    flat = flatten_job(job_raw)
    _job_cache[key] = {"flat": deepcopy(flat), "embedding_text": None}
    _evict_if_necessary()
    return flat, False


def get_cached_job_embedding_text(job_raw):
    """원래 get_job_embedding_text의 텍스트와 캐시 사용 여부를 반환한다."""
    key = _fingerprint(job_raw)
    entry = _job_cache.get(key)
    if entry is not None and entry["embedding_text"] is not None:
        _job_cache.move_to_end(key)
        return entry["embedding_text"], True

    result = get_job_embedding_text(job_raw)
    if entry is None:
        # 외부에서 이 함수만 사용해도 일관되게 동작하도록 함.
        _job_cache[key] = {"flat": deepcopy(flatten_job(job_raw)), "embedding_text": result}
    else:
        entry["embedding_text"] = result
        _job_cache.move_to_end(key)
    _evict_if_necessary()
    return result, False
