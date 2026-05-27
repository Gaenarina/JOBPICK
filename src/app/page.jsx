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
import { FileText, Sparkles } from 'lucide-react'

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
  const { user, isAuthenticated, mounted } = useAuth()
  const resumeUserId = user?.uid || user?.id || ''
  const [jobs, setJobs] = useState([])

  const [matchedJobs, setMatchedJobs] = useState([])
  const [matchPage, setMatchPage] = useState(1)
  const matchItemsPerPage = 10
  const [isLoadingJobs, setIsLoadingJobs] = useState(false)
  const [selectedPopularCategory, setSelectedPopularCategory] = useState('전체')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

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
    if (!isAuthenticated) {
      router.push('/login')
      return
    }
    setShowSavedResumes((prev) => !prev)
  }

  const handleNewUploadClick = () => {
    if (!isAuthenticated) {
      router.push('/login')
      return
    }
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

      if (!resumeId) return false

      const storageKey = getMatchedJobsStorageKey(userId, resumeId)
      const savedMatchedJobs = localStorage.getItem(storageKey)

      if (!savedMatchedJobs) return false

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
    setMatchPage(1)

    try {
      const res = await fetch(MATCH_API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          docId: resumeId,
          userId: user?.uid || user?.id || '',
          force: force,
        }),
      })

      const data = await res.json()
      console.log('메인 AI 매칭 응답:', data)

      if (!res.ok) {
        throw new Error(data.error || 'AI 매칭 실패')
      }

      const topMatches = normalizeJobs(data.topFitMatches || data.matches || [])
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
    if (!resumeId) return null

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
    if (!isAuthenticated) {
      router.push('/login')
      e.target.value = ''
      return
    }
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
      startStatusPolling(mappedResume)

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

    const savedResumes = getResumes(resumeUserId)
    setResumes(savedResumes)
    setBookmarkIds(getBookmarks(resumeUserId).map((item) => getJobKey(item)))
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
    if (restored) return
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
    if (!isAuthenticated) {
      router.push('/login')
      return
    }
    const next = toggleBookmark(job, resumeUserId)
    setBookmarkIds(next.map((item) => getJobKey(item)))
  }

  // AI 추천 매칭 리스트 페이징 데이터
  const totalMatchPages = Math.ceil(matchedJobs.length / matchItemsPerPage)
  const matchStartIndex = (matchPage - 1) * matchItemsPerPage
  const matchEndIndex = matchStartIndex + matchItemsPerPage
  const pagedMatchedJobs = matchedJobs.slice(matchStartIndex, matchEndIndex)
  console.log('matchedJobs:', matchedJobs)
