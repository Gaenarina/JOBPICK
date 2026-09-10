# JOBPICK 실행 환경 버전 기준

기록일: 2026-08-26  
기준 작업 폴더: `C:\Users\82109\JOBPICK`

이 문서는 다른 컴퓨터에서 JOBPICK의 추천 결과가 달라질 때 실행 환경을 비교하기 위한 기준표다. API 키와 개인 키의 실제 값은 기록하지 않는다.

## 권장 실행 방법

AI 서버는 반드시 프로젝트 가상환경의 Python을 직접 지정해서 실행한다.

```powershell
cd C:\Users\82109\JOBPICK
.\venv\Scripts\python.exe server.py
```

프론트엔드는 별도 터미널에서 실행한다.

```powershell
cd C:\Users\82109\JOBPICK
npm run dev
```

`python server.py`만 사용하면 전역 Python이 선택될 수 있다. 현재 전역 Python에는 `sentence-transformers`, `torch`, `transformers`, `google-cloud-vision`, `firebase-admin`이 설치되어 있지 않으므로 기준 실행 방법으로 사용하지 않는다.

## 시스템 및 소스 코드

| 항목 | 현재 기준값 |
|---|---|
| 운영체제 | Windows 11 (`10.0.26200`) |
| Git commit | `1b7a2f334db1752c7a1e3e2afe987ecc8be2467c` |
| Node.js | `v20.17.0` |
| npm | `10.8.2` |
| Python | `3.13.13` |
| 기준 Python 실행 파일 | `C:\Users\82109\JOBPICK\venv\Scripts\python.exe` |
| pip | `26.1` |

## Python 패키지

아래 버전은 프로젝트 `venv` 기준이다.

| 패키지 | 버전 |
|---|---:|
| sentence-transformers | 5.4.1 |
| transformers | 5.7.0 |
| torch | 2.11.0 |
| numpy | 2.4.4 |
| google-cloud-vision | 3.13.0 |
| firebase-admin | 7.4.0 |
| google-auth | 2.49.2 |
| Flask | 3.1.3 |

임베딩 모델 이름은 코드에 `jhgan/ko-sroberta-multitask`로 지정되어 있다.

## Node 패키지

아래는 현재 `node_modules`에 실제 설치된 버전이다.

| 패키지 | 버전 |
|---|---:|
| next | 14.2.0 |
| react | 18.3.1 |
| react-dom | 18.3.1 |
| firebase | 12.13.0 |
| firebase-admin | 13.7.0 |
| lucide-react | 1.21.0 |
| tailwindcss | 3.4.19 |
| postcss | 8.5.8 |
| autoprefixer | 10.4.27 |
| typescript | 6.0.2 |
| @types/node | 25.5.0 |
| @types/react | 19.2.14 |

## 데이터 및 인증 파일 해시

키 파일의 내용은 공유하지 말고 SHA-256 해시만 비교한다.

| 파일 | SHA-256 |
|---|---|
| `data/embeddings/text_vectors.json` | `F35DD6276F1FD690B09D7FDB74FC7A301CFD7CCB05E05BBF3FD905D3B036E1AD` |
| `data/embeddings/text_vectors.npy` | `25A6684FF129738040860D5D837EB641A4458C572A56D67A698346365AAB474C` |
| `config/firebase_key.json` | `42C946D8BDCAF9530602DE161EE1415E622EB28FE3884190DDF4AB6893278562` |
| `config/vision_key.json` | `6A5620E7D12FD973B0F6B82091301FFCA249F4BB32807A21B9AA80288C20F8B7` |

인증 파일의 해시도 민감한 환경 식별 정보가 될 수 있으므로 팀 내부 비교에만 사용한다.

## `.env.local` 변수 이름

현재 설정된 변수 이름은 다음과 같다. 실제 값은 문서에 기록하지 않는다.

```text
AI_SERVER_URL
FIREBASE_CLIENT_EMAIL
FIREBASE_PRIVATE_KEY
FIREBASE_PROJECT_ID
FIREBASE_STORAGE_BUCKET
GEMINI_API_KEY
MOEF_RECRUITMENT_API_KEY
NCS_MAX_DUTY_CODES_PER_CATEGORY
NCS_STANDARD_SERVICE_KEY
NEXT_PUBLIC_FIREBASE_API_KEY
NEXT_PUBLIC_FIREBASE_APP_ID
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID
NEXT_PUBLIC_FIREBASE_PROJECT_ID
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET
```

현재 `.env.local`에는 `GEMINI_MODEL`, `MATCHING_AI_CANDIDATE_LIMIT`, `JOB_POSTING_ACTIVE_SOURCES`가 없으므로 코드의 기본값을 사용한다.

