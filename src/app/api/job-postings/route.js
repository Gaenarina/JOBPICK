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

  const keyPath = path.join(process.cwd(), 'config', 'firebase_key.json')
  const serviceAccount = JSON.parse(fs.readFileSync(keyPath, 'utf8'))

  initializeApp({
    credential: cert(serviceAccount),
  })
}

function toDisplayText(value, fallback = '') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }

  if (typeof value === 'string' || typeof value === 'number') {
    return String(value)
  }

  if (Array.isArray(value)) {
    const text = value
      .map((item) => toDisplayText(item, ''))
      .filter(Boolean)
      .join(', ')

    return text || fallback
  }

  if (typeof value === 'object') {
    return (
      value.name ||
      value.title ||
      value.value ||
      value.type ||
      value.label ||
      value.text ||
      value.description ||
      fallback
    )
  }

  return fallback
}

function normalizeJob(doc) {
  const data = doc.data() || {}
  const jobPosting = data.jobPosting || {}
  const meta = data.meta || {}
  const requirements = jobPosting.requirements || {}

  const title = toDisplayText(
    jobPosting.title ||
      meta.title ||
      data.title,
    '제목 없음'
  )

  const company = toDisplayText(
    jobPosting.company ||
      jobPosting.companyName ||
      meta.companyName ||
      data.company ||
      data.companyName,
    '회사명 없음'
  )

  const location = toDisplayText(
    jobPosting.location ||
      requirements.location ||
      data.location,
    '지역 미정'
  )

  const career = toDisplayText(
    requirements.experience ||
      jobPosting.experience ||
      data.career ||
      data.experience,
    '경력 미정'
  )

  const category = toDisplayText(
    jobPosting.category ||
      requirements.category ||
      data.category ||
      data.jobCategory,
    '직무 미정'
  )

  const salary = toDisplayText(
    jobPosting.salary ||
      requirements.salary ||
      data.salary,
    '급여 미정'
  )

  const sourceUrl = toDisplayText(
    jobPosting.sourceUrl ||
      meta.sourceUrl ||
      data.sourceUrl,
    ''
  )

  const postingType = toDisplayText(
    meta.postingType ||
      data.postingType,
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
    sourceUrl,
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