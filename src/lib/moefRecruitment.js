const DEFAULT_API_URL = 'https://apis.data.go.kr/1051000/recruitment/list'

let activeSyncPromise = null

export function mapMoefCategory(...values) {
  const source = values.flat(Infinity).filter(Boolean).join(' ').toLowerCase()

  const rules = [
    ['IT/개발', ['정보통신', '정보기술', '소프트웨어', '데이터', '인공지능', '전산', '개발']],
    ['의료/바이오', ['보건·의료', '보건의료', '의료', '바이오', '생명과학', '제약']],
    ['디자인', ['문화·예술·디자인·방송', '디자인', '문화예술', '방송', '콘텐츠', '섬유·의복']],
    ['마케팅', ['마케팅', '광고', '홍보', '시장조사']],
    ['영업·고객상담', ['영업판매', '영업·판매', '고객상담', '판매']],
    ['교육', ['교육·자연·사회과학', '교육', '교사', '강사']],
    ['운전/운송/배송', ['운전·운송', '운전운송', '운송', '물류', '배송']],
    ['건축/시설', ['건설', '건축', '시설', '기계', '전기·전자', '전기전자', '환경·에너지·안전']],
    ['사무·총무', ['사업관리', '경영·회계·사무', '경영회계사무', '금융·보험', '금융보험', '행정', '총무', '회계']],
  ]

  for (const [category, keywords] of rules) {
    if (keywords.some((keyword) => source.includes(keyword.toLowerCase()))) return category
  }
  return '기타'
}

function text(value) {
  if (value === null || value === undefined) return ''
  if (Array.isArray(value)) return value.map(text).filter(Boolean).join(', ')
  if (typeof value === 'object') {
    return text(value.name || value.value || value.text || value.title || Object.values(value))
  }
  return String(value).replace(/\s+/g, ' ').trim()
}

function list(value) {
  if (value === null || value === undefined || value === '') return []
  if (Array.isArray(value)) return [...new Set(value.flatMap(list))]
  if (typeof value === 'object') {
    return list(value.name || value.value || value.text || Object.values(value))
  }
  return [...new Set(String(value).split(/[\r\n|;,]+/).map((item) => item.trim()).filter(Boolean))]
}

function normalizeSteps(value) {
  const items = Array.isArray(value) ? value : value ? [value] : []
  return [...new Set(items.map((item) => {
    if (typeof item !== 'object') return text(item)
    return text(item.recrutStepNm || item.stepNm || item.name || item.recrutStepExpln || item)
  }).filter(Boolean))]
}

function normalizeFiles(value) {
  const items = Array.isArray(value) ? value : value ? [value] : []
  return items.map((item) => {
    if (typeof item !== 'object') return { name: text(item), url: '', type: '' }
    return {
      name: text(item.atchFileNm || item.fileNm || item.name),
      url: text(item.url || item.fileUrl || item.atchFileUrl),
      type: text(item.atchFileTypeNm || item.fileType || item.type),
    }
  }).filter((item) => item.name || item.url)
}

function responseItems(payload) {
  const wrappedItems = payload?.response?.body?.items
  const candidate = payload?.result ?? payload?.items ?? wrappedItems
  if (Array.isArray(candidate)) return candidate
  if (Array.isArray(candidate?.item)) return candidate.item
  if (candidate?.item && typeof candidate.item === 'object') return [candidate.item]
  if (candidate && typeof candidate === 'object') return [candidate]
  return []
}

