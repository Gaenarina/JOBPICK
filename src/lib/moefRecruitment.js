const DEFAULT_API_URL =
  'https://apis.data.go.kr/1051000/recruitment/list'

let activeSyncPromise = null


// ============================================================
// JOBPICK 최종 카테고리
// ============================================================

const NORMALIZED_CATEGORIES = new Set([
  'IT/개발',
  '의료/바이오',
  '디자인',
  '마케팅',
  '영업·고객상담',
  '교육',
  '운전/운송/배송',
  '건축/시설',
  '사무·총무',
  '기타',
])


export function mapMoefCategory(...values) {
  const flattenedValues = values
    .flat(Infinity)
    .map((value) => text(value))
    .filter(Boolean)

  // 이미 JOBPICK 카테고리로 정규화된 값이면 그대로 사용
  const normalizedCategory =
    flattenedValues.find((value) =>
      NORMALIZED_CATEGORIES.has(value)
    )

  if (normalizedCategory) {
    return normalizedCategory
  }

  const source =
    flattenedValues
      .join(' ')
      .toLowerCase()

  const rules = [
    [
      'IT/개발',
      [
        '정보통신',
        '정보기술',
        '소프트웨어',
        '데이터',
        '인공지능',
        '전산',
        '개발',
      ],
    ],

    [
      '의료/바이오',
      [
        '보건·의료',
        '보건.의료',
        '보건의료',
        '의료',
        '바이오',
        '생명과학',
        '제약',
      ],
    ],

    [
      '디자인',
      [
        '문화·예술·디자인·방송',
        '문화.예술.디자인.방송',
        '디자인',
        '문화예술',
        '방송',
        '콘텐츠',
        '섬유·의복',
        '섬유.의복',
      ],
    ],

    [
      '마케팅',
      [
        '마케팅',
        '광고',
        '홍보',
        '시장조사',
      ],
    ],

    [
      '영업·고객상담',
      [
        '영업판매',
        '영업·판매',
        '영업.판매',
        '고객상담',
        '판매',
      ],
    ],

    [
      '교육',
      [
        '교육·자연·사회과학',
        '교육.자연.사회과학',
        '교육',
        '교사',
        '강사',
      ],
    ],

    [
      '운전/운송/배송',
      [
        '운전·운송',
        '운전.운송',
        '운전운송',
        '운송',
        '물류',
        '배송',
      ],
    ],

    [
      '건축/시설',
      [
        '건설',
        '건축',
        '시설',
        '기계',
        '전기·전자',
        '전기.전자',
        '전기전자',
        '환경·에너지·안전',
        '환경.에너지.안전',
      ],
    ],

    [
      '사무·총무',
      [
        '사업관리',
        '경영·회계·사무',
        '경영.회계.사무',
        '경영회계사무',
        '금융·보험',
        '금융.보험',
        '금융보험',
        '행정',
        '총무',
        '회계',
      ],
    ],
  ]

  const matchedCategories = []

  for (
    const [category, keywords]
    of rules
  ) {
    if (
      keywords.some((keyword) =>
        source.includes(
          keyword.toLowerCase()
        )
      )
    ) {
      matchedCategories.push(
        category
      )
    }
  }

  const uniqueCategories = [
    ...new Set(matchedCategories),
  ]

  if (uniqueCategories.length === 1) {
    return uniqueCategories[0]
  }

  // 여러 직군이 묶인 통합공고
  if (uniqueCategories.length > 1) {
    return '기타'
  }

  return '기타'
}


// ============================================================
// 기본 텍스트
// ============================================================

function text(value) {
  if (
    value === null ||
    value === undefined
  ) {
    return ''
  }

  if (Array.isArray(value)) {
    return value
      .map(text)
      .filter(Boolean)
      .join(', ')
  }

  if (
    typeof value === 'object'
  ) {
    return text(
      value.name ||
      value.value ||
      value.text ||
      value.title ||
      Object.values(value)
    )
  }

  return String(value)
    .replace(/\s+/g, ' ')
    .trim()
}


