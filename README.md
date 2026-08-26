# JOBPICK

## 채용공고 수집

기본 수집원은 공공데이터포털의 `재정경제부_공공기관 채용정보 조회서비스`입니다.
발급 화면의 일반 인증키를 `.env.local`에 설정합니다. Encoding/Decoding 키를 모두 처리합니다.

```dotenv
MOEF_RECRUITMENT_API_KEY=발급받은_디코딩_키
MOEF_SYNC_INTERVAL_MINUTES=60
```

앱에서 `/api/job-postings`를 처음 조회하면 재정경제부 API를 자동 호출하여 Firestore를
동기화하고, 동기화된 공공기관 공고만 화면과 이력서 매칭에 사용합니다. 기본 동기화
간격은 60분이며, API 장애가 발생하면 기존에 저장된 공고를 계속 표시합니다.

수동 동기화가 필요할 때는 PowerShell 환경변수로도 실행할 수 있습니다.

```powershell
$env:MOEF_RECRUITMENT_API_KEY = "발급받은 디코딩 키"
python main/main_jobposting.py
```

API 응답과 정규화 결과만 확인하고 Firestore에는 저장하지 않으려면 다음처럼 실행합니다.

```powershell
python main/main_jobposting.py --dry-run --max-pages 1
```

선택 환경변수:

- `FIREBASE_KEY_PATH`: Firebase 서비스 계정 파일 경로(기본 `config/firebase_key.json`)
- `MOEF_RECRUITMENT_API_URL`: 공공데이터포털의 API URL이 변경되었을 때 재정의
- `JOB_POSTING_SOURCE`: 기본값 `moef`
- `MOEF_SYNC_INTERVAL_MINUTES`: 앱의 자동 동기화 간격(기본 60분)
- `MOEF_SYNC_ROWS_PER_PAGE`: API 페이지당 요청 공고 수(기본 100)
- `MOEF_SYNC_MAX_PAGES`: 한 번의 동기화에서 가져올 최대 페이지 수(기본 10)
- `JOB_POSTING_ACTIVE_SOURCES`: 매칭 대상 수집원(기본 `moef_job_alio`)

잡코리아 크롤러 코드는 레거시 fallback으로 보존되어 있지만 기본 실행에서는 비활성화되어
있습니다. 실수로 실행되지 않도록 `JOB_POSTING_SOURCE=jobkorea`와
`ENABLE_LEGACY_JOBKOREA_CRAWLER=true`를 모두 명시한 경우에만 동작합니다.

## NCS 통합 능력단위 사전

승인된 `한국산업인력공단_NCS 관련 정보 서비스`의 전체 페이지를 자동 순회해
능력단위 코드·명칭·수준·정의가 포함된 통합 사전을 생성합니다.

```powershell
$env:NCS_INFO_API_KEY = "발급받은 인증키"
python main/main_ncs_units.py
```

결과는 `data/ncs_units.json` 하나로 저장됩니다. 매칭기는 이 통합 사전이
있으면 공고의 NCS 코드와 가장 가까운 능력단위만 사용하고, 파일이 없으면 기존
`ncs_dictionary_by_category.json`으로 자동 fallback합니다. NCS 데이터는 자주 변하지
않으므로 월 1회 정도 같은 명령으로 갱신하면 충분합니다.