function responseTotal(payload, fallback) {
  const value = payload?.totalCount ?? payload?.response?.body?.totalCount
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

export function normalizeMoefRecruitment(item) {
  const externalId = text(item.recrutPblntSn || item.recruitmentId || item.id)
  if (!externalId) throw new Error('재정경제부 채용공고에 고유번호가 없습니다.')

  const title = text(item.recrutPbancTtl)
  const companyName = text(item.instNm)
  const sourceUrl = text(item.srcUrl)
  const ncsCodes = list(item.ncsCdLst)
  const ncsNames = list(item.ncsCdNmLst)
  const locations = list(item.workRgnNmLst)
  const educationNames = list(item.acbgCondNmLst)
  const hireTypes = list(item.hireTypeNmLst)
  const recruitmentTypes = list(item.recrutSeNm)
  const requiredQualifications = list(item.aplyQlfcCn)
  const preferredQualifications = list(item.prefCondCn || item.prefCn)
  const screening = list(item.scrnprcdrMthdExpln)
  const steps = normalizeSteps(item.steps)
  const responsibilities = [...new Set([...ncsNames, ...screening, ...steps])]
  const rawCategory = ncsNames.join(', ') || recruitmentTypes.join(', ')
  const category = mapMoefCategory(ncsNames, title, recruitmentTypes)
  const employmentType = hireTypes.join(', ')
  const education = educationNames.join(', ')
  const location = locations.join(', ')
  const recruitmentType = recruitmentTypes.join(', ')
  const fullForEmbedding = [
    title,
    companyName,
    category,
    location,
    employmentType,
    recruitmentType,
    ...responsibilities,
    ...requiredQualifications,
    ...preferredQualifications,
  ].filter(Boolean).join(' / ')

  return {
    documentId: `moef_${externalId}`,
    jobPosting: {
      title,
      companyName,
      category,
      sourceUrl,
      sourceSite: 'moef_job_alio',
      postingType: 'open_api',
      job: {
        department: category,
        employmentType,
        hiringCount: item.recrutNope ?? '',
        recruitmentType,
      },
      responsibilities,
      requirements: {
        requiredSkills: [],
        preferredSkills: [],
        requiredQualifications,
        preferredQualifications,
        coreCompetencies: ncsNames,
        certifications: [],
        education: { minimum: education, raw: education },
        experience: { type: recruitmentType, raw: recruitmentType },
      },
      workConditions: { location, salary: '' },
      recruitment: {
        startDate: text(item.pbancBgngYmd),
        endDate: text(item.pbancEndYmd),
        isActive: text(item.ongoingYn).toUpperCase() === 'Y',
        steps,
        applicationMethod: text(item.scrnprcdrMthdExpln),
      },
      ncs: { codes: ncsCodes, names: ncsNames },
      sourceCategory: rawCategory,
      attachments: normalizeFiles(item.files),
      embeddingText: {
        fullForEmbedding,
        responsibilitiesForEmbedding: responsibilities.join(' / '),
        qualificationsForEmbedding: [...requiredQualifications, ...preferredQualifications].join(' / '),
      },
    },
    meta: {
      source: 'moef_job_alio',
      sourceUrl,
      companyName,
      title,
      postingType: 'open_api',
      externalId,
    },
    rawApiData: item,
  }
}

async function fetchPage({ apiKey, apiUrl, pageNo, numOfRows }) {
  const url = new URL(apiUrl)
  // data.go.kr exposes both encoding and decoding keys. URLSearchParams
  // performs encoding itself, so decode a pre-encoded key exactly once.
  let normalizedApiKey = apiKey
  if (/%[0-9a-f]{2}/i.test(apiKey)) {
    try {
      normalizedApiKey = decodeURIComponent(apiKey)
    } catch {
      normalizedApiKey = apiKey
    }
  }
  url.searchParams.set('serviceKey', normalizedApiKey)
  url.searchParams.set('pageNo', String(pageNo))
  url.searchParams.set('numOfRows', String(numOfRows))
  url.searchParams.set('ongoingYn', 'Y')

  const response = await fetch(url, {
    headers: { Accept: 'application/json' },
    cache: 'no-store',
    signal: AbortSignal.timeout(20000),
  })
  const body = await response.text()
  if (!response.ok) throw new Error(`재정경제부 API HTTP ${response.status}: ${body.slice(0, 200)}`)

  let payload
  try {
    payload = JSON.parse(body)
  } catch {
    throw new Error(`재정경제부 API가 JSON이 아닌 응답을 반환했습니다: ${body.slice(0, 200)}`)
  }

  const resultCode = payload?.resultCode ?? payload?.response?.header?.resultCode
  if (![undefined, null, 0, '0', '00', 200, '200'].includes(resultCode)) {
    const message = payload?.resultMsg ?? payload?.response?.header?.resultMsg ?? ''
    throw new Error(`재정경제부 API 오류 ${resultCode}: ${message}`)
  }
  return payload
}

async function writePostings(db, postings) {
  let writes = 0
  for (let offset = 0; offset < postings.length; offset += 400) {
    const batch = db.batch()
    for (const posting of postings.slice(offset, offset + 400)) {
      const ref = db.collection('job_postings').doc(posting.documentId)
      batch.set(ref, {
        jobPosting: posting.jobPosting,
        meta: posting.meta,
        rawApiData: posting.rawApiData,
        updatedAt: new Date().toISOString(),
      }, { merge: true })
      writes += 1
    }
    await batch.commit()
  }
  return writes
}

async function performSync(db, settings) {
  const allItems = []
  let pageNo = 1
  let totalCount = Infinity

  while (pageNo <= settings.maxPages && allItems.length < totalCount) {
    const payload = await fetchPage({ ...settings, pageNo })
    const items = responseItems(payload)
    if (items.length === 0) break
    allItems.push(...items)
    totalCount = responseTotal(payload, allItems.length)
    if (items.length < settings.numOfRows) break
    pageNo += 1
  }

  const normalized = []
  const errors = []
  for (const item of allItems) {
    try {
      normalized.push(normalizeMoefRecruitment(item))
    } catch (error) {
      errors.push(error.message)
    }
  }

  const savedCount = await writePostings(db, normalized)
  const syncedAt = new Date().toISOString()
  await db.collection('system_metadata').doc('moef_job_postings_sync').set({
    source: 'moef_job_alio',
    syncedAt,
    receivedCount: allItems.length,
    savedCount,
    errors: errors.slice(0, 20),
  }, { merge: true })

  return { synced: true, syncedAt, receivedCount: allItems.length, savedCount, errors }
}

export async function syncMoefRecruitmentsIfNeeded(db, { force = false } = {}) {
  const apiKey = process.env.MOEF_RECRUITMENT_API_KEY?.trim()
  if (!apiKey) {
    return { synced: false, skipped: true, reason: 'MOEF_RECRUITMENT_API_KEY가 설정되지 않았습니다.' }
  }

  const intervalMinutes = Math.max(Number(process.env.MOEF_SYNC_INTERVAL_MINUTES) || 60, 1)
  const metadataRef = db.collection('system_metadata').doc('moef_job_postings_sync')
  const metadata = await metadataRef.get()
  const lastSync = Date.parse(metadata.data()?.syncedAt || '')
  if (!force && Number.isFinite(lastSync) && Date.now() - lastSync < intervalMinutes * 60 * 1000) {
    return { synced: false, skipped: true, reason: 'sync_interval', syncedAt: metadata.data()?.syncedAt }
  }

  if (!activeSyncPromise) {
    activeSyncPromise = performSync(db, {
      apiKey,
      apiUrl: process.env.MOEF_RECRUITMENT_API_URL?.trim() || DEFAULT_API_URL,
      numOfRows: Math.min(Math.max(Number(process.env.MOEF_SYNC_ROWS_PER_PAGE) || 100, 1), 1000),
      maxPages: Math.max(Number(process.env.MOEF_SYNC_MAX_PAGES) || 10, 1),
    }).finally(() => {
      activeSyncPromise = null
    })
  }
  return activeSyncPromise
}