function list(value) {
  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return []
  }

  if (Array.isArray(value)) {
    return [
      ...new Set(
        value.flatMap(list)
      ),
    ]
  }

  if (
    typeof value === 'object'
  ) {
    return list(
      value.name ||
      value.value ||
      value.text ||
      Object.values(value)
    )
  }

  return [
    ...new Set(
      String(value)
        .split(/[\r\n|;,]+/)
        .map((item) =>
          item.trim()
        )
        .filter(Boolean)
    ),
  ]
}


const LIST_MARKER_PATTERN =
  /^\s*(?:[-–—•·ㆍ※○?□■▪◆◇▶▷]+|[oOㅇ](?=\s|[가-힣])|[가-하][.)]|(?:\d+)[.)]|[①-⑳])\s*/


function stripListMarker(value) {
  return String(value)
    .replace(
      LIST_MARKER_PATTERN,
      ''
    )
    .replace(/\s+/g, ' ')
    .trim()
}


// ============================================================
// 줄 단위 목록
// ============================================================

function lineList(value) {
  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return []
  }

  if (Array.isArray(value)) {
    return [
      ...new Set(
        value.flatMap(lineList)
      ),
    ]
  }

  if (
    typeof value === 'object'
  ) {
    return lineList(
      value.name ||
      value.value ||
      value.text ||
      Object.values(value)
    )
  }

  return [
    ...new Set(
      String(value)
        .split(/[\r\n|]+/)
        .map(stripListMarker)
        .filter(Boolean)
    ),
  ]
}


// ============================================================
// 자격요건 전용 처리
// ============================================================

function cleanQualificationText(
  value
) {
  let cleaned = text(value)

  if (!cleaned) {
    return ''
  }

  const detailMatch =
    cleaned.match(
      /(?:\(\*?\s*|※\s*)?(?:보다\s+)?자세한\s+사항은/i
    )

  if (
    detailMatch &&
    detailMatch.index !== undefined
  ) {
    cleaned = cleaned
      .slice(
        0,
        detailMatch.index
      )
  }

  cleaned = cleaned
    .replace(
      /^[\s,;:*()]+|[\s,;:*()]+$/g,
      ''
    )
    .replace(/\s+/g, ' ')
    .trim()

  const compact =
    cleaned.replace(/\s+/g, '')

  const vaguePatterns = new Set([
    '제한경쟁요건',
    '제한경쟁요건등',
    '모집분야별응시자격',
    '모집분야별응시자격등',
    '응시자격',
    '응시자격등',
    '지원자격',
    '지원자격등',
  ])

  if (
    vaguePatterns.has(compact)
  ) {
    return ''
  }

  if (
  new Set([
    '가점사항',
    '우대사항',
    '우대조건',
    '우대자격',
  ]).has(compact)
) {
  return ''
}

  if (
    (
      compact.includes('공고문') ||
      compact.includes('첨부파일')
    ) &&
    (
      compact.includes('참조') ||
      compact.includes('참고')
    )
  ) {
    return ''
  }

  return cleaned
}


function qualificationList(
  value
) {
  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return []
  }

  if (Array.isArray(value)) {
    return [
      ...new Set(
        value.flatMap(
          qualificationList
        )
      ),
    ]
  }

  if (
    typeof value === 'object'
  ) {
    return qualificationList(
      value.name ||
      value.value ||
      value.text ||
      Object.values(value)
    )
  }

  const rawLines =
    String(value)
      .split(/[\r\n|]+/)

  const result = []

  let current = ''

  for (
    const originalLine
    of rawLines
  ) {
    const rawLine =
      originalLine.trim()

    if (!rawLine) {
      continue
    }

    const hasMarker =
      LIST_MARKER_PATTERN.test(
        rawLine
      )

    const cleaned =
      stripListMarker(rawLine)

    if (!cleaned) {
      continue
    }

    const startsLabeledCondition =
      /^\([^)]{1,100}\)/.test(
        cleaned
      )

    if (
      !current ||
      hasMarker ||
      startsLabeledCondition
    ) {
      if (current) {
        const normalized =
          cleanQualificationText(
            current
          )

        if (normalized) {
          result.push(
            normalized
          )
        }
      }

      current = cleaned
    } else {
      current =
        `${current} ${cleaned}`
          .trim()
    }
  }

  if (current) {
    const normalized =
      cleanQualificationText(
        current
      )

    if (normalized) {
      result.push(normalized)
    }
  }

  return [
    ...new Set(result),
  ]
}


