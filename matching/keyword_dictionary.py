import re


SKILL_ALIASES = {
    "python": ["python", "파이썬"],
    "javascript": ["javascript", "java script", "js", "자바스크립트"],
    "typescript": ["typescript", "type script", "ts", "타입스크립트"],
    "react": ["react", "react.js", "reactjs", "리액트"],
    "next.js": ["next.js", "nextjs", "next", "넥스트"],
    "node.js": ["node.js", "nodejs", "node"],
    "java": ["java", "자바"],
    "spring": ["spring", "spring boot", "스프링", "스프링부트"],
    "html": ["html"],
    "css": ["css"],
    "sql": ["sql", "mysql", "mariadb", "postgresql", "postgres", "oracle", "database", "db", "데이터베이스"],
    "firebase": ["firebase", "파이어베이스"],
    "aws": ["aws", "amazon web services"],
    "docker": ["docker", "도커"],
    "git": ["git", "github", "gitlab", "깃", "깃허브"],
    "linux": ["linux", "리눅스"],
    "unix": ["unix"],
    "windows_server": ["windows server", "windows 서버", "윈도우 서버"],
    "server": ["server", "서버", "서버 운영", "시스템 운영"],
    "network": ["network", "네트워크", "통신"],
    "cloud": ["cloud", "클라우드", "클라우드 솔루션"],
    "ai": ["ai", "인공지능", "artificial intelligence"],
    "machine_learning": ["machine learning", "머신러닝", "ml"],
    "deep_learning": ["deep learning", "딥러닝", "dl"],
    "data_analysis": ["data analysis", "데이터 분석", "데이터분석", "자료 분석"],
    "data_modeling": ["data modeling", "데이터 모델링", "모델링"],
    "tensorflow": ["tensorflow", "텐서플로우"],
    "pytorch": ["pytorch", "파이토치"],
    "llm": ["llm", "대규모 언어모델", "언어모델", "생성형 ai", "생성형"],
    "nlp": ["nlp", "자연어처리", "자연어 처리"],
    "chatbot": ["chatbot", "챗봇", "ai 챗봇"],
    "frontend": ["frontend", "front-end", "프론트엔드", "프론트 개발"],
    "backend": ["backend", "back-end", "백엔드", "서버 개발"],
    "web_development": ["web development", "웹 개발", "웹서비스", "웹 서비스"],
    "web_publishing": ["웹 퍼블리싱", "퍼블리싱", "웹 퍼블리셔"],
    "ui_ux": ["ui", "ux", "ui/ux", "사용자 경험", "사용자 중심"],
    "c": ["c", "c언어"],
    "hardware": ["hardware", "hw", "h/w", "하드웨어", "pc 하드웨어"],
    "software": ["software", "sw", "s/w", "소프트웨어"],
    "sensor": ["sensor", "센서"],
    "kiosk": ["kiosk", "키오스크"],
    "projector": ["projector", "빔프로젝터"],
    "maintenance": ["유지보수", "점검", "기술지원", "장애 조치"],
    "installation": ["설치", "장비 설치", "h/w 설치", "hw 설치"],
    "as_service": ["a/s", "a s", "as 담당", "설치as", "설치 a/s", "서비스 대응"],
    "electrical": ["전기", "전자", "전기전자", "전기/전자"],
    "telecommunication": ["통신", "통신 관련"],
    "excel": ["excel", "엑셀"],
    "powerpoint": ["powerpoint", "power point", "ppt", "파워포인트", "프레젠테이션", "프리젠테이션"],
    "microsoft_office": ["microsoft office", "office", "오피스", "오피스프로그램", "오피스 프로그램"],
    "oa": ["oa", "oa 활용"],
    "word_processor": ["word", "워드", "워드프로세서"],
    "spss": ["spss"],
    "tableau": ["tableau", "태블로"],
    "erp": ["erp", "erp 시스템"],
    "vba": ["vba", "엑셀 vba"],
    "photoshop": ["photoshop", "포토샵", "adobe 포토샵"],
    "illustrator": ["illustrator", "일러스트", "일러스트레이터"],
    "figma": ["figma", "피그마"],
    "blender": ["blender", "블렌더"],
    "adobe_xd": ["adobe xd", "xd"],
    "design_tool": ["adobe", "그래픽 툴", "디자인 툴"],
    "marketing": ["marketing", "마케팅", "마케팅 전략"],
    "branding": ["branding", "브랜딩"],
    "content": ["content", "콘텐츠", "컨텐츠", "카드뉴스", "배너"],
    "md": ["md", "온라인 md", "상품관리", "상품 관리"],
    "purchasing": ["구매", "구매 담당", "구매담당", "매입"],
    "sourcing": ["소싱", "제품 소싱", "원부자재", "원/부자재", "발주"],
    "estimate": ["견적", "견적서", "견적 관리", "단가 관리"],
    "sales": ["sales", "영업", "기술영업", "b2b 영업"],
    "customer_service": ["customer service", "고객상담", "고객 상담", "고객센터", "cs", "상담"],
    "admin": ["사무", "행정", "사무행정", "일반사무", "전산 보조", "행정사무"],
    "document_work": ["문서작성", "문서 작성", "보고서 작성", "자료 작성"],
    "accounting": ["회계", "전산회계", "세무"],
    "logistics": ["물류", "납품", "입출고", "출고", "배송"],
    "inventory": ["재고관리", "재고 관리", "입출고 관리"],
    "production": ["생산", "생산직", "생산관리", "생산 일정 관리"],
    "quality_control": ["품질관리", "품질 관리", "품질"],
    "facility_operation": ["설비운전", "설비 운전", "믹서 운전", "원료계량", "혼합"],
    "forklift": ["지게차", "지게차 운전", "지게차 운전기능사"],
    "driving": ["운전", "운전 가능", "운전가능", "차량소지", "차량 소지"],
    "teaching": ["강사", "강의", "수업", "교육", "코딩체험", "코딩 체험"],
    "english": ["english", "영어", "영어회화", "비즈니스영어", "비즈니스 영어"],
    "japanese": ["japanese", "일본어"],
    "chinese": ["chinese", "중국어"],
    "bakery": ["제과", "제빵", "제과제빵", "반죽", "제과제빵보조"],
    "retail_sales": ["판매", "매장", "매장관리", "고객응대", "가구판매"],
    "fashion": ["패션", "의류", "섬유", "원부자재"],
}


