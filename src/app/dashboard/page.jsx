'use client'

import { useMemo, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '../context/AuthContext'
import { addResumes, getApplications, getBookmarks, getResumes, pushRecentJob, toggleBookmark, upsertApplication } from '../lib/userStorage'
import { DASHBOARD_JOBS } from '../lib/jobs'

export default function DashboardPage() {
  const { user, isAuthenticated, mounted } = useAuth()
  const router = useRouter()
  const [selectedRegion, setSelectedRegion] = useState('전체')
  const [selectedCategory, setSelectedCategory] = useState('전체')
  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [aiMatched, setAiMatched] = useState(false)
  const [isMatching, setIsMatching] = useState(false)
  const [bookmarkIds, setBookmarkIds] = useState([])
  const [appliedMap, setAppliedMap] = useState({})
  const [resumes, setResumes] = useState([])

  useEffect(() => {
    if (mounted && !isAuthenticated) {
      router.replace('/login')
    }
  }, [mounted, isAuthenticated, router])

  useEffect(() => {
    if (!mounted) return
    const bookmarks = getBookmarks()
    const applications = getApplications()
    const savedResumes = getResumes()
    setBookmarkIds(bookmarks.map((item) => item.id))
    setResumes(savedResumes)
    setAppliedMap(
      applications.reduce((acc, item) => {
        acc[item.jobId] = item
        return acc
      }, {})
    )
  }, [mounted])

  const filteredJobs = useMemo(() => {
    const keyword = searchQuery.trim().toLowerCase()
    return DASHBOARD_JOBS.filter((job) => {
      const regionMatched = selectedRegion === '전체' || job.location.startsWith(selectedRegion)
      const categoryMatched = selectedCategory === '전체' || job.category === selectedCategory
      const searchMatched =
        !keyword ||
        job.title.toLowerCase().includes(keyword) ||
        job.company.toLowerCase().includes(keyword) ||
        job.category.toLowerCase().includes(keyword)
      return regionMatched && categoryMatched && searchMatched
    })
  }, [selectedRegion, selectedCategory, searchQuery])

  const shownJobs = useMemo(() => {
    if (!aiMatched) return filteredJobs
    return [...filteredJobs].sort((a, b) => b.matchRate - a.matchRate)
  }, [aiMatched, filteredJobs])

  const runAiMatching = () => {
    setIsMatching(true)
    setTimeout(() => {
      setIsMatching(false)
      setAiMatched(true)
    }, 1000)
  }

  const runSearch = () => {
    setSearchQuery(searchInput)
  }

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    runSearch()
  }

  const handleUploadResume = (e) => {
    const files = Array.from(e.target.files || [])
    if (!files.length) return

    const validTypes = ['.pdf', '.doc', '.docx']
    const validFiles = files.filter((f) => {
      const ext = '.' + f.name.split('.').pop().toLowerCase()
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
    const mapped = validFiles.map((f) => ({
      id: Date.now() + Math.random(),
      name: f.name,
      size: Math.round(f.size / 1024) + ' KB',
      date: dateStr,
    }))

    setResumes(addResumes(mapped))
    e.target.value = ''
  }

  const handleViewJob = (job) => {
    pushRecentJob(job)
    router.push(`/jobs/${job.id}`)
  }

  const handleToggleBookmark = (job) => {
    const next = toggleBookmark(job)
    setBookmarkIds(next.map((item) => item.id))
  }

  const handleApply = (job) => {
    const status = '검토 중'
    const application = {
      jobId: job.id,
      company: job.company,
      title: job.title,
      appliedAt: new Date().toLocaleDateString('ko-KR'),
      status,
    }
    upsertApplication(application)
    setAppliedMap((prev) => ({ ...prev, [job.id]: application }))
    alert('지원이 완료되었습니다.')
  }

  if (!mounted || !isAuthenticated) {
    return (
      <main className="max-w-3xl mx-auto p-8 flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin w-10 h-10 border-2 border-primary border-t-transparent rounded-full" />
      </main>
    )
  }

  const name = user?.name || '회원'

  return (
    <main className="max-w-5xl mx-auto p-6 sm:p-8">
      <section className="mb-8">
        <h1 className="text-4xl font-bold mb-6">채용 정보</h1>
        <div className="rounded-2xl bg-white border border-gray-200 p-6">
          <form onSubmit={handleSearchSubmit} className="mb-6 flex gap-2">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="포지션, 회사명, 키워드 검색"
              className="flex-1 bg-slate-100 rounded-xl px-5 py-4 text-gray-700 text-xl outline-none border border-transparent focus:border-primary"
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
              <option value="부산">부산</option>
            </select>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-5 py-3 rounded-xl bg-slate-100 text-gray-700"
            >
              <option value="전체">직업별</option>
              <option value="개발·데이터">개발·데이터</option>
              <option value="사무·총무">사무·총무</option>
              <option value="영업·고객상담">영업·고객상담</option>
              <option value="마케팅·광고">마케팅·광고</option>
            </select>
            <button
              type="button"
              onClick={runAiMatching}
              className="px-7 py-3 rounded-xl bg-primary text-white font-medium hover:bg-primary-dark transition-colors"
            >
              AI매칭
            </button>
            <label className="px-5 py-3 rounded-xl bg-slate-100 text-gray-700 cursor-pointer">
              이력서 첨부
              <input type="file" accept=".pdf,.doc,.docx" multiple className="hidden" onChange={handleUploadResume} />
            </label>
          </div>
          {resumes.length > 0 && (
            <p className="text-sm text-gray-500 mt-3">최근 첨부 파일: {resumes[0].name} 외 {resumes.length}개</p>
          )}
        </div>
      </section>

      <section className="mt-8">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-3xl font-bold">{aiMatched ? `${name}님 맞춤 공고` : '추천 공고'}</h2>
          <div className="px-4 py-2 bg-slate-100 rounded-xl text-sm text-gray-600">업데이트 순</div>
        </div>
        {isMatching ? (
          <div className="p-8 bg-white border border-gray-200 rounded-2xl text-center">
            <div className="w-10 h-10 border-2 border-gray-200 border-t-primary rounded-full animate-spin mx-auto mb-4" />
            <p>AI가 조건에 맞는 기업을 찾는 중입니다...</p>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {shownJobs.map((job) => (
              <div key={job.id} className="relative bg-white rounded-2xl p-6 border border-gray-200">
                <button
                  onClick={() => handleToggleBookmark(job)}
                  className="absolute top-5 right-5 text-xl"
                  aria-label="북마크"
                >
                  <svg width="22" height="22" viewBox="0 0 24 24" fill={bookmarkIds.includes(job.id) ? '#2563eb' : '#ffffff'} xmlns="http://www.w3.org/2000/svg">
                    <path
                      d="M6 3.75C6 3.33579 6.33579 3 6.75 3H17.25C17.6642 3 18 3.33579 18 3.75V21L12 16.5L6 21V3.75Z"
                      stroke={bookmarkIds.includes(job.id) ? '#2563eb' : '#94a3b8'}
                      strokeWidth="1.8"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
                <p className="text-2xl text-gray-500 mb-2">{job.company}</p>
                <button onClick={() => handleViewJob(job)} className="text-3xl font-semibold mb-4 text-left hover:text-primary transition-colors">
                  {job.title}
                </button>
                <div className="flex gap-2 mb-2 flex-wrap">
                  <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">{job.location}</span>
                  <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">{job.career}</span>
                  <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">{job.category}</span>
                </div>
                <div className="mt-4 flex gap-2">
                  <button onClick={() => handleViewJob(job)} className="px-3 py-2 rounded-lg bg-slate-100 text-sm">
                    공고 보기
                  </button>
                  <button
                    onClick={() => handleApply(job)}
                    disabled={!!appliedMap[job.id]}
                    className={`px-3 py-2 rounded-lg text-sm ${appliedMap[job.id] ? 'bg-gray-200 text-gray-500' : 'bg-primary text-white'}`}
                  >
                    {appliedMap[job.id] ? appliedMap[job.id].status : '지원하기'}
                  </button>
                </div>
                {aiMatched && (
                  <span className="text-5xl font-bold text-primary absolute right-8 bottom-6">{job.matchRate}% <span className="text-xl text-gray-500 font-medium">적합</span></span>
                )}
              </div>
            ))}
            {shownJobs.length === 0 && (
              <div className="bg-white rounded-2xl p-8 border border-gray-200 text-center text-gray-500">
                선택한 조건에 맞는 공고가 없습니다.
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  )
}