// ============================================================
// 특정 모집분야 조건
// ============================================================

function isConditionalQualification(
  value
) {
  const cleaned = text(value)

  const match =
    cleaned.match(
      /^\(([^)]+)\)/
    )

  if (!match) {
    return false
  }

  const label =
    match[1]
      .replace(/\s+/g, '')
      .toLowerCase()

  if (
    label.includes('공통') ||
    label.includes('전체')
  ) {
    return false
  }

  const conditionalMarkers = [
    '_',
    '제한경쟁',
    '장애인',
    '자립준비',
    '북한이탈',
    '다문화',
    '보훈',
    '취업지원',
    '지역인재',
    '고졸',
    '특성화고',
    '체험형청년인턴',
    '채용형인턴',
    '기간제',
    '무기계약',
    '직무',
    '직종',
    '분야',
  ]

  return conditionalMarkers.some(
    (marker) =>
      label.includes(marker)
  )
}


function splitRequiredQualifications(
  value
) {
  const required = []
  const conditional = []

  for (
    const qualification
    of qualificationList(value)
  ) {
    if (
      isConditionalQualification(
        qualification
      )
    ) {
      conditional.push(
        qualification
      )
    } else {
      required.push(
        qualification
      )
    }
  }

  return {
    required: [
      ...new Set(required),
    ],

    conditional: [
      ...new Set(conditional),
    ],
  }
}



