import { NextResponse } from 'next/server'
import { cert, getApps, initializeApp } from 'firebase-admin/app'
import { getFirestore } from 'firebase-admin/firestore'
import fs from 'fs'
import path from 'path'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

function initFirebaseAdmin() {
  if (getApps().length > 0) {
    return
  }

  let serviceAccount;

  // 1. 버셀(Vercel) 환경 변수가 있으면 그걸 사용합니다.
  if (process.env.FIREBASE_SERVICE_ACCOUNT) {
    serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
  } else {
    // 2. 환경 변수가 없으면 (내 컴퓨터 로컬일 때) 기존처럼 파일을 읽습니다.
    const keyPath = path.join(process.cwd(), 'config', 'firebase_key.json')
    serviceAccount = JSON.parse(fs.readFileSync(keyPath, 'utf8'))
  }
  initializeApp({
    credential: cert(serviceAccount),
  })
}

function toDisplayText(value, fallback = '') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }

  if (typeof value === 'string' || typeof value === 'number') {
    return String(value).trim()
  }

  if (Array.isArray(value)) {
    const text = value
      .map((item) => toDisplayText(item, ''))
      .filter(Boolean)
      .join(', ')

    return text || fallback
  }

  if (typeof value === 'object') {
    return toDisplayText(
      value.name ||
        value.title ||
        value.value ||
        value.type ||
        value.label ||
        value.text ||
        value.description,
      fallback
    )
  }

  return fallback
}

function toDisplayList(value) {
  if (!value) return []

  if (Array.isArray(value)) {
    return value
      .map((item) => toDisplayText(item, ''))
      .filter(Boolean)
  }

  if (typeof value === 'string') {
    return value
      .split(/\n|,|ㆍ/)
      .map((item) => item.trim())
      .filter(Boolean)
  }

  if (typeof value === 'object') {
    return Object.values(value)
      .flatMap((item) => toDisplayList(item))
      .filter(Boolean)
  }

  return []
}

function cleanLocationOutput(value) {
  return toDisplayText(value, '')
    .replace(/\s+/g, ' ')
    .replace(/가산\s+디지털/g, '가산디지털')
    .replace(/디지털\s+로/g, '디지털로')
    .replace(/([가-힣])\s+([0-9]+로)/g, '$1$2')
    .trim()
}

function normalizeRegionName(region) {
  const regionMap = {
    서울특별시: '서울',
    부산광역시: '부산',
    대구광역시: '대구',
    인천광역시: '인천',
    광주광역시: '광주',
    대전광역시: '대전',
    울산광역시: '울산',
    세종특별자치시: '세종',
    경기도: '경기',
    강원도: '강원',
    충청북도: '충북',
    충청남도: '충남',
    전라북도: '전북',
    전라남도: '전남',
    경상북도: '경북',
    경상남도: '경남',
    제주도: '제주',
    제주특별자치도: '제주',
  }

  return regionMap[region] || region
}

function shortenLocation(value) {
  let text = toDisplayText(value, '')

  if (!text) return ''

  text = text
    .replace(/^(근무지역|근무지|근무장소|근무지주소|주소)\s*[:：]?\s*/g, '')
    .replace(/\([^)]*\)/g, ' ')
    .replace(/\[[^\]]*\]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

  text = text
    .split(/지도보기|인근지하철|지하철|도보|버스|출구|역에서|역\s|주차|복리후생|근무시간|급여|담당업무|자격요건|우대사항/)[0]
    .trim()

  const regionPattern =
    '(서울|서울특별시|부산|부산광역시|대구|대구광역시|인천|인천광역시|광주|광주광역시|대전|대전광역시|울산|울산광역시|세종|세종특별자치시|경기|경기도|강원|강원도|충북|충청북도|충남|충청남도|전북|전라북도|전남|전라남도|경북|경상북도|경남|경상남도|제주|제주도|제주특별자치도)'

  const areaMatch = text.match(
    new RegExp(
      `${regionPattern}\\s+([가-힣]+(?:시|군|구))(?:\\s+([가-힣0-9]+(?:구|군|읍|면|동|가|리)))?`
    )
  )

  if (areaMatch) {
    const region = normalizeRegionName(areaMatch[1])
    const firstArea = areaMatch[2]
    const secondArea = areaMatch[3] || ''

    let result = `${region} ${firstArea}`

    if (secondArea) {
      result += ` ${secondArea}`
    }

    return cleanLocationOutput(result)
  }

  const cleanedText = cleanLocationOutput(text)

  return cleanedText.length > 15 ? `${cleanedText.slice(0, 15).trim()}...` : cleanedText
}

