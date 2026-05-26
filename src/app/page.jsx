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

const MATCH_API_URL = process.env.NEXT_PUBLIC_MATCH_API_URL || 'http://localhost:8000/process-resume'
const MATCHED_JOBS_STORAGE_PREFIX = 'jobpick_matched_jobs' 

function getJobKey(job) {
  return String(job?.id || job?.jobId || '')
}

function getResumeDocId(resume) {
  return resume?.docId || resume?.resumeId || resume?.id
}

function getMatchedJobsStorageKey(userId, resumeId) {
  return `${MATCHED_JOBS_STORAGE_PREFIX}_${userId || 'anonymous'}_${resumeId || 'unknown'}`
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

function normalizeMatchRate(job) {
  const rawScore =
    job.matchRate ??
    job.finalScore ??
    job.final_score ??
    job.score ??
    job.matchScore ??
    job.match_score ??
    job.similarity ??
    0

  const numberScore = Number(rawScore)

  if (!Number.isFinite(numberScore)) {
    return 0
  }

  if (numberScore > 0 && numberScore <= 1) {
    return Math.round(numberScore * 100)
  }

  return Math.round(numberScore)
}

function normalizeJobs(jobs) {
  return (jobs || []).map((job) => {
    const source = job.jobPosting
      ? {
          ...job.jobPosting,
          ...job,
        }
      : job

    const jobId = source.id || source.jobId || job.id || job.jobId

    return {
      ...source,
      id: String(jobId || ''),
      jobId: String(jobId || ''),
      sourceUrl:
        source.sourceUrl ||
        source.url ||
        source.jobPosting?.sourceUrl ||
        source.meta?.sourceUrl ||
        '',
      title: toDisplayText(source.title, '제목 없음'),
      company: toDisplayText(source.company || source.companyName, '회사명 없음'),
      location: toDisplayText(source.location, ''),
      career: toDisplayText(source.career || source.experience, ''),
      category: toDisplayText(source.category || source.jobCategory, ''),
      salary: toDisplayText(source.salary, ''),
      matchRate: normalizeMatchRate(source),
    }
  })
}

function getTopMatches(jobs, count = 5) {
  return [...(jobs || [])]
    .sort((a, b) => Number(b.matchRate || 0) - Number(a.matchRate || 0))
    .slice(0, count)
}

export default function LandingPage() {
  const router = useRouter()
  const { user, isAuthenticated, mounted, logout } = useAuth()
  const resumeUserId = user?.uid || user?.id || ''

  const [jobs, setJobs] = useState([])
  const [matchedJobs, setMatchedJobs] = useState([])
  const [isLoadingJobs, setIsLoadingJobs] = useState(false)
  const [selectedPopularCategory, setSelectedPopularCategory] = useState('전체')

  const [resumes, setResumes] = useState([])
  const fileInputRef = useRef(null)
  const [showSavedResumes, setShowSavedResumes] = useState(true)
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

  const restoreMatchedJobsFromStorage = (resume) => {
    try {
      const resumeId = getResumeDocId(resume)
      const userId = user?.uid || user?.id || ''

      if (!resumeId) {
        return false
      }

      const storageKey = getMatchedJobsStorageKey(userId, resumeId)
      const savedMatchedJobs = localStorage.getItem(storageKey)

      if (!savedMatchedJobs) {
        return false
      }

      const parsed = JSON.parse(savedMatchedJobs)
      const savedJobs = Array.isArray(parsed) ? parsed : parsed.jobs || []
      const normalized = getTopMatches(normalizeJobs(savedJobs), 5)

      if (normalized.length > 0) {
        setSelectedResume(resume)
        setMatchedJobs(normalized)
        setAnalysisDone(true)
        return true
      }

      return false
    } catch (error) {
      console.error('저장된 매칭 결과 불러오기 실패:', error)
      return false
    }
  }

  const runAiMatchingByResume = async (resume, force = false) => {
    const resumeId = getResumeDocId(resume)

    if (!resumeId) {
      alert('이력서 문서 ID를 찾을 수 없습니다.')
      return
    }

    setSelectedResume(resume)
    setIsAnalyzing(true)
    setAnalysisDone(false)
    setMatchedJobs([])

    try {
      const res = await fetch(MATCH_API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          docId: resumeId,
          userId: user?.uid || user?.id || '',
          force,
        }),
      })

      const data = await res.json()

      console.log('메인 AI 매칭 응답:', data)

      if (!res.ok) {
        throw new Error(data.error || 'AI 매칭 실패')
      }

      const matches = normalizeJobs(data.topFitMatches || data.matches || [])
      const topMatches = getTopMatches(matches, 5)

      setMatchedJobs(topMatches)

      const storageKey = getMatchedJobsStorageKey(user?.uid || user?.id || '', resumeId) 

      localStorage.setItem(
        storageKey, 
        JSON.stringify({
          resumeId,
          jobs: topMatches,
          savedAt: new Date().toISOString(),
        })
      )

      setAnalysisDone(true)

      if (!topMatches.length) {
        alert('매칭 결과가 비어 있습니다. 백엔드 matches 반환값을 확인해주세요.')
      }
    } catch (error) {
      console.error(error)
      alert(error.message || 'AI 매칭 중 오류가 발생했습니다.')
      setAnalysisDone(false)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const checkResumeStatus = async (resume, shouldRunMatching = false) => {
    const resumeId = getResumeDocId(resume)

    if (!resumeId) {
      return null
    }

    try {
      const res = await fetch(`/api/resume/${resumeId}`)
      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.error || '상태 조회 실패')
      }

      const latestStatus = data.status || 'INIT'

      setResumes((prev) =>
        prev.map((item) =>
          getResumeDocId(item) === resumeId
            ? { ...item, status: latestStatus }
            : item
        )
      )

      setSelectedResume((prev) =>
        getResumeDocId(prev) === resumeId
          ? { ...prev, status: latestStatus }
          : prev
      )

      if (latestStatus === 'PROCESSING') {
        setIsAnalyzing(true)
        setAnalysisDone(false)
      }

      if (latestStatus === 'DONE') {
        if (shouldRunMatching) {
          await runAiMatchingByResume({ ...resume, status: latestStatus })
        } else {
          setIsAnalyzing(false)
          setAnalysisDone(false)
        }
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

  const startStatusPolling = (resume) => {
    let count = 0
    const maxCount = 10

    const timer = setInterval(async () => {
      count += 1

      const status = await checkResumeStatus(resume, true)

      if (status === 'DONE' || status === 'FAILED' || count >= maxCount) {
        clearInterval(timer)
      }
    }, 2000)
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
      setMatchedJobs([])

      const formData = new FormData()
      formData.append('file', file)
      formData.append('userId', user?.uid || user?.id || 'anonymous')

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

      const mappedResume = {
        id: docId,
        docId,
        name: file.name,
        size: Math.round(file.size / 1024) + ' KB',
        date: dateStr,
        status: data.status || 'INIT',
      }

      setResumes(addResumes([mappedResume], resumeUserId))
      setShowSavedResumes(true)
      setSelectedResume(mappedResume)

      await runAiMatchingByResume(mappedResume)
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

    const alreadySignedOut = sessionStorage.getItem('jobpick_auto_signed_out')

    if (isAuthenticated && !alreadySignedOut && typeof logout === 'function') {
      sessionStorage.setItem('jobpick_auto_signed_out', 'true')
      logout()
    }
  }, [mounted, isAuthenticated, logout])

  useEffect(() => {
    if (!mounted) return

    const savedResumes = getResumes(resumeUserId) 

    setResumes(savedResumes)
    setBookmarkIds(getBookmarks().map((item) => getJobKey(item)))
    fetchJobs()

    if (savedResumes.length > 0) {
      restoreMatchedJobsFromStorage(savedResumes[0]) 
    }

    const handlePageShow = () => {
      if (savedResumes.length > 0) {
        restoreMatchedJobsFromStorage(savedResumes[0]) 
      }
    }

    window.addEventListener('pageshow', handlePageShow)

    return () => {
      window.removeEventListener('pageshow', handlePageShow)
    }
  }, [mounted, resumeUserId])

  const name = user?.displayName || user?.name || '회원'

  const handleResumeAnalyze = (resume) => {
    const restored = restoreMatchedJobsFromStorage(resume)

    if (restored) {
      return
    }

    runAiMatchingByResume(resume, false)
  }

  const handleDeleteResume = (resumeId) => {
    const next = removeResume(resumeId, resumeUserId)

    setResumes(next)

    const storageKey = getMatchedJobsStorageKey(resumeUserId, resumeId) 
    localStorage.removeItem(storageKey) 

    if (getResumeDocId(selectedResume) === resumeId) {
      setSelectedResume(null)
      setAnalysisDone(false)
      setMatchedJobs([])
    }
  }

  const handleGoJob = (job) => {
    pushRecentJob(job)
    router.push(`/jobs/${job.id || job.jobId}`)
  }

  const handleGoPopularJob = (job) => {
    pushRecentJob(job)

    if (job.sourceUrl) {
      window.open(job.sourceUrl, '_blank', 'noopener,noreferrer')
      return
    }

    alert('원본 공고 링크를 찾을 수 없습니다.')
  }

  const handleToggleBookmark = (job) => {
    const next = toggleBookmark(job)
    setBookmarkIds(next.map((item) => getJobKey(item)))
  }

  const recommendedJobs = matchedJobs.slice(0, 3)

  const popularJobs = jobs
    .filter((job) => {
      if (selectedPopularCategory === '전체') return true
      return job.category === selectedPopularCategory
    })
    .slice(0, 2)

  const handleRematch = (resume) => {
    if (!resume) {
      alert('먼저 이력서를 선택해주세요.')
      return
    }

    runAiMatchingByResume(resume, true)
  }

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
                        getResumeDocId(selectedResume) === getResumeDocId(resume) ? 'border-primary' : 'border-gray-200'
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
                      <button
                        type="button"
                        onClick={() => handleRematch(resume)} 
                        className="px-3 py-2 rounded-lg text-xs font-medium bg-primary text-white hover:bg-primary-dark transition-colors"
                      >
                        재분석
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

                          <div className="flex gap-2 mt-2 flex-wrap">
                            {job.category && (
                              <span className="text-xs px-2 py-1 bg-blue-50 rounded text-blue-600">
                                {job.category}
                              </span>
                            )}

                            {job.location && (
                              <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">
                                {job.location}
                              </span>
                            )}

                            {job.career && (
                              <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">
                                {job.career}
                              </span>
                            )}

                            {job.salary && (
                              <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">
                                {job.salary}
                              </span>
                            )}
                          </div>
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
                            <span className="text-primary font-bold text-lg">{job.matchRate}점</span>
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
          <select
            value={selectedPopularCategory}
            onChange={(e) => setSelectedPopularCategory(e.target.value)}
            className="px-3 py-2 border border-gray-200 rounded-md text-sm bg-white"
          >
            <option value="전체">전체</option>
            <option value="IT/개발">IT/개발</option>
            <option value="디자인">디자인</option>
            <option value="마케팅">마케팅</option>
            <option value="영업·고객상담">영업·고객상담</option>
            <option value="사무·총무">사무·총무</option>
            <option value="교육">교육</option>
            <option value="의료/바이오">의료/바이오</option>
            <option value="운전/운송/배송">운전/운송/배송</option>
            <option value="건축/시설">건축/시설</option>
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
                      onClick={() => handleGoPopularJob(job)}
                      className="font-semibold mb-1 hover:text-primary transition-colors text-left pr-8"
                    >
                      {job.title}
                    </button>

                    <p className="text-sm text-gray-500 mb-2">{job.company}</p>

                    <div className="flex gap-2 flex-wrap">
                      {job.category && (
                        <span className="text-xs px-2 py-1 bg-blue-50 rounded text-blue-600">
                          {job.category}
                        </span>
                      )}

                      {job.location && (
                        <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">
                          {job.location}
                        </span>
                      )}

                      {job.career && (
                        <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">
                          {job.career}
                        </span>
                      )}

                      {job.salary && (
                        <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">
                          {job.salary}
                        </span>
                      )}
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