function parseApplicationRequirements(
  value
) {
  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return {
      required: [],
      conditional: [],
      responsibilities: [],
    }
  }

  const rawLines =
    String(value)
      .split(/[\r\n|]+/)
      .map((line) =>
        line.trim()
      )
      .filter(Boolean)

  const required = []
  const conditional = []
  const responsibilities = []

  let currentScope = 'common'
  let currentGroup = ''

  const addRequired = (
    value
  ) => {
    const cleaned =
      cleanQualificationText(
        value
      )

    if (cleaned) {
      required.push(cleaned)
    }
  }

  const addConditional = (
    value,
    group = ''
  ) => {
    const cleaned =
      cleanQualificationText(
        value
      )

    if (!cleaned) {
      return
    }

    conditional.push(
      group
        ? `(${group}) ${cleaned}`
        : cleaned
    )
  }

  const addResponsibility = (
    value,
    group = ''
  ) => {
    const cleaned = text(value)

    if (!cleaned) {
      return
    }

    responsibilities.push(
      group
        ? `(${group}) ${cleaned}`
        : cleaned
    )
  }

  for (
    let index = 0;
    index < rawLines.length;
    index += 1
  ) {
    const rawLine =
      rawLines[index]

    const cleanedLine =
      stripListMarker(
        rawLine
      )

    if (!cleanedLine) {
      continue
    }

    const compact =
      cleanedLine
        .replace(/\s+/g, '')
        .toLowerCase()

    if (
      [
        '공통',
        '공통사항',
        '공통자격',
        '공통자격요건',
      ].includes(compact)
    ) {
      currentScope = 'common'
      currentGroup = ''
      continue
    }

    if (
      [
        '직종별자격',
        '직종별자격요건',
        '모집분야별자격',
        '모집분야별자격요건',
        '분야별자격',
        '분야별자격요건',
      ].some((keyword) =>
        compact.includes(keyword)
      )
    ) {
      currentScope = 'conditional'
      currentGroup = ''
      continue
    }

    const numberedHeader =
      /^\s*\d+[.)]\s*/.test(
        rawLine
      )

    if (numberedHeader) {
          const nextLines =
      rawLines
        .slice(index + 1, index + 4)
        .join(' ')

    const hasStructuredFields = [
      '담당업무',
      '담당 업무',
      '담당직무',
      '담당 직무',
      '자격요건',
      '지원자격',
      '응시자격',
      '자격:',
      '자격 :',
      '자격：',
    ].some((keyword) =>
      nextLines.includes(keyword)
    )

    const bracketHeaderMatch =
      cleanedLine.match(
        /^\[([^\]]{1,100})\]$/
      )

    if (
      bracketHeaderMatch &&
      hasStructuredFields
    ) {
      currentScope = 'conditional'
      currentGroup =
        bracketHeaderMatch[1].trim()
      continue
    }

    if (
      /\d+\s*명\s*$/.test(cleanedLine) &&
      hasStructuredFields
    ) {
      currentScope = 'conditional'

      currentGroup =
        cleanedLine
          .replace(
            /\s*[:：]?\s*\d+\s*명\s*$/,
            ''
          )
          .replace(/^\[|\]$/g, '')
          .trim()

      continue
    }
    }

    if (
      currentScope ===
        'conditional' &&
      numberedHeader
    ) {
      if (
        cleanedLine.includes(
          ':'
        ) ||
        cleanedLine.includes(
          '：'
        )
      ) {
        const parts =
          cleanedLine.split(
            /[:：]/,
            2
          )

        if (parts[0]?.trim()) {
          currentGroup =
            parts[0].trim()
        }

        if (parts[1]?.trim()) {
          addConditional(
            parts[1].trim(),
            currentGroup
          )
        }

        continue
      }

      currentGroup =
        cleanedLine
          .replace(
            /\s+\d+\s*명\s*$/,
            ''
          )
          .trim()

      continue
    }

    const responsibilityMatch =
      cleanedLine.match(
        /(?:담당업무|담당 업무|담당직무|담당 직무)\s*[:：]\s*(.+)$/i
      )

    if (responsibilityMatch) {
      addResponsibility(
        responsibilityMatch[1],
        currentGroup
      )
      continue
    }

    if (
      /(?:계약기간|근무기간)\s*[:：]/i
        .test(cleanedLine)
    ) {
      continue
    }

    const qualificationMatch =
      cleanedLine.match(
        /(?:자격요건|지원자격|응시자격|자격)\s*[:：]\s*(.+)$/i
      )

    if (qualificationMatch) {
      if (currentGroup) {
        addConditional(
          qualificationMatch[1],
          currentGroup
        )
      } else {
        addRequired(
          qualificationMatch[1]
        )
      }

      continue
    }

    if (currentGroup) {
      addConditional(
        cleanedLine,
        currentGroup
      )
      continue
    }

    if (
      currentScope ===
      'conditional'
    ) {
      addConditional(
        cleanedLine,
        currentGroup
      )
      continue
    }

    addRequired(cleanedLine)
  }

  return {
    required: [
      ...new Set(required),
    ],

    conditional: [
      ...new Set(
        conditional
      ),
    ],

    responsibilities: [
      ...new Set(
        responsibilities
      ),
    ],
  }
}


// ============================================================
// 전형단계
// ============================================================

function normalizeSteps(value) {
  const items =
    Array.isArray(value)
      ? value
      : value
        ? [value]
        : []

  return [
    ...new Set(
      items
        .map((item) => {
          if (
            typeof item !== 'object'
          ) {
            return text(item)
          }

          return text(
            item.recrutStepNm ||
            item.stepNm ||
            item.name ||
            item.recrutStepExpln
          )
        })
        .filter(Boolean)
    ),
  ]
}


// ============================================================
// 첨부파일
// ============================================================

function normalizeFiles(value) {
  const items =
    Array.isArray(value)
      ? value
      : value
        ? [value]
        : []

  return items
    .map((item) => {
      if (
        typeof item !== 'object'
      ) {
        return {
          name: text(item),
          url: '',
          type: '',
        }
      }

      return {
        name: text(
          item.atchFileNm ||
          item.fileNm ||
          item.name
        ),

        url: text(
          item.url ||
          item.fileUrl ||
          item.atchFileUrl
        ),

        type: text(
          item.atchFileTypeNm ||
          item.atchFileType ||
          item.fileType ||
          item.type
        ),
      }
    })
    .filter(
      (item) =>
        item.name ||
        item.url
    )
}