function getTextPool(jobPosting) {
  const requirements = jobPosting.requirements || {}
  const job = jobPosting.job || {}

  return [
    jobPosting.title,
    jobPosting.companyName,
    job.department,
    job.employmentType,
    ...toDisplayList(jobPosting.responsibilities),
    ...toDisplayList(requirements.requiredSkills),
    ...toDisplayList(requirements.preferredSkills),
    ...toDisplayList(requirements.requiredQualifications),
    ...toDisplayList(requirements.preferredQualifications),
    ...toDisplayList(requirements.coreCompetencies),
    ...toDisplayList(requirements.certifications),
  ]
    .map((item) => toDisplayText(item, ''))
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
}

function inferCategory(jobPosting) {
  const text = getTextPool(jobPosting)

  if (
    text.includes('개발') ||
    text.includes('서버') ||
    text.includes('백엔드') ||
    text.includes('프론트') ||
    text.includes('프론트엔드') ||
    text.includes('웹') ||
    text.includes('앱') ||
    text.includes('데이터') ||
    text.includes('ai') ||
    text.includes('인공지능') ||
    text.includes('머신러닝') ||
    text.includes('딥러닝') ||
    text.includes('python') ||
    text.includes('java') ||
    text.includes('javascript') ||
    text.includes('typescript') ||
    text.includes('react') ||
    text.includes('next') ||
    text.includes('node') ||
    text.includes('spring') ||
    text.includes('django') ||
    text.includes('flask') ||
    text.includes('linux') ||
    text.includes('unix') ||
    text.includes('windows 서버') ||
    text.includes('엔지니어') ||
    text.includes('프로그래머')
  ) {
    return 'IT/개발'
  }

  if (
    text.includes('디자인') ||
    text.includes('figma') ||
    text.includes('photoshop') ||
    text.includes('illustrator') ||
    text.includes('ui') ||
    text.includes('ux') ||
    text.includes('웹디자인')
  ) {
    return '디자인'
  }

  if (
    text.includes('마케팅') ||
    text.includes('광고') ||
    text.includes('콘텐츠') ||
    text.includes('sns') ||
    text.includes('md') ||
    text.includes('브랜딩')
  ) {
    return '마케팅'
  }

  if (
    text.includes('영업') ||
    text.includes('고객') ||
    text.includes('상담') ||
    text.includes('cs') ||
    text.includes('tm') ||
    text.includes('판매')
  ) {
    return '영업·고객상담'
  }

  if (
    text.includes('사무') ||
    text.includes('총무') ||
    text.includes('경리') ||
    text.includes('회계') ||
    text.includes('행정') ||
    text.includes('문서') ||
    text.includes('인사') ||
    text.includes('비서')
  ) {
    return '사무·총무'
  }

  if (
    text.includes('강사') ||
    text.includes('교육') ||
    text.includes('수업') ||
    text.includes('교사') ||
    text.includes('학원')
  ) {
    return '교육'
  }

  if (
    text.includes('간호') ||
    text.includes('의료') ||
    text.includes('병원') ||
    text.includes('바이오') ||
    text.includes('약사') ||
    text.includes('물리치료') ||
    text.includes('임상')
  ) {
    return '의료/바이오'
  }

  if (
    text.includes('배송') ||
    text.includes('운전') ||
    text.includes('운송') ||
    text.includes('물류') ||
    text.includes('배달')
  ) {
    return '운전/운송/배송'
  }

  if (
    text.includes('건축') ||
    text.includes('시설') ||
    text.includes('설비') ||
    text.includes('시공') ||
    text.includes('전기') ||
    text.includes('기계')
  ) {
    return '건축/시설'
  }

  return ''
}