| 설정 | 기본값 |
|---|---|
| 임베딩 모델 | `jhgan/ko-sroberta-multitask` |
| 정밀 매칭 후보 수 | `80` |
| 활성 공고 출처 | `moef_job_alio` |
| Gemini 모델 | 코드에 정의된 fallback 순서로 선택 |

## 다른 컴퓨터에서 비교하는 명령

반드시 AI 서버를 실행할 터미널에서 실행한다.

### 한 번에 확인하기

아래 블록 전체를 PowerShell에 붙여 넣으면 주요 버전과 파일 해시를 한 번에 확인할 수 있다.

```powershell
Write-Output "[WORKSPACE]"
Get-Location

Write-Output "[GIT]"
git rev-parse HEAD
git status --short

Write-Output "[NODE]"
node --version
npm --version
npm ls --depth=0

Write-Output "[GLOBAL PYTHON]"
python --version
python -c "import sys; print(sys.executable)"
python -m pip --version

Write-Output "[PROJECT VENV]"
.\venv\Scripts\python.exe --version
.\venv\Scripts\python.exe -c "import sys; print(sys.executable)"
.\venv\Scripts\python.exe -m pip --version
.\venv\Scripts\python.exe -m pip show sentence-transformers transformers torch numpy google-cloud-vision firebase-admin google-auth flask

Write-Output "[TORCH DEVICE]"
.\venv\Scripts\python.exe -c "import torch; print('torch=' + torch.__version__); print('cuda_available=' + str(torch.cuda.is_available())); print('cuda_version=' + str(torch.version.cuda)); print('device=' + (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'))"

Write-Output "[FILE HASHES]"
Get-FileHash data\embeddings\text_vectors.json -Algorithm SHA256
Get-FileHash data\embeddings\text_vectors.npy -Algorithm SHA256
Get-FileHash config\firebase_key.json -Algorithm SHA256
Get-FileHash config\vision_key.json -Algorithm SHA256
```

결과를 파일로 저장하려면 위 명령 블록 전체를 괄호로 감싼 뒤 마지막에 다음을 연결한다.

```powershell
& {
    # 위의 "한 번에 확인하기" 명령을 여기에 넣는다.
} *>&1 | Tee-Object environment-check.txt
```

`environment-check.txt`에는 키 파일의 내용이 아니라 해시만 기록된다. 그래도 팀 내부에서만 공유하는 것을 권장한다.

### 항목별 확인하기

```powershell
Get-Location
git rev-parse HEAD
git status --short

node --version
npm --version
npm ls --depth=0

.\venv\Scripts\python.exe --version
.\venv\Scripts\python.exe -c "import sys; print(sys.executable)"
.\venv\Scripts\python.exe -m pip show sentence-transformers transformers torch numpy google-cloud-vision firebase-admin google-auth flask

Get-FileHash data\embeddings\text_vectors.json -Algorithm SHA256
Get-FileHash data\embeddings\text_vectors.npy -Algorithm SHA256
Get-FileHash config\firebase_key.json -Algorithm SHA256
Get-FileHash config\vision_key.json -Algorithm SHA256
```

설치된 모든 Python 패키지를 비교하려면 다음 명령을 사용한다.

```powershell
.\venv\Scripts\python.exe -m pip freeze | Sort-Object
```

목록을 비교용 파일로 저장하려면 다음과 같이 실행한다.

```powershell
.\venv\Scripts\python.exe -m pip freeze |
  Sort-Object |
  Out-File python-package-versions.txt -Encoding utf8

Get-FileHash python-package-versions.txt -Algorithm SHA256
```

실제로 8000번 포트에서 실행 중인 AI 서버 프로세스를 확인하려면 다음 명령을 사용한다.

```powershell
$aiServerConnection = Get-NetTCPConnection -LocalPort 8000 -State Listen
$aiServerConnection | Select-Object LocalAddress, LocalPort, OwningProcess
Get-CimInstance Win32_Process |
  Where-Object ProcessId -eq $aiServerConnection.OwningProcess |
  Select-Object ProcessId, ExecutablePath, CommandLine
```

## 추천 결과가 다를 때 추가 확인

버전과 해시가 모두 같다면 다음 값을 두 실행 결과에서 비교한다.

```text
rawText
preprocessedText
effectiveAnalysis
matchPreferences
filteredJobCount
candidateJobCount
추천 공고 jobId
fitScore
accessibilityScore
confidenceScore
```

- `rawText`가 다르면 Google Vision OCR 결과 차이다.
- `rawText`는 같고 `effectiveAnalysis`가 다르면 전처리 또는 구조화 환경 차이다.
- `effectiveAnalysis`까지 같고 점수가 다르면 임베딩 실행 환경 차이다.
- 점수까지 같고 추천 공고만 다르면 후보 조회 순서 또는 동점 정렬 문제다.