CERT_ALIASES = {
    "정보처리기사": ["정보처리기사", "정보처리 기사"],
    "정보처리기능사": ["정보처리기능사", "정보처리 기능사"],
    "sqld": ["sqld", "sql 개발자", "sql개발자"],
    "sqlp": ["sqlp", "sql 전문가", "sql전문가"],
    "adsp": ["adsp", "데이터분석 준전문가", "데이터 분석 준전문가"],
    "adp": ["adp", "데이터분석전문가", "데이터 분석 전문가"],
    "컴퓨터활용능력": ["컴퓨터활용능력", "컴퓨터 활용능력", "컴활", "컴퓨터활용능력 1급", "컴퓨터활용능력 자격증"],
    "gtq": ["gtq", "gtq 포토샵", "그래픽기술자격"],
    "전산회계": ["전산회계", "전산회계 1급"],
    "워드프로세서": ["워드프로세서", "워드 프로세서"],
    "지게차운전기능사": ["지게차 운전기능사", "지게차운전기능사"],
    "유통관리사": ["유통관리사", "유통관리사 1급"],
    "가맹거래사": ["가맹거래사"],
    "운전면허": ["운전면허", "운전 면허", "1종", "2종", "1종보통", "2종보통", "2종보통운전면허", "운전면허 1종", "운전면허 2종"],
    "toeic": ["toeic", "토익"],
    "toefl": ["toefl", "토플"],
    "opic": ["opic", "오픽"],
    "jlpt": ["jlpt", "jlpt n1", "jlpt n2"],
    "hsk": ["hsk", "hsk5"],
}