// ============================================================
// 접수방법
// ============================================================

function extractApplicationMethod(
  value
) {
  if (!value) {
    return ''
  }

  const match =
    String(value).match(
      /(?:접수방법|접수 방법)\s*[:：]\s*([^\r\n※]+)/
    )

  return match
    ? text(match[1])
    : ''
}


// ============================================================
// API 응답
// ============================================================

function responseItems(payload) {
  const wrappedItems =
    payload?.response
      ?.body
      ?.items

  const candidate =
    payload?.result ??
    payload?.items ??
    wrappedItems

  if (Array.isArray(candidate)) {
    return candidate
  }

  if (
    Array.isArray(
      candidate?.item
    )
  ) {
    return candidate.item
  }

  if (
    candidate?.item &&
    typeof candidate.item ===
      'object'
  ) {
    return [
      candidate.item,
    ]
  }

  if (
    candidate &&
    typeof candidate ===
      'object'
  ) {
    return [candidate]
  }

  return []
}


function responseTotal(
  payload,
  fallback
) {
  const value =
    payload?.totalCount ??
    payload?.response
      ?.body
      ?.totalCount

  const number =
    Number(value)

  return Number.isFinite(number)
    ? number
    : fallback
}


// ============================================================
// JOB-ALIO → JOBPICK
// ============================================================

const SEMANTIC_EXCLUDE_KEYWORDS = [
  // 법적/행정적 지원조건
  '결격사유',
  '인사규정',
  '국가공무원법',
  '병역',
  '해외여행',
  '징계',
  '채용비리',
  '부정한방법으로채용',

  // 근무 가능 여부
  '즉시근무',
  '바로근무',
  '즉시업무종사',
  '업무종사가능',
  '근무가가능',
  '근무가능',
  '임용예정일부터',
  '채용예정일즉시',

  // 입대/전역
  '전역예정',
  '전역예정자',

  // 연령/신분/정책 가점
  '청년연령',
  '취업지원대상',
  '취업보호대상',
  '장애대상',
  '장애인',
  '지역인재',
  '정부권장정책',
  '국민기초생활수급',
  '차상위',
  '한부모',
  '북한이탈',
  '다문화',
  '경력단절여성',
  '자립준비청년',
  '국가유공자',
  '보훈대상',
  '취업취약계층',

  //지역/거주 조건
  '주민등록상주소지',
  '거주지',

  // 가점/전형 안내
  '전형별가점',
  '가점적용기준',
  '가산점부여',
  '만점의5%',
  '만점의10%',
  '대상별가산점수가',

  // 계약정보
  '계약기간',
]


function isSemanticRelevantQualification(
  value
) {
  const raw = text(value)

  if (!raw) {
    return false
  }

  const compact =
    raw
      .replace(/\s+/g, '')
      .toLowerCase()

  if (
    !/[가-힣a-zA-Z]/.test(
      raw
    )
  ) {
    return false
  }

  if (
    [
      '가점사항',
      '가점적용기준',
      '우대사항',
      '우대조건',
      '직종별우대사항',
      '직종별자격',
      '직종별자격요건',
    ].includes(compact)
  ) {
    return false
  }

  if (
    compact.includes(
      '제한없음'
    ) &&
    [
      '학력',
      '연령',
      '나이',
      '성별',
      '지역',
      '외국어',
      '경력',
    ].some((keyword) =>
      compact.includes(keyword)
    )
  ) {
    return false
  }

  if (
    /만\s*\d+\s*세/.test(
      raw
    )
  ) {
    return false
  }

  if (
    SEMANTIC_EXCLUDE_KEYWORDS
      .some((keyword) =>
        compact.includes(
          keyword.toLowerCase()
        )
      )
  ) {
    return false
  }

  return true
}