function normalizeJob(doc) {
  const data = doc.data() || {}

  const jobPosting = data.jobPosting || {}
  const legacy = data.legacyJobPosting || {}
  const meta = data.meta || {}

  const job = jobPosting.job || {}
  const requirements = jobPosting.requirements || {}
  const workConditions = jobPosting.workConditions || {}
  const companyInfo = jobPosting.companyInfo || {}

  const education = requirements.education || {}
  const experience = requirements.experience || {}
  const recruitment = jobPosting.recruitment || {}

  const title = toDisplayText(
    jobPosting.title ||
      legacy.title ||
      meta.title ||
      data.title,
    '제목 없음'
  )

  const company = toDisplayText(
    jobPosting.companyName ||
      legacy.companyName ||
      meta.companyName ||
      data.companyName ||
      data.company,
    '회사명 없음'
  )

  const rawLocation = toDisplayText(
    workConditions.location ||
      companyInfo.location ||
      legacy.location ||
      data.location,
    ''
  )

  const location = shortenLocation(rawLocation)

  const career = toDisplayText(
    experience.type ||
      legacy.career ||
      data.career ||
      data.experience,
    ''
  )

  const category =
    toDisplayText(
      jobPosting.category ||
        legacy.category ||
        data.category ||
        data.jobCategory,
      ''
    ) ||
    inferCategory(jobPosting) ||
    toDisplayText(job.department, '')

  const salary = toDisplayText(
    workConditions.salary ||
      legacy.salary ||
      data.salary,
    ''
  )

  const sourceUrl = toDisplayText(
    jobPosting.sourceUrl ||
      legacy.sourceUrl ||
      meta.sourceUrl ||
      data.sourceUrl,
    ''
  )

  const imageUrl = toDisplayText(
    jobPosting.imageUrl ||
      legacy.imageUrl ||
      meta.imageUrl ||
      data.imageUrl,
    ''
  )

  const postingType = toDisplayText(
    jobPosting.postingType ||
      legacy.postingType ||
      meta.postingType ||
      data.postingType,
    ''
  )

  const recruitmentPeriod = toDisplayText(
    legacy.recruitmentPeriod ||
      recruitment.raw,
    ''
  )

  return {
    id: doc.id,
    jobId: doc.id,

    title,
    company,
    location,
    career,
    category,
    salary,

    education: toDisplayText(education.minimum || legacy.education, ''),
    skills: toDisplayList(requirements.requiredSkills || legacy.skills),
    preferredSkills: toDisplayList(requirements.preferredSkills),
    qualifications: toDisplayList(requirements.requiredQualifications || legacy.qualifications),
    preferredQualifications: toDisplayList(requirements.preferredQualifications),
    certifications: toDisplayList(requirements.certifications || legacy.certifications),
    responsibilities: toDisplayList(jobPosting.responsibilities || legacy.responsibilities),

    employmentType: toDisplayText(job.employmentType, ''),
    hiringCount: toDisplayText(job.hiringCount || legacy.hiringCount, ''),
    recruitmentPeriod,
    sourceUrl,
    imageUrl,
    postingType,

    rawData: data,
  }
}

export async function GET() {
  try {
    initFirebaseAdmin()

    const db = getFirestore()
    const snapshot = await db.collection('job_postings').get()

    const jobs = snapshot.docs.map((doc) => normalizeJob(doc))

    return NextResponse.json({
      jobs,
      count: jobs.length,
    })
  } catch (error) {
    console.error('[job-postings 조회 실패]', error)

    return NextResponse.json(
      {
        error: error.message || '채용공고 목록을 불러오지 못했습니다.',
      },
      { status: 500 }
    )
  }
}