JOB_CATEGORY_KEYWORDS = {
    "AI/데이터": [
        "ai",
        "인공지능",
        "머신러닝",
        "딥러닝",
        "데이터 분석",
        "데이터분석",
        "데이터사이언스",
        "데이터 사이언스",
        "모델 개발",
        "모델링",
        "생성형 ai",
        "llm",
        "nlp",
        "챗봇",
        "pytorch",
        "tensorflow",
        "sql",
    ],
    "웹개발/프론트엔드": [
        "프론트엔드",
        "웹 개발",
        "웹서비스",
        "웹 서비스",
        "웹 퍼블리싱",
        "웹 퍼블리셔",
        "ui 구현",
        "ui/ux",
        "html",
        "css",
        "javascript",
        "react",
        "next.js",
    ],
    "백엔드/서버개발": [
        "백엔드",
        "서버 개발",
        "api",
        "spring",
        "node.js",
        "django",
        "flask",
        "database",
        "db",
    ],
    "서버/인프라": [
        "linux",
        "unix",
        "windows 서버",
        "서버 운영",
        "시스템 운영",
        "시스템 관리",
        "장애 조치",
        "서버 취약점",
        "네트워크",
        "클라우드",
    ],
    "하드웨어/설치AS": [
        "설치",
        "설치as",
        "a/s",
        "하드웨어",
        "hw",
        "센서",
        "키오스크",
        "빔프로젝터",
        "장비",
        "점검",
        "유지보수",
        "전기",
        "전자",
        "통신",
        "운전면허",
        "이동근무",
    ],
    "디자인": [
        "디자인",
        "웹디자이너",
        "컨텐츠 디자이너",
        "콘텐츠 디자이너",
        "ui 디자인",
        "ux 디자인",
        "제품 디자인",
        "운영디자인",
        "시안",
        "포토샵",
        "일러스트",
        "figma",
        "blender",
        "adobe xd",
        "포트폴리오",
    ],
    "마케팅/기획": [
        "마케팅",
        "마케팅 전략",
        "브랜딩",
        "콘텐츠",
        "기획",
        "프로모션",
        "시장 조사",
        "전략 기획",
        "자료 분석",
    ],
    "MD/구매": [
        "md",
        "온라인 md",
        "구매",
        "구매 담당",
        "상품관리",
        "상품 등록",
        "제품 구매",
        "원부자재",
        "소싱",
        "협력사",
        "견적",
        "단가 관리",
        "생산 일정 관리",
    ],
    "사무/행정": [
        "사무",
        "행정",
        "사무행정",
        "일반사무",
        "전산 보조",
        "문서작성",
        "보고서 작성",
        "excel",
        "powerpoint",
        "oa",
        "컴퓨터활용능력",
    ],
    "고객상담/CS": [
        "고객상담",
        "고객 상담",
        "고객센터",
        "cs",
        "게시판",
        "카카오채널",
        "어드민",
        "고객 응대",
    ],
    "영업/판매": [
        "영업",
        "기술영업",
        "b2b 영업",
        "판매",
        "매장",
        "매장관리",
        "고객응대",
        "가구판매",
        "견적",
        "협상",
    ],
    "물류/유통": [
        "물류",
        "납품",
        "입출고",
        "출고",
        "재고관리",
        "재고 관리",
        "유통",
        "유통망",
        "지게차",
        "erp",
    ],
    "생산/품질": [
        "생산",
        "생산직",
        "생산관리",
        "생산 일정 관리",
        "품질관리",
        "품질 관리",
        "설비운전",
        "원료계량",
        "혼합",
        "믹서 운전",
        "3교대",
    ],
    "교육/강사": [
        "강사",
        "강의",
        "교육",
        "수업",
        "코딩체험",
        "코딩 체험",
        "학교",
        "학생 대상",
    ],
    "어학/영어교육": [
        "영어회화",
        "영어 강의",
        "공인어학",
        "원어민",
        "toeic",
        "영어능통",
        "영어가능",
        "영어영문학",
    ],
    "제과제빵": [
        "제과",
        "제빵",
        "제과제빵",
        "반죽",
        "제과제빵보조",
    ],
    "패션/의류소싱": [
        "의류",
        "패션",
        "섬유",
        "원부자재",
        "발주",
        "소싱",
        "브랜드 의류",
    ],
}


