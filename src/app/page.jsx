'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import {
  addResumes,
  getBookmarks,
  getResumes,
  pushRecentJob,
  removeResume,
  toggleBookmark,
} from '@/lib/userStorage'

function getJobKey(job) {
  return String(job?.id || job?.jobId || '')
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

function normalizeJobs(jobs) {
  return (jobs || []).map((job) => {
    const jobId = job.id || job.jobId

    return {
      ...job,
      id: String(jobId || ''),
      jobId: String(jobId || ''),
      title: toDisplayText(job.title, '제목 없음'),
      company: toDisplayText(job.company, '회사명 없음'),
      location: toDisplayText(job.location, '지역 미정'),
      career: toDisplayText(job.career, '경력 미정'),
      category: toDisplayText(job.category, '직무 미정'),
      salary: toDisplayText(job.salary, '급여 미정'),
      matchRate: job.matchRate ?? Math.round(Number(job.finalScore || 0)),
    }
  })
}

export default function LandingPage() {
  const router = useRouter()
  const { user, isAuthenticated, mounted } = useAuth()

  const [jobs, setJobs] = useState([])
  const [isLoadingJobs, setIsLoadingJobs] = useState(false)

  const [resumes, setResumes] = useState([])
  const fileInputRef = useRef(null)
  const [showSavedResumes, setShowSavedResumes] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisDone, setAnalysisDone] = useState(false)
  const [selectedResume, setSelectedResume] = useState(null)
  const [bookmarkIds, setBookmarkIds] = useState([])

  const handleGetStarted = () => {
    router.push('/login')
  }

  const handleShowSavedClick = () => {
    setShowSavedResumes((prev) => !prev)
  }

  const handleNewUploadClick = () => {
    fileInputRef.current?.click()
  }

  const checkResumeStatus = async (resumeId) => {
    try {
      const res = await fetch(`/api/resume/${resumeId}`)
      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.error || '상태 조회 실패')
      }

      const latestStatus = data.status || 'INIT'

      setResumes((prev) =>
        prev.map((resume) =>
          resume.id === resumeId
            ? { ...resume, status: latestStatus }
            : resume
        )
      )

      setSelectedResume((prev) =>
        prev?.id === resumeId
          ? { ...prev, status: latestStatus }
          : prev
      )

      if (latestStatus === 'PROCESSING') {
        setIsAnalyzing(true)
        setAnalysisDone(false)
      }

      if (latestStatus === 'DONE') {
        setIsAnalyzing(false)
        setAnalysisDone(true)
      }

      if (latestStatus === 'FAILED') {
        setIsAnalyzing(false)
        setAnalysisDone(false)
      }

      return latestStatus
    } catch (error) {
      console.error(error)
      return null
    }
  }

  const startStatusPolling = (resumeId) => {
    let count = 0
    const maxCount = 10

    const timer = setInterval(async () => {
      count += 1

      const status = await checkResumeStatus(resumeId)

      if (status === 'DONE' || status === 'FAILED' || count >= maxCount) {
        clearInterval(timer)
      }
    }, 2000)
  }

  const fetchJobs = async () => {
    setIsLoadingJobs(true)

    try {
      const res = await fetch('/api/job-postings', {
        cache: 'no-store',
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.error || '공고 목록 불러오기 실패')
      }

      setJobs(normalizeJobs(data.jobs || []))
    } catch (error) {
      console.error(error)
    } finally {
      setIsLoadingJobs(false)
    }
  }

  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files || [])
    if (!files.length) return

    const validTypes = ['.pdf', '.doc', '.docx']
    const validFiles = files.filter((file) => {
      const ext = '.' + file.name.split('.').pop().toLowerCase()
      return validTypes.includes(ext)
    })

    if (!validFiles.length) {
      alert('PDF, DOC, DOCX 파일만 업로드 가능합니다.')
      e.target.value = ''
      return
    }

    const file = validFiles[0]

    try {
      setIsAnalyzing(true)
      setAnalysisDone(false)

      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch('/api/resume/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.error || '업로드 실패')
      }

      const dateStr = new Date()
        .toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' })
        .replace(/\. /g, '.')
        .replace(/\.$/, '')

      const docId = data.docId || data.resumeId || data.id || String(Date.now())

      const mapped = [
        {
          id: docId,
          docId,
          name: file.name,
          size: Math.round(file.size / 1024) + ' KB',
          date: dateStr,
          status: data.status || 'INIT',
        },
      ]

      setResumes(addResumes(mapped))
      setShowSavedResumes(true)
      setSelectedResume(mapped[0])

      startStatusPolling(mapped[0].id)
    } catch (error) {
      console.error(error)
      alert(error.message || '업로드 중 오류가 발생했습니다.')
      setIsAnalyzing(false)
    } finally {
      e.target.value = ''
    }
  }

  useEffect(() => {
    if (!mounted) return

    setResumes(getResumes())
    setBookmarkIds(getBookmarks().map((item) => getJobKey(item)))
    fetchJobs()
  }, [mounted])

  const name = user?.displayName || user?.name || '회원'

  const handleResumeAnalyze = (resume) => {
    setSelectedResume(resume)
    setAnalysisDone(false)
    setIsAnalyzing(true)

    setTimeout(() => {
      setIsAnalyzing(false)
      setAnalysisDone(true)
    }, 1000)
  }

  const handleDeleteResume = (resumeId) => {
    const next = removeResume(resumeId)

    setResumes(next)

    if (selectedResume?.id === resumeId) {
      setSelectedResume(null)
      setAnalysisDone(false)
    }
  }

  const handleGoJob = (job) => {
    pushRecentJob(job)
    router.push(`/jobs/${job.id || job.jobId}`)
  }

  const handleToggleBookmark = (job) => {
    const next = toggleBookmark(job)
    setBookmarkIds(next.map((item) => getJobKey(item)))
  }

  const recommendedJobs = jobs.slice(0, 3)
  const popularJobs = jobs.slice(0, 2)

  return (
    <main className="max-w-3xl mx-auto p-8">
      {isAuthenticated ? (
        <section className="py-8">
          <h1 className="text-2xl font-bold mb-1">
            안녕하세요, <span className="text-primary">{name}</span> 님!
          </h1>
          <p className="text-gray-500">AI 기반 이력서/채용공고 매칭 서비스예요.</p>
        </section>
      ) : (
        <section className="text-center py-12">
          <h1 className="text-3xl font-bold text-primary mb-2">로그인을 해주세요!</h1>
          <p className="text-gray-500 mb-6">AI 기반 이력서/채용공고 매칭 서비스예요.</p>
          <button
            onClick={handleGetStarted}
            className="px-8 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors"
          >
            로그인하고 시작하기
          </button>
        </section>
      )}

      <section className="mt-8">
        <div className="bg-blue-50 rounded-xl p-6 border border-blue-200">
          <h2 className="text-lg font-semibold mb-4">⭐ AI 커리어 매칭 분석</h2>
          <p className="text-gray-500 text-sm mb-4">
            로그인 후 이력서를 업로드하면 AI가 분석하여 맞춤 채용공고를 추천해드립니다.
          </p>

          <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 bg-white">
            <div className="flex flex-wrap gap-3 mb-4">
              <button
                type="button"
                onClick={handleShowSavedClick}
                className={`px-4 py-2 rounded-lg text-sm font-medium ${
                  showSavedResumes ? 'bg-primary text-white' : 'bg-slate-100 text-gray-700'
                }`}
              >
                등록한 이력서 불러오기
              </button>

              <button
                type="button"
                onClick={handleNewUploadClick}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-slate-900 text-white"
              >
                새 이력서 등록하기
              </button>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.doc,.docx"
                multiple
                className="hidden"
                onChange={handleFileSelect}
              />
            </div>

            <p className="text-sm text-gray-500 mb-3">
              PDF, DOC, DOCX 파일을 업로드하거나, 등록한 이력서를 선택해 분석해보세요.
            </p>

            {showSavedResumes && (
              <div className="flex flex-col gap-3">
                {resumes.length === 0 ? (
                  <p className="text-sm text-gray-500">등록된 이력서가 없습니다. 새 이력서를 등록해 주세요.</p>
                ) : (
                  resumes.map((resume) => (
                    <div
                      key={resume.id}
                      className={`flex items-center justify-between gap-3 p-4 border rounded-lg bg-white ${
                        selectedResume?.id === resume.id ? 'border-primary' : 'border-gray-200'
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => handleResumeAnalyze(resume)}
                        className="flex items-center gap-4 text-left flex-1"
                      >
                        <span className="text-2xl">📄</span>

                        <div className="flex flex-col">
                          <span className="font-medium">{resume.name}</span>
                          <span className="text-sm text-gray-500">
                            {resume.size} · {resume.date}
                          </span>

                          <span className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-600">
                            {resume.status === 'INIT' && '업로드 완료'}
                            {resume.status === 'PROCESSING' && '분석 중'}
                            {resume.status === 'DONE' && '분석 완료'}
                            {resume.status === 'FAILED' && '실패'}
                          </span>
                        </div>
                      </button>

                      <button
                        type="button"
                        onClick={() => handleDeleteResume(resume.id)}
                        className="text-xs px-2 py-1 rounded bg-red-50 text-red-600"
                      >
                        삭제
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}

            {isAnalyzing && (
              <div className="mt-4 p-4 bg-white/80 rounded-lg flex items-center gap-3 text-sm text-gray-700">
                <div className="w-5 h-5 border-2 border-gray-200 border-t-primary rounded-full animate-spin" />
                <span>AI가 이력서를 분석하고 있어요...</span>
              </div>
            )}
          </div>

          {analysisDone && (
            <div className="mt-6 bg-white rounded-xl p-4 border border-blue-200">
              <p className="text-sm text-gray-600 mb-2">
                {name} 님의 이력서 기준으로 아래 채용 공고를 추천드려요.
              </p>

              <div className="flex flex-col gap-3">
                {recommendedJobs.length === 0 ? (
                  <p className="text-sm text-gray-500">
                    표시할 추천 공고가 없습니다.
                  </p>
                ) : (
                  recommendedJobs.map((job) => {
                    const jobKey = getJobKey(job)

                    return (
                      <div
                        key={jobKey}
                        className="flex items-center justify-between gap-3 border border-gray-200 rounded-lg p-4"
                      >
                        <div>
                          <p className="text-xs text-gray-500 mb-1">{job.company}</p>
                          <button
                            onClick={() => handleGoJob(job)}
                            className="font-medium text-sm text-left hover:text-primary transition-colors"
                          >
                            {job.title}
                          </button>
                        </div>

                        <div className="flex items-center gap-3">
                          <button onClick={() => handleToggleBookmark(job)} aria-label="북마크">
                            <svg
                              width="22"
                              height="22"
                              viewBox="0 0 24 24"
                              fill={bookmarkIds.includes(jobKey) ? '#2563eb' : '#ffffff'}
                              xmlns="http://www.w3.org/2000/svg"
                            >
                              <path
                                d="M6 3.75C6 3.33579 6.33579 3 6.75 3H17.25C17.6642 3 18 3.33579 18 3.75V21L12 16.5L6 21V3.75Z"
                                stroke={bookmarkIds.includes(jobKey) ? '#2563eb' : '#94a3b8'}
                                strokeWidth="1.8"
                                strokeLinejoin="round"
                              />
                            </svg>
                          </button>

                          {job.matchRate > 0 && (
                            <span className="text-primary font-bold text-lg">{job.matchRate}%</span>
                          )}
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            </div>
          )}

          {isAuthenticated && (
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() => router.push('/dashboard')}
                className="px-5 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors"
              >
                채용정보로 이동
              </button>
            </div>
          )}
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold mb-4">인기 커리어</h2>

        <div className="mb-4">
          <select className="px-3 py-2 border border-gray-200 rounded-md text-sm bg-white">
            <option>IT/개발</option>
          </select>
        </div>

        {isLoadingJobs ? (
          <div className="p-6 bg-white rounded-lg border border-gray-200 text-center">
            <div className="w-8 h-8 border-2 border-gray-200 border-t-primary rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-500">DB 공고를 불러오는 중입니다...</p>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {popularJobs.length === 0 ? (
              <div className="bg-white rounded-lg p-5 border border-gray-200 text-sm text-gray-500">
                표시할 공고가 없습니다.
              </div>
            ) : (
              popularJobs.map((job) => {
                const jobKey = getJobKey(job)

                return (
                  <div key={jobKey} className="relative bg-white rounded-lg p-5 shadow-sm border border-gray-200">
                    <button onClick={() => handleToggleBookmark(job)} className="absolute top-4 right-4" aria-label="북마크">
                      <svg
                        width="22"
                        height="22"
                        viewBox="0 0 24 24"
                        fill={bookmarkIds.includes(jobKey) ? '#2563eb' : '#ffffff'}
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path
                          d="M6 3.75C6 3.33579 6.33579 3 6.75 3H17.25C17.6642 3 18 3.33579 18 3.75V21L12 16.5L6 21V3.75Z"
                          stroke={bookmarkIds.includes(jobKey) ? '#2563eb' : '#94a3b8'}
                          strokeWidth="1.8"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </button>

                    <button
                      onClick={() => handleGoJob(job)}
                      className="font-semibold mb-1 hover:text-primary transition-colors text-left pr-8"
                    >
                      {job.title}
                    </button>

                    <p className="text-sm text-gray-500 mb-2">{job.company}</p>

                    <div className="flex gap-2 flex-wrap">
                      <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">{job.career}</span>
                      <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">{job.location}</span>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        )}
      </section>
    </main>
  )
}