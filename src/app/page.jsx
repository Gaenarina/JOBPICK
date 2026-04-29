'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '../context/AuthContext'
import { addResumes, getBookmarks, getResumes, pushRecentJob, removeResume, toggleBookmark } from '../lib/userStorage'
import { DASHBOARD_JOBS } from '../lib/jobs'

export default function LandingPage() {
  const router = useRouter()
  const { user, isAuthenticated, mounted } = useAuth()
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

  const handleFileSelect = async (e) => {
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

      const mapped = [{
        id: data.docId || Date.now() + Math.random(),
        name: file.name,
        size: Math.round(file.size / 1024) + ' KB',
        date: dateStr,
      }]

      setResumes(addResumes(mapped))
      setShowSavedResumes(true)
      setSelectedResume(mapped[0])

      setIsAnalyzing(false)
      setAnalysisDone(true)
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
    setBookmarkIds(getBookmarks().map((item) => item.id))
  }, [mounted])

  const name = user?.name || '홍길동'

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
    router.push(`/jobs/${job.id}`)
  }

  const handleToggleBookmark = (job) => {
    const next = toggleBookmark(job)
    setBookmarkIds(next.map((item) => item.id))
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
            <p className="text-sm text-gray-500 mb-3">PDF, DOC, DOCX 파일을 업로드하거나, 등록한 이력서를 선택해 분석해보세요.</p>
            {showSavedResumes && (
              <div className="flex flex-col gap-3">
                {resumes.length === 0 ? (
                  <p className="text-sm text-gray-500">등록된 이력서가 없습니다. 새 이력서를 등록해 주세요.</p>
                ) : (
                  resumes.map((r) => (
                    <div key={r.id} className={`flex items-center justify-between gap-3 p-4 border rounded-lg bg-white ${
                      selectedResume?.id === r.id ? 'border-primary' : 'border-gray-200'
                    }`}>
                      <button
                        type="button"
                        onClick={() => handleResumeAnalyze(r)}
                        className="flex items-center gap-4 text-left flex-1"
                      >
                        <span className="text-2xl">📄</span>
                        <div className="flex flex-col">
                          <span className="font-medium">{r.name}</span>
                          <span className="text-sm text-gray-500">
                            {r.size} · {r.date}
                          </span>
                        </div>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteResume(r.id)}
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
                {DASHBOARD_JOBS.slice(0, 3).map((job) => (
                  <div key={job.id} className="flex items-center justify-between gap-3 border border-gray-200 rounded-lg p-4">
                    <div>
                      <p className="text-xs text-gray-500 mb-1">{job.company}</p>
                      <button onClick={() => handleGoJob(job)} className="font-medium text-sm text-left hover:text-primary transition-colors">
                        {job.title}
                      </button>
                    </div>
                    <div className="flex items-center gap-3">
                      <button onClick={() => handleToggleBookmark(job)} aria-label="북마크">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill={bookmarkIds.includes(job.id) ? '#2563eb' : '#ffffff'} xmlns="http://www.w3.org/2000/svg">
                          <path
                            d="M6 3.75C6 3.33579 6.33579 3 6.75 3H17.25C17.6642 3 18 3.33579 18 3.75V21L12 16.5L6 21V3.75Z"
                            stroke={bookmarkIds.includes(job.id) ? '#2563eb' : '#94a3b8'}
                            strokeWidth="1.8"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </button>
                      {job.matchRate && (
                        <span className="text-primary font-bold text-lg">{job.matchRate}%</span>
                      )}
                    </div>
                  </div>
                ))}
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
        <div className="flex flex-col gap-4">
          {DASHBOARD_JOBS.slice(0, 2).map((job) => (
            <div key={job.id} className="relative bg-white rounded-lg p-5 shadow-sm border border-gray-200">
              <button onClick={() => handleToggleBookmark(job)} className="absolute top-4 right-4" aria-label="북마크">
                <svg width="22" height="22" viewBox="0 0 24 24" fill={bookmarkIds.includes(job.id) ? '#2563eb' : '#ffffff'} xmlns="http://www.w3.org/2000/svg">
                  <path
                    d="M6 3.75C6 3.33579 6.33579 3 6.75 3H17.25C17.6642 3 18 3.33579 18 3.75V21L12 16.5L6 21V3.75Z"
                    stroke={bookmarkIds.includes(job.id) ? '#2563eb' : '#94a3b8'}
                    strokeWidth="1.8"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
              <button onClick={() => handleGoJob(job)} className="font-semibold mb-1 hover:text-primary transition-colors text-left">
                {job.title}
              </button>
              <p className="text-sm text-gray-500 mb-2">{job.company}</p>
              <div className="flex gap-2 flex-wrap">
                <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">{job.career}</span>
                <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">{job.location}</span>
              </div>
            </div>
          ))}
        </div>
      </section>
    </main>
  )
}