function semanticQualificationList(
  values
) {
  const result = []

  for (
    const value
    of values || []
  ) {
    const original =
      text(value)

    if (!original) {
      continue
    }

    const originalCompact =
      original
        .replace(/\s+/g, '')
        .toLowerCase()

    if (
      originalCompact.includes(
        '제한없음'
      ) &&
      [
        '학력',
        '연령',
        '나이',
        '성별',
        '지역',
        '외국어',
        '경력',
      ].some((keyword) =>
        originalCompact
          .includes(keyword)
      )
    ) {
      continue
    }

    const parts =
      original.split(
        /[,;]+/
      )

    for (
      const part
      of parts
    ) {
      const cleaned =
        text(part)

      if (
        cleaned &&
        isSemanticRelevantQualification(
          cleaned
        )
      ) {
        result.push(cleaned)
      }
    }
  }

  return [
    ...new Set(result),
  ]
}


export function normalizeMoefRecruitment(
  item
) {
  const externalId =
    text(
      item.recrutPblntSn ||
      item.recruitmentId ||
      item.id
    )

  if (!externalId) {
    throw new Error(
      '재정경제부 채용공고에 고유번호가 없습니다.'
    )
  }


  const title =
    text(
      item.recrutPbancTtl
    )

  const companyName =
    text(item.instNm)

  const sourceUrl =
    text(item.srcUrl)


  const ncsSourceCodes =
    list(item.ncsCdLst)

  const ncsNames =
    list(item.ncsCdNmLst)


  const locations =
    list(item.workRgnNmLst)

  const educationNames =
    list(item.acbgCondNmLst)

  const hireTypes =
    list(item.hireTypeNmLst)

  const recruitmentTypes =
    list(item.recrutSeNm)


  // ----------------------------------------------------------
  // 필수 / 조건부 자격요건
  // ----------------------------------------------------------

  const {
    required:
      requiredQualifications,

    conditional:
      conditionalQualifications,

    responsibilities,
  } =
    parseApplicationRequirements(
      item.aplyQlfcCn
    )


  // prefCn 상세 우선, 없으면 prefCondCn
  const preferredSource =
    item.prefCn ||
    item.prefCondCn

  const preferredQualifications =
    qualificationList(
      preferredSource
    )


  // ----------------------------------------------------------
  // 전형절차
  // ----------------------------------------------------------

  const screeningProcedure =
    lineList(
      item.scrnprcdrMthdExpln
    )

  const steps =
    normalizeSteps(
      item.steps
    )


  // ----------------------------------------------------------
  // 카테고리
  // ----------------------------------------------------------

  const rawCategory =
    ncsNames.join(', ') ||
    recruitmentTypes.join(', ')

  const categorySources =
    ncsNames.length > 0
      ? ncsNames
      : [
          title,
          ...recruitmentTypes,
        ]

  const category =
    mapMoefCategory(
      categorySources
    )


  const employmentType =
    hireTypes.join(', ')

  const education =
    educationNames.join(', ')

  const location =
    locations.join(', ')

  const recruitmentType =
    recruitmentTypes.join(', ')


  // ----------------------------------------------------------
  // 임베딩
  //
  // 조건부 자격요건은 전체 공고 임베딩에서 제외한다.
  // ----------------------------------------------------------

  const semanticRequiredQualifications =
  semanticQualificationList(
    requiredQualifications
  )

  const semanticPreferredQualifications =
  semanticQualificationList(
    preferredQualifications
  )
  
  const fullForEmbedding = [
    title,
    category,
    ...ncsNames,
    education,
    recruitmentType,
    ...responsibilities,
    ...semanticRequiredQualifications,
    ...semanticPreferredQualifications,
  ]
    .filter(Boolean)
    .join(' / ')


  return {
    documentId:
      `moef_${externalId}`,

    jobPosting: {
      title,

      companyName,

      category,

      sourceUrl,

      sourceSite:
        'moef_job_alio',

      postingType:
        'open_api',


      job: {
        department:
          category,

        employmentType,

        hiringCount:
          item.recrutNope ??
          item.recrutNope2 ??
          '',

        recruitmentType,
      },


      responsibilities,


      requirements: {
        education: {
          minimum:
            education,

          raw:
            education,
        },

        experience: {
          type:
            recruitmentType,

          raw:
            recruitmentType,
        },

        requiredSkills: [],

        preferredSkills: [],

        requiredQualifications,

        conditionalQualifications,

        preferredQualifications,

        coreCompetencies: [],

        certifications: [],
      },


      workConditions: {
        location,
        salary: '',
      },


      recruitment: {
        startDate:
          text(
            item.pbancBgngYmd
          ),

        endDate:
          text(
            item.pbancEndYmd
          ),

        isActive:
          text(
            item.ongoingYn
          ).toUpperCase() ===
          'Y',

        steps,

        screeningProcedure,

        applicationMethod:
          extractApplicationMethod(
            item.scrnprcdrMthdExpln
          ),
      },


      ncs: {
        // JOB-ALIO 코드 보존용
        // matcher에는 실제 NCS 코드로 전달하지 않음
        codes: [],

        names:
          ncsNames,

        sourceCodes:
          ncsSourceCodes,
      },


      sourceCategory:
        rawCategory,


      attachments:
        normalizeFiles(
          item.files
        ),


      embeddingText: {
        fullForEmbedding,

        responsibilitiesForEmbedding:
          responsibilities.join(' / '),

        qualificationsForEmbedding:
          [
            ...semanticRequiredQualifications,
            ...semanticPreferredQualifications,
          ].join(' / '),
      },
    },


    meta: {
      source:
        'moef_job_alio',

      sourceUrl,

      companyName,

      title,

      postingType:
        'open_api',

      externalId,
    },


    rawApiData:
      item,
  }
}


