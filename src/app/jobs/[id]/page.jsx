'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { X } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { getJobById } from '@/lib/jobs'
import { getBookmarks, toggleBookmark } from '@/lib/userStorage'

function getJobKey(job) {
  return String(job?.id || job?.jobId || '')
}

export default function JobDetailPage() {
  const router = useRouter()
  const params = useParams()
  const { user, mounted } = useAuth()
  const resumeUserId = user?.uid || user?.id || ''

  const [isBookmarked, setIsBookmarked] = useState(false)
  const [matchedJob, setMatchedJob] = useState(null)
  const [showDetail, setShowDetail] = useState(false)

  const id = Array.isArray(params?.id) ? params.id[0] : params?.id
  const staticJob = getJobById(id)
  const job = matchedJob || staticJob

  useEffect(() => {
    if (!mounted || !id) return

    try {
      const saved = localStorage.getItem('jobpick_matched_jobs')
      const matchedJobs = saved ? JSON.parse(saved) : []

      const foundJob = matchedJobs.find(
        (item) => String(item.id) === String(id) || String(item.jobId) === String(id)
      )

      if (foundJob) {
        setMatchedJob(foundJob)
      }
    } catch (error) {
      console.error('매칭 결과 불러오기 실패:', error)
    }
  }, [mounted, id])

  useEffect(() => {
    if (!mounted || !job) return

    const jobKey = getJobKey(job)
    const bookmarked = getBookmarks(resumeUserId).some((item) => getJobKey(item) === jobKey)

    setIsBookmarked(bookmarked)
  }, [mounted, job, resumeUserId])

  if (!mounted) return null

  if (!job) {
    return (
      <main className="max-w-4xl mx-auto p-8">
        <h1 className="text-2xl font-bold mb-4">공고를 찾을 수 없습니다.</h1>
        <button onClick={() => router.back()} className="px-4 py-2 rounded-lg bg-slate-100">
          이전으로
        </button>
      </main>
    )
  }

  const matchDetail = job.matchDetail || {}
  const hasMatchResult = job.matchRate !== undefined && job.matchRate !== null

  return (
    <main className="max-w-4xl mx-auto p-8">
      <div className="bg-white border border-gray-200 rounded-2xl p-6">
        <div className="flex justify-end mb-2">
          <button
            type="button"
            onClick={() => {
              const next = toggleBookmark(job, resumeUserId)
              const jobKey = getJobKey(job)
              setIsBookmarked(next.some((item) => getJobKey(item) === jobKey))
            }}
            aria-label="북마크"
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill={isBookmarked ? '#2563eb' : '#ffffff'}
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M6 3.75C6 3.33579 6.33579 3 6.75 3H17.25C17.6642 3 18 3.33579 18 3.75V21L12 16.5L6 21V3.75Z"
                stroke={isBookmarked ? '#2563eb' : '#94a3b8'}
                strokeWidth="1.8"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>

        <p className="text-gray-500 mb-2">{job.company}</p>
        <h1 className="text-3xl font-bold mb-4">{job.title}</h1>

        <div className="flex gap-2 flex-wrap mb-6">
          <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">
            {job.location || '지역 미정'}
          </span>
          <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">
            {job.career || '경력 미정'}
          </span>
          <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">
            {job.category || '직무 미정'}
          </span>
        </div>

        <div className="grid sm:grid-cols-2 gap-3 mb-6">
          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-sm text-gray-500 mb-1">예상 신입연봉</p>
            <p className="text-2xl font-bold text-primary">{job.salary || '협의'}</p>
          </div>

          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-sm text-gray-500 mb-1">AI 적합도</p>
            <p className="text-2xl font-bold text-primary">
              {hasMatchResult ? `${job.matchRate}점` : '미분석'}
            </p>

            {job.matchDetail && (
              <button
                type="button"
                onClick={() => setShowDetail(true)}
                className="mt-3 px-3 py-2 rounded-lg bg-primary text-white text-sm"
              >
                상세 계산 보기
              </button>
            )}
          </div>
        </div>

        <div className="bg-slate-50 rounded-xl p-5 text-gray-700 leading-7">
          담당 업무: 직무 운영 및 협업, 데이터 기반 개선, 고객/내부 커뮤니케이션 수행
          <br />
          자격 요건: 관련 직무 이해도, 문서 커뮤니케이션 능력, 기본적인 OA 또는 협업툴 활용 가능
          <br />
          우대 사항: 해당 산업 경험, 프로젝트 경험, 빠른 실행력
        </div>
      </div>

      {showDetail && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-xl max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-start gap-4 mb-4">
              <div>
                <p className="text-sm text-gray-500">{job.company}</p>
                <h2 className="text-xl font-bold">{job.title}</h2>
              </div>

              <button
                type="button"
                onClick={() => setShowDetail(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" aria-hidden />
              </button>
            </div>

            <div className="rounded-xl bg-slate-50 p-4 mb-4">
              <p className="text-sm text-gray-500">최종 매칭 점수</p>
              <p className="text-2xl md:text-3xl font-bold text-primary">
                {job.finalScore ?? job.matchRate}점
              </p>
              <p className="text-sm text-gray-600 mt-2">
                룰 기반 {job.ruleTotal ?? 0}점 + 의미 기반 {job.semanticTotal ?? 0}점
              </p>
            </div>

            <div className="space-y-3 text-sm">
              <div className="border border-gray-200 rounded-xl p-4">
                <h3 className="font-semibold mb-2">기술 점수</h3>
                <p>
                  {matchDetail.skills?.score ?? 0}점 / {matchDetail.skills?.maxScore ?? 30}점
                </p>
                <p className="text-gray-500 mt-1">
                  일치 기술:{' '}
                  {matchDetail.skills?.matchedSkills?.length
                    ? matchDetail.skills.matchedSkills.join(', ')
                    : '없음'}
                </p>
              </div>

              <div className="border border-gray-200 rounded-xl p-4">
                <h3 className="font-semibold mb-2">학력 점수</h3>
                <p>
                  {matchDetail.education?.score ?? 0}점 / {matchDetail.education?.maxScore ?? 10}점
                </p>
                <p className="text-gray-500 mt-1">
                  공고 학력: {matchDetail.education?.jobLevel || '무관'} / 이력서 학력:{' '}
                  {matchDetail.education?.resumeLevel || '미확인'}
                </p>
              </div>

              <div className="border border-gray-200 rounded-xl p-4">
                <h3 className="font-semibold mb-2">경력 점수</h3>
                <p>
                  {matchDetail.experience?.score ?? 0}점 / {matchDetail.experience?.maxScore ?? 20}점
                </p>
                <p className="text-gray-500 mt-1">
                  지원자 경력: {matchDetail.experience?.resumeExp ?? 0}년 / 요구 경력:{' '}
                  {matchDetail.experience?.minExp ?? 0}년
                </p>
                <p className="text-gray-500 mt-1">
                  연수 점수: {matchDetail.experience?.yearScore ?? 0}점
                </p>
                <p className="text-gray-500 mt-1">
                  관련성 점수: {matchDetail.experience?.relevanceScore ?? 0}점
                </p>
              </div>

              <div className="border border-gray-200 rounded-xl p-4">
                <h3 className="font-semibold mb-2">자격증 점수</h3>
                <p>
                  {matchDetail.certifications?.score ?? 0}점 /{' '}
                  {matchDetail.certifications?.maxScore ?? 10}점
                </p>
                <p className="text-gray-500 mt-1">
                  일치 자격증:{' '}
                  {matchDetail.certifications?.matchedCerts?.length
                    ? matchDetail.certifications.matchedCerts.join(', ')
                    : '없음'}
                </p>
              </div>

              <div className="border border-gray-200 rounded-xl p-4">
                <h3 className="font-semibold mb-2">자격요건 점수</h3>
                <p>
                  {matchDetail.qualifications?.score ?? 0}점 /{' '}
                  {matchDetail.qualifications?.maxScore ?? 10}점
                </p>
                <p className="text-gray-500 mt-1">
                  일치 자격요건:{' '}
                  {matchDetail.qualifications?.matchedQuals?.length
                    ? matchDetail.qualifications.matchedQuals.join(', ')
                    : '없음'}
                </p>
              </div>

              <div className="border border-gray-200 rounded-xl p-4">
                <h3 className="font-semibold mb-2">의미 기반 점수</h3>
                <p>
                  담당업무 유사도 점수: {matchDetail.semantic?.responsibilityScore ?? 0}점
                </p>
                <p>
                  자격요건 유사도 점수: {matchDetail.semantic?.qualificationScore ?? 0}점
                </p>
              </div>

              <div className="border border-gray-200 rounded-xl p-4">
                <h3 className="font-semibold mb-2">미충족 조건</h3>
                <p className="text-gray-500">
                  {job.unmetConditions?.length ? job.unmetConditions.join(', ') : '없음'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}