REQUIREMENT_ALIASES = {
    "운전가능": ["운전 가능", "운전가능자", "운전면허", "2종보통운전면허", "차량소지자", "차량 소지자"],
    "외근가능": ["외근", "이동근무", "현장 이동", "고객 현장", "파견"],
    "주말근무가능": ["주말 근무", "공휴일 근무", "휴일 근무", "당직근무"],
    "교대근무가능": ["교대 근무", "3교대", "야간근무", "야간 근무"],
    "문서작성가능": ["문서작성", "문서 작성", "보고서 작성", "자료 작성"],
    "오피스활용가능": ["excel", "엑셀", "powerpoint", "ppt", "oa", "microsoft office", "오피스프로그램"],
    "영어가능": ["영어가능", "영어 가능", "비즈니스영어", "영어능통", "toeic", "toefl", "opic"],
    "디자인툴활용": ["photoshop", "포토샵", "illustrator", "일러스트", "figma", "adobe xd", "blender"],
    "개발경험": ["개발 경험", "프로젝트 개발", "웹 개발", "앱 개발", "프론트엔드 개발", "백엔드 개발"],
    "데이터분석경험": ["데이터 분석", "데이터분석", "sql", "통계", "모델링", "tableau", "spss"],
    "하드웨어이해": ["하드웨어 이해", "pc 하드웨어", "hw 이해", "장비 이해"],
    "전기전자통신이해": ["전기", "전자", "통신", "전기전자", "전기/전자"],
    "고객응대경험": ["고객상담", "고객 상담", "고객응대", "고객 응대", "cs", "게시판", "카카오채널"],
    "재고물류경험": ["재고관리", "입출고", "출고관리", "납품", "물류 관리"],
    "생산품질경험": ["생산 일정 관리", "품질 관리", "생산관리", "설비운전"],
    "강의경험": ["강의", "수업", "강사", "교육", "학생 대상"],
    "포트폴리오필요": ["포트폴리오"],
}


TASK_KEYWORDS = {
    "데이터 분석": ["데이터 분석", "데이터분석", "자료 분석", "통계", "모델링", "대시보드"],
    "AI 모델 개발": ["ai 모델", "모델 개발", "머신러닝", "딥러닝", "생성형 ai", "llm"],
    "웹 개발": ["웹 개발", "프론트엔드", "백엔드", "웹 퍼블리싱", "ui 구현"],
    "서버 운영": ["서버 운영", "시스템 운영", "장애 대비", "시스템 관리", "취약점 점검"],
    "디자인 제작": ["디자인", "시안", "배너", "카드뉴스", "프로토타입", "3d 모델링"],
    "마케팅 기획": ["마케팅", "전략", "기획", "공모전", "브랜딩", "프로모션"],
    "사무 행정": ["사무", "행정", "문서작성", "보고서 작성", "전산 보조"],
    "고객 상담": ["고객상담", "고객센터", "게시판", "카카오채널", "어드민"],
    "상품 관리": ["상품관리", "상품 등록", "품절", "온라인 md", "스마트스토어", "쿠팡"],
    "구매 소싱": ["구매", "소싱", "원부자재", "협력사", "견적", "단가 관리"],
    "영업 판매": ["영업", "판매", "고객응대", "견적", "협상", "기술영업"],
    "물류 관리": ["입출고", "재고관리", "납품", "물류 관리", "출고 관리"],
    "생산 품질": ["생산", "생산 일정 관리", "품질 관리", "설비운전", "원료계량"],
    "설치 유지보수": ["설치", "a/s", "유지보수", "점검", "장비", "하드웨어"],
    "강의 교육": ["강의", "수업", "강사", "교육", "코딩체험", "영어회화"],
    "제과제빵": ["제과", "제빵", "반죽", "제과제빵보조"],
}


LOW_VALUE_WORDS = [
    "성실성",
    "꼼꼼함",
    "협동심",
    "적응성",
    "성장지향성",
    "계획성",
    "윤리의식",
    "성취지향성",
    "스트레스관리",
    "근면성실",
    "정직한 분",
    "리더쉽",
    "리더십",
    "소통",
    "커뮤니케이션",
]