// ============================================================
// API 호출
// ============================================================

async function fetchPage({
  apiKey,
  apiUrl,
  pageNo,
  numOfRows,
}) {
  const url =
    new URL(apiUrl)

  let normalizedApiKey =
    apiKey

  if (
    /%[0-9a-f]{2}/i.test(
      apiKey
    )
  ) {
    try {
      normalizedApiKey =
        decodeURIComponent(
          apiKey
        )
    } catch {
      normalizedApiKey =
        apiKey
    }
  }

  url.searchParams.set(
    'serviceKey',
    normalizedApiKey
  )

  url.searchParams.set(
    'pageNo',
    String(pageNo)
  )

  url.searchParams.set(
    'numOfRows',
    String(numOfRows)
  )

  url.searchParams.set(
    'ongoingYn',
    'Y'
  )

  const response =
    await fetch(
      url,
      {
        headers: {
          Accept:
            'application/json',
        },

        cache:
          'no-store',

        signal:
          AbortSignal.timeout(
            20000
          ),
      }
    )

  const body =
    await response.text()

  if (!response.ok) {
    throw new Error(
      `재정경제부 API HTTP ${response.status}: ${body.slice(0, 200)}`
    )
  }

  let payload

  try {
    payload =
      JSON.parse(body)
  } catch {
    throw new Error(
      `재정경제부 API가 JSON이 아닌 응답을 반환했습니다: ${body.slice(0, 200)}`
    )
  }

  const resultCode =
    payload?.resultCode ??
    payload?.response
      ?.header
      ?.resultCode

  if (
    ![
      undefined,
      null,
      0,
      '0',
      '00',
      200,
      '200',
    ].includes(resultCode)
  ) {
    const message =
      payload?.resultMsg ??
      payload?.response
        ?.header
        ?.resultMsg ??
      ''

    throw new Error(
      `재정경제부 API 오류 ${resultCode}: ${message}`
    )
  }

  return payload
}


// ============================================================
// Firestore 저장
// ============================================================