console.log('matchedJobs length:', matchedJobs.length)
console.log('totalMatchPages:', totalMatchPages)

  // 인기 커리어 리스트 페이징 데이터
  const filteredJobs = jobs.filter((job) => {
    if (selectedPopularCategory === '전체') return true
    return job.category === selectedPopularCategory
  })
  const totalPages = Math.ceil(filteredJobs.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const popularJobs = filteredJobs.slice(startIndex, endIndex)

  useEffect(() => {
    setCurrentPage(1)
  }, [selectedPopularCategory])

  const handleRematch = (resume) => {
    if (!resume) {
      alert('먼저 이력서를 선택해주세요.')
      return
    }
    runAiMatchingByResume(resume, true)
  }

  return (
    <main className="max-w-5xl mx-auto p-4 md:p-8">
      {isAuthenticated ? (
        <section className="py-6 md:py-8">
          <h1 className="text-2xl md:text-4xl font-bold mb-1">
            안녕하세요, <span className="text-primary">{name}</span> 님!
          </h1>
          <p className="text-gray-500 text-base md:text-lg">AI 기반 이력서/채용공고 매칭 서비스예요.</p>
        </section>
      ) : (
        <section className="text-center py-10 md:py-12">
          <h1 className="text-3xl md:text-5xl font-bold text-primary mb-2">로그인을 해주세요!</h1>
          <p className="text-gray-500 mb-6 text-base md:text-lg">AI 기반 이력서/채용공고 매칭 서비스예요.</p>
          <button
            onClick={handleGetStarted}
            className="px-8 py-3 md:py-4 md:text-lg bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition-colors"
          >
            로그인하고 시작하기
          </button>
        </section>
      )}

      {/* AI 매칭 추천 블록 */}
      <section
        className={`mt-8 md:mt-10 ${
          !isAuthenticated ? 'blur-sm opacity-60 select-none pointer-events-none' : ''
        }`}
      >
        <div className="bg-blue-50 rounded-2xl p-5 md:p-8 border border-blue-200 relative">
          <h2 className="text-2xl md:text-2xl font-bold mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 md:w-6 md:h-6 text-primary" aria-hidden />
            AI 커리어 매칭 분석
          </h2>

          <p className="text-gray-500 text-base md:text-base mb-4">
            로그인 후 이력서를 업로드하면 AI가 분석하여 맞춤 채용공고를 추천해드립니다.
          </p>

          <div className="relative border-2 border-dashed border-gray-200 rounded-xl md:rounded-2xl p-5 md:p-8 bg-white">
            {!isAuthenticated && (
              <div className="absolute inset-0 z-20 flex items-center justify-center">
                <button
                  type="button"
                  onClick={() => router.push('/login')}
                  className="w-full h-full flex flex-col items-center justify-center gap-2 bg-black/30 text-white rounded-2xl"
                  aria-label="로그인 안내"
                >
                  <span className="text-lg font-medium">로그인 후 이용 가능합니다</span>
                  <span className="text-sm underline">로그인하러 가기</span>
                </button>
              </div>
            )}

            <div className="flex flex-wrap gap-3 mb-4">
              <button
                type="button"
                onClick={handleShowSavedClick}
                className={`px-5 py-2.5 rounded-xl text-sm md:text-base font-medium ${
                  showSavedResumes ? 'bg-primary text-white' : 'bg-slate-100 text-gray-700'
                }`}
              >
                등록한 이력서 불러오기
              </button>

              <button
                type="button"
                onClick={handleNewUploadClick}
                className="px-5 py-2.5 rounded-xl text-sm md:text-base font-medium bg-slate-900 text-white"
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

            <p className="text-sm md:text-base text-gray-500 mb-3">
              PDF, DOC, DOCX 파일을 업로드하거나, 등록한 이력서를 선택해 분석해보세요.
            </p>

            {showSavedResumes && (
              <div className="flex flex-col gap-3">
                {resumes.length === 0 ? (
                  <p className="text-sm text-gray-500">
                    등록된 이력서가 없습니다. 새 이력서를 등록해 주세요.
                  </p>
                ) : (
                  resumes.map((resume) => (
                    <div
                      key={resume.id}
                      className={`flex items-center justify-between gap-3 p-4 border rounded-lg bg-white ${
                        getResumeDocId(selectedResume) === getResumeDocId(resume)
                          ? 'border-primary'
                          : 'border-gray-200'
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => (isAuthenticated ? handleResumeAnalyze(resume) : router.push('/login'))}
                        className="flex items-center gap-4 text-left flex-1"
                      >
                        <FileText className="w-6 h-6 text-gray-500" aria-hidden />
                        <div className="flex flex-col">
                          <span className="font-medium">{resume.name}</span>
                          <span className="text-sm text-gray-500">
                            {resume.size} · {resume.date}
                          </span>
                          <span className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-600 w-fit mt-1">
                            {resume.status === 'INIT' && '업로드 완료'}
                            {resume.status === 'PROCESSING' && '분석 중'}
                            {resume.status === 'DONE' && '분석 완료'}
                            {resume.status === 'FAILED' && '실패'}
                          </span>
                        </div>
                      </button>

                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => (isAuthenticated ? handleDeleteResume(resume.id) : router.push('/login'))}
                          className="text-xs px-2 py-1 rounded bg-red-50 text-red-600 h-fit"
                        >
                          삭제
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRematch(resume)} 
                          className="px-3 py-1 rounded-lg text-xs font-medium bg-primary text-white hover:bg-primary-dark transition-colors"
                        >
                          재분석
                        </button>
                      </div>
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

          {/* AI 추천 공고 목록 노출 영역 */}
          {analysisDone && (
            <div className="mt-6 bg-white rounded-xl md:rounded-2xl p-5 md:p-6 border border-blue-200">
              <p className="text-base md:text-base text-gray-600 mb-3">
                {name} 님의 이력서 기준으로 아래 채용 공고를 추천드려요.
              </p>

              <div className="flex flex-col gap-4">
                {pagedMatchedJobs.length === 0 ? (
                  <p className="text-sm md:text-base text-gray-500">표시할 추천 공고가 없습니다.</p>
                ) : (
                  pagedMatchedJobs.map((job) => {
                    const jobKey = getJobKey(job)

                    return (
                      <div
                        key={jobKey}
                        className="flex items-center justify-between gap-3 border border-gray-200 rounded-xl p-5 md:p-6"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="text-sm md:text-base text-gray-500 mb-1">{job.company}</p>
                          <button
                            onClick={() => handleGoJob(job)}
                            className="font-semibold text-base md:text-lg text-left hover:text-primary transition-colors block"
                          >
                            {job.title}
                          </button>
                          <div className="flex gap-2 mt-2 flex-wrap">
                            {job.category && (
                              <span className="text-xs md:text-sm px-2 py-1 bg-blue-50 rounded text-blue-600">
                                {job.category}
                              </span>
                            )}
                            {job.location && (
                              <span className="text-xs md:text-sm px-2 py-1 bg-slate-100 rounded text-gray-500">
                                {job.location}
                              </span>
                            )}
                            {job.career && (
                              <span className="text-xs md:text-sm px-2 py-1 bg-slate-100 rounded text-gray-500">
                                {job.career}
                              </span>
                            )}
                            {job.salary && (
                              <span className="text-xs md:text-sm px-2 py-1 bg-slate-100 rounded text-gray-500">
                                {job.salary}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-3 flex-shrink-0">
                          {job.matchRate > 0 && (
                            <span className="text-primary font-bold text-lg md:text-xl whitespace-nowrap">
                              {job.matchRate}점
                            </span>
                          )}
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
                        </div>
                      </div>
                    )
                  })
                )}
              </div>

              {/* AI 매칭결과 전용 페이지네이션 */}
              {totalMatchPages > 1 && (
                <div className="flex justify-center items-center gap-2 mt-6">
                  {Array.from({ length: totalMatchPages }, (_, i) => i + 1).map((page) => (
                    <button
                      key={page}
                      onClick={() => setMatchPage(page)}
                      className={`min-w-[40px] h-10 px-3 rounded-lg text-sm font-medium transition-colors ${
                        matchPage === page
                          ? 'bg-primary text-white'
                          : 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      {page}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {isAuthenticated && (
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() => router.push('/dashboard')}
                className="px-6 py-2.5 md:py-3 md:text-base bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition-colors"
              >
                채용정보로 이동
              </button>
            </div>
          )}
        </div>
      </section>

      {/* 인기 커리어 영역 */}
      <section className="mt-10 md:mt-12">
        <h2 className="text-2xl md:text-3xl font-bold mb-4 md:mb-6">인기 커리어</h2>

        <div className="mb-4">
          <select
            value={selectedPopularCategory}
            onChange={(e) => setSelectedPopularCategory(e.target.value)}
            className="px-4 py-3 border border-gray-200 rounded-xl text-sm md:text-base bg-white w-full sm:w-auto min-h-[48px]"
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
          <div className="p-8 md:p-10 bg-white rounded-2xl border border-gray-200 text-center">
            <div className="w-10 h-10 border-2 border-gray-200 border-t-primary rounded-full animate-spin mx-auto mb-4" />
            <p className="text-sm md:text-base text-gray-500">DB 공고를 불러오는 중입니다...</p>
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-4 md:gap-6">
              {popularJobs.length === 0 ? (
                <div className="bg-white rounded-2xl p-6 md:p-8 border border-gray-200 text-sm md:text-base text-gray-500">
                  표시할 공고가 없습니다.
                </div>
              ) : (
                popularJobs.map((job) => {
                  const jobKey = getJobKey(job)

                  return (
                    <div key={jobKey} className="relative bg-white rounded-2xl p-6 md:p-8 shadow-sm border border-gray-200">
                      <button onClick={() => handleToggleBookmark(job)} className="absolute top-5 right-5 md:top-6 md:right-6" aria-label="북마크">
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
                        className="font-bold text-lg md:text-2xl mb-2 hover:text-primary transition-colors text-left pr-10 block"
                      >
                        {job.title}
                      </button>

                      <p className="text-base md:text-lg text-gray-500 mb-3">{job.company}</p>

                      <div className="flex gap-2 flex-wrap">
                        {job.category && (
                          <span className="text-xs md:text-sm px-2 py-1 bg-blue-50 rounded text-blue-600">
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

            {/* 인기 커리어 전용 페이지네이션 */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center gap-2 mt-6">
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page)}
                    className={`min-w-[40px] h-10 px-3 rounded-lg text-sm font-medium transition-colors ${
                      currentPage === page
                        ? 'bg-primary text-white'
                        : 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    {page}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </section>
    </main>
  )
}