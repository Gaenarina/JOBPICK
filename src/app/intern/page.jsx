'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { INTERN_JOBS } from '@/lib/jobs'
import { addResumes, getBookmarks, getResumes, pushRecentJob, removeResume, toggleBookmark } from '@/lib/userStorage'

export default function InternPage() {
  const { user, isAuthenticated, mounted } = useAuth()
  const resumeUserId = user?.uid || user?.id || ''
  const router = useRouter()
  const [activeTab, setActiveTab] = useState('coaching')
  const [savedResumes, setSavedResumes] = useState([])
  const [coachingFiles, setCoachingFiles] = useState([])
  const [showSavedList, setShowSavedList] = useState(false)
  const [selectedResume, setSelectedResume] = useState(null)
  const [isCoaching, setIsCoaching] = useState(false)
  const [coachingResult, setCoachingResult] = useState(null)
  const [bookmarkIds, setBookmarkIds] = useState([])
  const fileInputRef = useRef(null)
  const coachingInputRef = useRef(null)

  useEffect(() => {
    if (mounted && !isAuthenticated) {
      router.replace('/login')
    }
  }, [mounted, isAuthenticated, router])

  useEffect(() => {
    if (!mounted) return
    setSavedResumes(getResumes(resumeUserId))
    setBookmarkIds(getBookmarks(resumeUserId).map((item) => item.id))
  }, [mounted, resumeUserId])

  const attachSavedResume = (resume) => {
    setCoachingFiles((prev) => {
      if (prev.some((file) => file.id === resume.id)) return prev
      return [resume, ...prev]
    })
    startCoaching(resume)
  }

  const startCoaching = (resume) => {
    setSelectedResume(resume)
    setIsCoaching(true)
    setCoachingResult(null)
    setTimeout(() => {
      const lower = resume.name.toLowerCase()
      const domainHint = lower.includes('dev') || lower.includes('server') || lower.includes('frontend') ? '기술 기반 역량' : '직무 이해와 성과 중심 서술'

      setCoachingResult({
        title: `${resume.name} 기준 작성 방향 코칭`,
        bullets: [
          `도입부는 “지원 직무에 왜 적합한지”를 한 문장으로 먼저 고정하세요.`,
          `경험 파트는 ${domainHint} 관점에서 STAR(상황-과제-행동-결과) 구조로 정리하세요.`,
          `마무리는 지원 회사의 요구사항(직무/환경)에 맞춰 “입사 후 어떻게 기여할지”를 구체적으로 연결하세요.`,
          `마지막 검수에서 문장 길이를 줄이고, 핵심 키워드를 2~3회 반복해 인상도를 높이세요.`,
        ],
      })
      setIsCoaching(false)
    }, 900)
  }

  const handleNewResumeUpload = (e) => {
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

    const next = addResumes(mapped, resumeUserId)
    setSavedResumes(next)
    setCoachingFiles((prev) => [...mapped, ...prev])
    if (mapped.length > 0) startCoaching(mapped[0])
    e.target.value = ''
  }

  const handleDeleteSavedResume = (resumeId) => {
    const next = removeResume(resumeId, resumeUserId)
    setSavedResumes(next)
    setCoachingFiles((prev) => prev.filter((r) => r.id !== resumeId))
    if (selectedResume?.id === resumeId) {
      setSelectedResume(null)
      setIsCoaching(false)
      setCoachingResult(null)
    }
  }

  const goJobDetail = (job) => {
    pushRecentJob(job)
    router.push(`/jobs/${job.id}`)
  }

  const handleToggleBookmark = (job) => {
    const next = toggleBookmark(job, resumeUserId)
    setBookmarkIds(next.map((item) => item.id))
  }

  if (!mounted || !isAuthenticated) {
    return (
      <main className="max-w-5xl mx-auto p-4 md:p-8 flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin w-10 h-10 border-2 border-primary border-t-transparent rounded-full" />
      </main>
    )
  }

  return (
    <main className="max-w-5xl mx-auto p-4 md:p-8">
      <div className="flex flex-wrap gap-2 md:gap-3 mb-6 md:mb-8">
        <button
          type="button"
          onClick={() => setActiveTab('realtime')}
          className={`px-4 md:px-6 py-2.5 md:py-3 rounded-xl text-sm md:text-base ${activeTab === 'realtime' ? 'bg-primary text-white' : 'bg-slate-100 text-gray-700'}`}
        >
          실시간 공고
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('salary')}
          className={`px-4 md:px-6 py-2.5 md:py-3 rounded-xl text-sm md:text-base ${activeTab === 'salary' ? 'bg-primary text-white' : 'bg-slate-100 text-gray-700'}`}
        >
          신입연봉
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('coaching')}
          className={`px-4 md:px-6 py-2.5 md:py-3 rounded-xl text-sm md:text-base ${activeTab === 'coaching' ? 'bg-primary text-white' : 'bg-slate-100 text-gray-700'}`}
        >
          AI 자소서 코칭
        </button>
      </div>

      {activeTab === 'coaching' && (
        <section className="mb-8 bg-gradient-to-r from-blue-500/80 to-cyan-200 rounded-3xl border border-blue-400 p-4 md:p-5 text-white">
          <h2 className="text-2xl md:text-3xl font-semibold mb-1">AI 자소서 코칭</h2>
          <p className="text-sm md:text-base text-blue-50 mb-4">AI가 자기소개서를 분석하고 개선 방향을 제시해드립니다.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
            <button
              type="button"
              onClick={() => setShowSavedList((prev) => !prev)}
              className="bg-white text-primary rounded-xl px-4 py-3 font-medium"
            >
              등록한 자소서 불러오기
            </button>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="bg-white/90 text-gray-700 rounded-xl px-4 py-3 font-medium"
            >
              새 자소서 등록하기
            </button>
            <input ref={fileInputRef} type="file" accept=".pdf,.doc,.docx" multiple className="hidden" onChange={handleNewResumeUpload} />
          </div>
          {showSavedList && (
            <div className="mb-4 bg-white/90 rounded-xl p-3 text-gray-800">
              <p className="font-medium mb-2">기존 등록 파일 선택</p>
              {savedResumes.length === 0 ? (
                <p className="text-sm text-gray-500">등록된 파일이 없습니다.</p>
              ) : (
                <div className="space-y-2">
                  {savedResumes.map((resume) => (
                    <div key={resume.id} className="flex items-center justify-between gap-2 border border-gray-200 rounded-lg p-2">
                      <div>
                        <p className="text-sm font-medium">{resume.name}</p>
                        <p className="text-xs text-gray-500">{resume.size} · {resume.date}</p>
                      </div>
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => attachSavedResume(resume)}
                              className="px-3 py-1 rounded-md bg-primary text-white text-sm"
                            >
                              첨부
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteSavedResume(resume.id)}
                              className="px-2 py-1 rounded-md bg-red-50 text-red-600 text-sm"
                            >
                              삭제
                            </button>
                          </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          <div className="space-y-3">
            {coachingFiles.map((file) => (
              <div key={file.id} className="bg-white rounded-xl p-4 text-gray-800">
                <p className="font-medium">{file.name}</p>
                <p className="text-sm text-gray-500">{file.size} · {file.date}</p>
              </div>
            ))}
          </div>
              {selectedResume && (
                <div className="mt-5 bg-white/10 border border-white/20 rounded-2xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-lg font-semibold">{selectedResume.name}</h3>
                    <span className="text-xs text-blue-50/90">
                      {isCoaching ? '코칭 중...' : '코칭 완료'}
                    </span>
                  </div>
                  {isCoaching ? (
                    <div className="flex items-center gap-3 text-sm text-blue-50">
                      <div className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                      AI가 작성 방향을 생성하고 있어요...
                    </div>
                  ) : coachingResult ? (
                    <div>
                      <p className="text-sm text-blue-50 mb-2">{coachingResult.title}</p>
                      <ul className="list-disc pl-5 space-y-1 text-sm text-blue-50/95">
                        {coachingResult.bullets.map((b, idx) => (
                          <li key={idx}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              )}
        </section>
      )}

      {activeTab === 'realtime' && (
        <section>
          <h2 className="text-2xl md:text-4xl font-bold mb-4 md:mb-5">실시간 공고</h2>
          <div className="space-y-4">
            {INTERN_JOBS.map((job) => (
              <div key={job.id} className="bg-white border border-gray-200 rounded-2xl p-4 md:p-5 relative">
                <button onClick={() => handleToggleBookmark(job)} className="absolute top-5 right-5" aria-label="북마크">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill={bookmarkIds.includes(job.id) ? '#2563eb' : '#ffffff'} xmlns="http://www.w3.org/2000/svg">
                    <path
                      d="M6 3.75C6 3.33579 6.33579 3 6.75 3H17.25C17.6642 3 18 3.33579 18 3.75V21L12 16.5L6 21V3.75Z"
                      stroke={bookmarkIds.includes(job.id) ? '#2563eb' : '#94a3b8'}
                      strokeWidth="1.8"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
                <p className="text-base md:text-2xl text-gray-500 mb-2">{job.company}</p>
                <button onClick={() => goJobDetail(job)} className="text-lg md:text-3xl font-semibold mb-3 text-left hover:text-primary transition-colors">
                  {job.title}
                </button>
                <div className="flex gap-2">
                  <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">{job.location}</span>
                  <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">{job.career}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {activeTab === 'salary' && (
        <section>
          <h2 className="text-2xl md:text-4xl font-bold mb-4 md:mb-5">신입연봉</h2>
          <div className="space-y-4">
            {INTERN_JOBS.map((job) => (
              <div key={job.id} className="bg-white border border-gray-200 rounded-2xl p-4 md:p-5 flex justify-between items-center gap-3 relative">
                <button onClick={() => handleToggleBookmark(job)} className="absolute top-5 right-5" aria-label="북마크">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill={bookmarkIds.includes(job.id) ? '#2563eb' : '#ffffff'} xmlns="http://www.w3.org/2000/svg">
                    <path
                      d="M6 3.75C6 3.33579 6.33579 3 6.75 3H17.25C17.6642 3 18 3.33579 18 3.75V21L12 16.5L6 21V3.75Z"
                      stroke={bookmarkIds.includes(job.id) ? '#2563eb' : '#94a3b8'}
                      strokeWidth="1.8"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
                <div>
                  <p className="text-base md:text-2xl text-gray-500 mb-1">{job.company}</p>
                  <button onClick={() => goJobDetail(job)} className="text-lg md:text-3xl font-semibold text-left hover:text-primary transition-colors">
                    {job.title}
                  </button>
                </div>
                <p className="text-2xl md:text-4xl font-bold text-primary whitespace-nowrap">{job.salary}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  )
}