async function writePostings(
  db,
  postings
) {
  let writes = 0

  for (
    let offset = 0;
    offset < postings.length;
    offset += 400
  ) {
    const batch =
      db.batch()

    for (
      const posting
      of postings.slice(
        offset,
        offset + 400
      )
    ) {
      const ref =
        db
          .collection(
            'job_postings'
          )
          .doc(
            posting.documentId
          )

      batch.set(
        ref,
        {
          jobPosting:
            posting.jobPosting,

          meta:
            posting.meta,

          rawApiData:
            posting.rawApiData,

          updatedAt:
            new Date()
              .toISOString(),
        },
        {
          merge: true,
        }
      )

      writes += 1
    }

    await batch.commit()
  }

  return writes
}


// ============================================================
// 전체 동기화
// ============================================================

async function performSync(
  db,
  settings
) {
  const allItems = []

  let pageNo = 1
  let totalCount =
    Infinity

  while (
    pageNo <=
      settings.maxPages &&
    allItems.length <
      totalCount
  ) {
    const payload =
      await fetchPage({
        ...settings,
        pageNo,
      })

    const items =
      responseItems(
        payload
      )

    if (
      items.length === 0
    ) {
      break
    }

    allItems.push(
      ...items
    )

    totalCount =
      responseTotal(
        payload,
        allItems.length
      )

    if (
      items.length <
      settings.numOfRows
    ) {
      break
    }

    pageNo += 1
  }


  const normalized = []
  const errors = []


  for (
    const item
    of allItems
  ) {
    try {
      normalized.push(
        normalizeMoefRecruitment(
          item
        )
      )
    } catch (error) {
      errors.push(
        error.message
      )
    }
  }


  const savedCount =
    await writePostings(
      db,
      normalized
    )


  const syncedAt =
    new Date()
      .toISOString()


  await db
    .collection(
      'system_metadata'
    )
    .doc(
      'moef_job_postings_sync'
    )
    .set(
      {
        source:
          'moef_job_alio',

        syncedAt,

        receivedCount:
          allItems.length,

        savedCount,

        errors:
          errors.slice(
            0,
            20
          ),
      },
      {
        merge: true,
      }
    )


  return {
    synced: true,

    syncedAt,

    receivedCount:
      allItems.length,

    savedCount,

    errors,
  }
}


// ============================================================
// 필요할 때 동기화
// ============================================================

export async function syncMoefRecruitmentsIfNeeded(
  db,
  {
    force = false,
  } = {}
) {
  const apiKey =
    process.env
      .MOEF_RECRUITMENT_API_KEY
      ?.trim()

  if (!apiKey) {
    return {
      synced: false,

      skipped: true,

      reason:
        'MOEF_RECRUITMENT_API_KEY가 설정되지 않았습니다.',
    }
  }


  const intervalMinutes =
    Math.max(
      Number(
        process.env
          .MOEF_SYNC_INTERVAL_MINUTES
      ) || 60,
      1
    )


  const metadataRef =
    db
      .collection(
        'system_metadata'
      )
      .doc(
        'moef_job_postings_sync'
      )


  const metadata =
    await metadataRef.get()


  const lastSync =
    Date.parse(
      metadata
        .data()
        ?.syncedAt ||
      ''
    )


  if (
    !force &&
    Number.isFinite(
      lastSync
    ) &&
    Date.now() -
      lastSync <
      intervalMinutes *
        60 *
        1000
  ) {
    return {
      synced: false,

      skipped: true,

      reason:
        'sync_interval',

      syncedAt:
        metadata
          .data()
          ?.syncedAt,
    }
  }


  if (
    !activeSyncPromise
  ) {
    activeSyncPromise =
      performSync(
        db,
        {
          apiKey,

          apiUrl:
            process.env
              .MOEF_RECRUITMENT_API_URL
              ?.trim() ||
            DEFAULT_API_URL,

          numOfRows:
            Math.min(
              Math.max(
                Number(
                  process.env
                    .MOEF_SYNC_ROWS_PER_PAGE
                ) || 100,
                1
              ),
              1000
            ),

          maxPages:
            Math.max(
              Number(
                process.env
                  .MOEF_SYNC_MAX_PAGES
              ) || 10,
              1
            ),
        }
      ).finally(
        () => {
          activeSyncPromise =
            null
        }
      )
  }


  return activeSyncPromise
}