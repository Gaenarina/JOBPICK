'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '../context/AuthContext'
import { getJobById } from '../lib/jobs'
import { getBookmarks, toggleBookmark } from '../lib/userStorage'

export default function JobDetailPage() {
  const router = useRouter()
  const params = useParams()
  const { isAuthenticated, mounted } = useAuth()
  const [isBookmarked, setIsBookmarked] = useState(false)

  useEffect(() => {
    if (mounted && !isAuthenticated) router.replace('/login')
  }, [mounted, isAuthenticated, router])

  if (!mounted || !isAuthenticated) return null

  const id = Array.isArray(params?.id) ? params.id[0] : params?.id
  const job = getJobById(id)

  useEffect(() => {
    if (!mounted || !job) return
    const bookmarked = getBookmarks().some((item) => String(item.id) === String(job.id))
    setIsBookmarked(bookmarked)
  }, [mounted, job])

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

  return (
    <main className="max-w-4xl mx-auto p-8">
      <div className="bg-white border border-gray-200 rounded-2xl p-6">
        <div className="flex justify-end mb-2">
          <button
            type="button"
            onClick={() => {
              const next = toggleBookmark(job)
              setIsBookmarked(next.some((item) => String(item.id) === String(job.id)))
            }}
            aria-label="북마크"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill={isBookmarked ? '#2563eb' : '#ffffff'} xmlns="http://www.w3.org/2000/svg">
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
          <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">{job.location}</span>
          <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">{job.career}</span>
          <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">{job.category}</span>
        </div>
        <div className="grid sm:grid-cols-2 gap-3 mb-6">
          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-sm text-gray-500 mb-1">예상 신입연봉</p>
            <p className="text-2xl font-bold text-primary">{job.salary || '협의'}</p>
          </div>
          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-sm text-gray-500 mb-1">AI 적합도</p>
            <p className="text-2xl font-bold text-primary">{job.matchRate ? `${job.matchRate}%` : '미분석'}</p>
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
    </main>
  )
}
