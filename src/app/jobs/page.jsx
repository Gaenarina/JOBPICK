'use client'

import { useMemo, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import {
  addResumes,
  getBookmarks,
  getResumes,
  pushRecentJob,
  toggleBookmark,
} from '@/lib/userStorage'

const MATCH_API_URL = process.env.NEXT_PUBLIC_MATCH_API_URL || 'http://localhost:8000/process-resume'

function getJobKey(job) {
  return String(job?.id || job?.jobId || '')
}

function getResumeDocId(resume) {
  return resume?.docId || resume?.resumeId || resume?.id
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

function normalizeJobs(jobs) {
  return (jobs || []).map((job) => {
    const jobId = job.id || job.jobId

    return {
      ...job,
      id: String(jobId || ''),
      jobId: String(jobId || ''),
      title: toDisplayText(job.title, '제목 없음'),
      company: toDisplayText(job.company || job.companyName, '회사명 없음'),
      location: toDisplayText(job.location, ''),
      career: toDisplayText(job.career || job.experience, ''),
      category: toDisplayText(job.category || job.jobCategory, ''),
      salary: toDisplayText(job.salary, ''),
      matchRate: job.matchRate ?? Math.round(Number(job.finalScore || 0)),
    }
  })
}

export default function JobsPage() {
  const { user, isAuthenticated, mounted } = useAuth()
  const router = useRouter()

  const [jobs, setJobs] = useState([])
  const [isLoadingJobs, setIsLoadingJobs] = useState(false)

  const [selectedRegion, setSelectedRegion] = useState('전체')
  const [selectedCategory, setSelectedCategory] = useState('전체')
  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [aiMatched, setAiMatched] = useState(false)
  const [isMatching, setIsMatching] = useState(false)
  const [bookmarkIds, setBookmarkIds] = useState([])
  const [resumes, setResumes] = useState([])
  const [matchedJobs, setMatchedJobs] = useState([])

  const resumeUserId = user?.uid || user?.id || ''

  useEffect(() => {
    if (!mounted) return

    const bookmarks = getBookmarks(resumeUserId)
    const savedResumes = getResumes(resumeUserId)

    setBookmarkIds(bookmarks.map((item) => getJobKey(item)))
    setResumes(savedResumes)

    try {
      const savedMatchedJobs = localStorage.getItem('jobpick_matched_jobs')

      if (savedMatchedJobs) {
        const parsed = JSON.parse(savedMatchedJobs)
        const normalized = normalizeJobs(parsed)

        if (normalized.length > 0) {
          setMatchedJobs(normalized)
          setAiMatched(true)
        }
      }
    } catch (error) {
      console.error('저장된 매칭 결과 불러오기 실패:', error)
    }
  }, [mounted, resumeUserId])

  useEffect(() => {
    if (!mounted || !isAuthenticated) return

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
        alert(error.message || '공고 목록을 불러오지 못했습니다.')
      } finally {
        setIsLoadingJobs(false)
      }
    }

    fetchJobs()
  }, [mounted, isAuthenticated])

  const filteredJobs = useMemo(() => {
    const keyword = searchQuery.trim().toLowerCase()

    return jobs.filter((job) => {
      const location = String(job.location || '')
      const category = String(job.category || '')
      const title = String(job.title || '').toLowerCase()
      const company = String(job.company || '').toLowerCase()

      const regionMatched =
        selectedRegion === '전체' ||
        location.startsWith(selectedRegion)

      const categoryMatched =
        selectedCategory === '전체' ||
        category === selectedCategory

      const searchMatched =
        !keyword ||
        title.includes(keyword) ||
        company.includes(keyword) ||
        category.toLowerCase().includes(keyword)

      return regionMatched && categoryMatched && searchMatched
    })
  }, [jobs, selectedRegion, selectedCategory, searchQuery])

  const shownJobs = useMemo(() => {
    if (aiMatched) return matchedJobs
    return filteredJobs
  }, [aiMatched, matchedJobs, filteredJobs])

  const runAiMatching = async () => {
    if (!resumes.length) {
      alert('먼저 이력서를 첨부하거나 등록한 이력서를 선택해주세요.')
      return
    }

    const resumeId = getResumeDocId(resumes[0])

    if (!resumeId) {
      alert('이력서 문서 ID를 찾을 수 없습니다. 이력서를 다시 업로드해주세요.')
      return
    }

    setIsMatching(true)

    try {
      const res = await fetch(MATCH_API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          docId: resumeId,
          userId: user?.uid || user?.id || '',
          force: true,
        }),
      })

      const data = await res.json()

      console.log('AI 매칭 응답:', data)

      if (!res.ok) {
        throw new Error(data.error || 'AI 매칭 실패')
      }

      const matches = normalizeJobs(data.topFitMatches || data.matches || [])

      console.log('AI 매칭 결과:', matches)

      if (!matches.length) {
        setMatchedJobs([])
        localStorage.removeItem('jobpick_matched_jobs')
        setAiMatched(true)
        alert('매칭 결과가 비어 있습니다. Firestore job_postings 데이터나 백엔드 반환값을 확인해주세요.')
        return
      }

      setMatchedJobs(matches)
      localStorage.setItem('jobpick_matched_jobs', JSON.stringify(matches))
      setAiMatched(true)
    } catch (error) {
      console.error(error)
      alert(error.message || 'AI 매칭 중 오류가 발생했습니다.')
    } finally {
      setIsMatching(false)
    }
  }

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    setSearchQuery(searchInput)
  }

  const handleUploadResume = async (e) => {
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

    const dateStr = new Date()
      .toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' })
      .replace(/\. /g, '.')
      .replace(/\.$/, '')

    try {
      const uploadedResumes = []

      for (const file of validFiles) {
        const formData = new FormData()
        formData.append('file', file)

        const res = await fetch('/api/resume/upload', {
          method: 'POST',
          body: formData,
        })

        const data = await res.json()

        if (!res.ok) {
          throw new Error(data.error || '이력서 업로드 실패')
        }

        const docId = data.docId || data.resumeId || data.id

        if (!docId) {
          throw new Error('업로드 응답에서 이력서 문서 ID를 찾을 수 없습니다.')
        }

        uploadedResumes.push({
          id: docId,
          docId,
          name: file.name,
          size: Math.round(file.size / 1024) + ' KB',
          date: dateStr,
        })
      }

      setResumes(addResumes(uploadedResumes, resumeUserId))
      alert('이력서 첨부가 완료되었습니다.')
    } catch (error) {
      console.error(error)
      alert(error.message || '이력서 첨부 중 오류가 발생했습니다.')
    } finally {
      e.target.value = ''
    }
  }

  const handleViewJob = (job) => {
    pushRecentJob(job)
    router.push(`/jobs/${job.id || job.jobId}`)
  }

  const handleToggleBookmark = (job) => {
    const next = toggleBookmark(job, resumeUserId)
    setBookmarkIds(next.map((item) => getJobKey(item)))
  }

  const handleResetMatching = () => {
    localStorage.removeItem('jobpick_matched_jobs')
    setMatchedJobs([])
    setAiMatched(false)
  }

  if (!mounted || !isAuthenticated) {
    return (
      <main className="max-w-3xl mx-auto p-8 flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin w-10 h-10 border-2 border-primary border-t-transparent rounded-full" />
      </main>
    )
  }

  const name = user?.name || user?.displayName || '회원'

  const btnPrimary = 'px-7 py-3 rounded-xl font-medium transition-colors disabled:opacity-60 bg-primary text-white hover:bg-primary-dark'
  const btnInactive = 'px-7 py-3 rounded-xl font-medium transition-colors disabled:opacity-60 bg-slate-100 text-gray-700 hover:bg-slate-200'
  const btnSecondaryActive = 'px-5 py-3 rounded-xl font-medium transition-colors bg-primary text-white hover:bg-primary-dark'
  const btnSecondaryInactive = 'px-5 py-3 rounded-xl font-medium transition-colors bg-slate-100 text-gray-700 hover:bg-slate-200'

  return (
    <main className="max-w-5xl mx-auto p-4 md:p-8">
      <section className="mb-8">
        <h1 className="text-2xl md:text-4xl font-bold mb-4 md:mb-6">채용 공고</h1>

        <div className="rounded-2xl bg-white border border-gray-200 p-4 md:p-6">
          <form onSubmit={handleSearchSubmit} className="mb-4 md:mb-6 flex gap-2">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="포지션, 회사명, 키워드 검색"
              className="flex-1 bg-slate-100 rounded-xl px-4 md:px-5 py-3 md:py-4 text-gray-700 text-base md:text-xl outline-none border border-transparent focus:border-primary"
            />
            <button type="submit" className="px-5 py-3 rounded-xl bg-slate-700 text-white">
              검색
            </button>
          </form>

          <div className="flex flex-wrap gap-3">
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              className="px-5 py-3 rounded-xl bg-slate-100 text-gray-700"
            >
              <option value="전체">지역별</option>
              <option value="서울">서울</option>
              <option value="경기">경기</option>
              <option value="인천">인천</option>
              <option value="부산">부산</option>
              <option value="대구">대구</option>
              <option value="광주">광주</option>
              <option value="대전">대전</option>
              <option value="울산">울산</option>
              <option value="세종">세종</option>
              <option value="강원">강원</option>
              <option value="충북">충북</option>
              <option value="충남">충남</option>
              <option value="전북">전북</option>
              <option value="전남">전남</option>
              <option value="경북">경북</option>
              <option value="경남">경남</option>
              <option value="제주">제주</option>
            </select>

            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-5 py-3 rounded-xl bg-slate-100 text-gray-700"
            >
              <option value="전체">직업별</option>
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

            <button
              type="button"
              onClick={runAiMatching}
              disabled={isMatching}
              className={aiMatched ? btnPrimary : btnInactive}
            >
              {isMatching ? '매칭 중' : 'AI매칭'}
            </button>

            <button
              type="button"
              onClick={handleResetMatching}
              className={!aiMatched ? btnSecondaryActive : btnSecondaryInactive}
            >
              기본 공고 보기
            </button>

            <label className="px-5 py-3 rounded-xl bg-slate-100 text-gray-700 cursor-pointer">
              이력서 첨부
              <input type="file" accept=".pdf,.doc,.docx" multiple className="hidden" onChange={handleUploadResume} />
            </label>
          </div>

          {resumes.length > 0 && (
            <p className="text-sm text-gray-500 mt-3">
              최근 첨부 파일: {resumes[0].name} 외 {resumes.length}개
            </p>
          )}
        </div>
      </section>

      <section className="mt-8">
        <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-2 mb-4">
          <h2 className="text-xl md:text-3xl font-bold">
            {aiMatched ? `${name}님 맞춤 공고` : '추천 공고'}
          </h2>
          <div className="px-4 py-2 bg-slate-100 rounded-xl text-sm text-gray-600 w-fit">
            {aiMatched ? 'AI 매칭 점수순' : 'DB 공고 목록'}
          </div>
        </div>

        {isLoadingJobs && !aiMatched ? (
          <div className="p-8 bg-white border border-gray-200 rounded-2xl text-center">
            <div className="w-10 h-10 border-2 border-gray-200 border-t-primary rounded-full animate-spin mx-auto mb-4" />
            <p>DB 공고를 불러오는 중입니다...</p>
          </div>
        ) : isMatching ? (
          <div className="p-8 bg-white border border-gray-200 rounded-2xl text-center">
            <div className="w-10 h-10 border-2 border-gray-200 border-t-primary rounded-full animate-spin mx-auto mb-4" />
            <p>AI가 조건에 맞는 기업을 찾는 중입니다...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {shownJobs.map((job) => {
              const jobKey = getJobKey(job)

              return (
                <div key={jobKey} className="relative bg-white rounded-2xl p-6 border border-gray-200 min-h-[230px]">
                  <button
                    onClick={() => handleToggleBookmark(job)}
                    className="absolute top-5 right-5 text-xl"
                    aria-label="북마크"
                  >
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

                  <p className="text-base md:text-2xl text-gray-500 mb-2 pr-8">{job.company}</p>

                  <button
                    onClick={() => handleViewJob(job)}
                    className="text-lg md:text-3xl font-semibold mb-4 text-left hover:text-primary transition-colors pr-8"
                  >
                    {job.title}
                  </button>

                  <div className="flex gap-2 mb-2 flex-wrap">
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

                  <div className="mt-4 flex gap-2">
                    <button onClick={() => handleViewJob(job)} className="px-3 py-2 rounded-lg bg-slate-100 text-sm">
                      공고 보기
                    </button>
                  </div>

                  {aiMatched && (
                    <span className="text-4xl md:text-5xl font-bold text-primary absolute right-6 md:right-8 bottom-6">
                      {job.matchRate ?? Math.round(job.finalScore ?? 0)}점{' '}
                      <span className="text-lg md:text-xl text-gray-500 font-medium">적합</span>
                    </span>
                  )}
                </div>
              )
            })}

            {shownJobs.length === 0 && (
              <div className="bg-white rounded-2xl p-8 border border-gray-200 text-center text-gray-500">
                표시할 공고가 없습니다.
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  )
}