STOPWORDS = [
    "서류전형",
    "1차면접",
    "2차면접",
    "임원면접",
    "직무인터뷰",
    "컬처핏인터뷰",
    "컬처핏",
    "최종심사",
    "최종합격",
    "최종평가",
    "면접일정",
    "추후 통보",
    "접수기간",
    "접수방법",
    "잡코리아 즉시지원",
    "지원양식",
    "잡코리아 이력서",
    "인사담당자",
    "마감일",
    "조기 마감",
    "채용 시 마감",
    "상시채용",
    "기업 정보",
    "기업정보 더보기",
    "지도보기",
    "인근지하철",
    "도보",
    "유의사항",
    "허위사실",
    "채용이 취소",
    "제출서류",
    "기재 내용",
    "기재 착오",
    "문의사항",
    "채용 홈페이지",
    "합류 과정",
    "복리후생",
    "복지혜택",
    "자율복장",
    "웰컴 키트",
    "생일 선물",
    "휴양시설",
    "사내 카페",
    "직원 할인",
    "퇴직금",
    "4대 보험",
    "수습기간",
    "면접비",
    "본사 면접",
    "최종평가에 영향없음",
    "ai역량검사",
    "ai 역량검사",
]


def normalize_text(text):
    text = str(text or "").lower()
    text = text.replace("ㆍ", " ")
    text = text.replace("·", " ")
    text = text.replace("/", " ")
    text = text.replace("|", " ")
    text = text.replace("(", " ")
    text = text.replace(")", " ")
    text = text.replace("[", " ")
    text = text.replace("]", " ")
    text = text.replace(",", " ")
    text = text.replace(":", " ")
    text = text.replace(";", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def remove_stopwords(text):
    result = str(text or "")

    for word in STOPWORDS + LOW_VALUE_WORDS:
        result = re.sub(re.escape(word), " ", result, flags=re.IGNORECASE)

    result = re.sub(r"\s+", " ", result)

    return result.strip()


def contains_keyword(text, keyword):
    normalized_text = normalize_text(text)
    normalized_keyword = normalize_text(keyword)

    if not normalized_keyword:
        return False

    if normalized_keyword == "c":
        return bool(re.search(r"(^|[^a-zA-Z0-9가-힣])c([^a-zA-Z0-9가-힣]|$)", normalized_text))

    return normalized_keyword in normalized_text


def extract_from_alias_dict(text, alias_dict):
    found = set()

    for standard_word, aliases in alias_dict.items():
        for alias in aliases:
            if contains_keyword(text, alias):
                found.add(standard_word)
                break

    return sorted(found)


def extract_job_categories(text):
    found = set()

    for category, keywords in JOB_CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if contains_keyword(text, keyword):
                found.add(category)
                break

    return sorted(found)


def extract_task_keywords(text):
    found = set()

    for task, keywords in TASK_KEYWORDS.items():
        for keyword in keywords:
            if contains_keyword(text, keyword):
                found.add(task)
                break

    return sorted(found)


def extract_dictionary_features(text):
    cleaned_text = remove_stopwords(text)

    return {
        "skills": extract_from_alias_dict(cleaned_text, SKILL_ALIASES),
        "certifications": extract_from_alias_dict(cleaned_text, CERT_ALIASES),
        "requirements": extract_from_alias_dict(cleaned_text, REQUIREMENT_ALIASES),
        "categories": extract_job_categories(cleaned_text),
        "tasks": extract_task_keywords(cleaned_text),
        "cleanedText": normalize_text(cleaned_text),
    }


def standardize_text(text):
    cleaned_text = remove_stopwords(text)
    features = extract_dictionary_features(cleaned_text)

    tokens = []

    for key in ["categories", "skills", "certifications", "requirements", "tasks"]:
        tokens.extend(features.get(key, []))

    unique_tokens = []
    seen = set()

    for token in tokens:
        if token not in seen:
            unique_tokens.append(token)
            seen.add(token)

    return " ".join([features["cleanedText"], *unique_tokens]).strip()


def get_category_overlap(resume_text, job_text):
    resume_categories = set(extract_job_categories(resume_text))
    job_categories = set(extract_job_categories(job_text))

    if not resume_categories or not job_categories:
        return {
            "resumeCategories": sorted(resume_categories),
            "jobCategories": sorted(job_categories),
            "matchedCategories": [],
            "categoryMatched": False,
        }

    matched_categories = sorted(resume_categories & job_categories)

    return {
        "resumeCategories": sorted(resume_categories),
        "jobCategories": sorted(job_categories),
        "matchedCategories": matched_categories,
        "categoryMatched": len(matched_categories) > 0,
    }