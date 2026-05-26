'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { getApplications, getBookmarks, toggleBookmark } from '@/lib/userStorage'

const STATUS_STYLE = {
  '검토 중': 'bg-amber-100 text-amber-700',
  합격: 'bg-green-100 text-green-700',
  불합격: 'bg-red-100 text-red-700',
}

export default function ApplicationStatusPage() {
  const router = useRouter()
  const { user, isAuthenticated, mounted } = useAuth()
  const resumeUserId = user?.uid || user?.id || ''
  const [bookmarkIds, setBookmarkIds] = useState([])

  useEffect(() => {
    if (mounted && !isAuthenticated) router.replace('/login')
  }, [mounted, isAuthenticated, router])

  useEffect(() => {
    if (!mounted || !isAuthenticated) return
    const bookmarks = getBookmarks(resumeUserId)
    setBookmarkIds(bookmarks.map((item) => item.id))
  }, [mounted, isAuthenticated, resumeUserId])

  if (!mounted || !isAuthenticated) return null

  const applications = getApplications(resumeUserId)

  return (
    <main className="max-w-4xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">지원현황</h1>
      {applications.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-2xl p-8 text-gray-500">지원한 기업 정보가 없습니다.</div>
      ) : (
        <div className="space-y-3">
          {applications.map((application) => (
            <div key={application.jobId} className="bg-white border border-gray-200 rounded-xl p-4 flex justify-between items-center gap-3 relative">
              <button
                onClick={() => {
                  const job = { id: application.jobId, title: application.title, company: application.company }
                  const next = toggleBookmark(job, resumeUserId)
                  setBookmarkIds(next.map((item) => item.id))
                }}
                className="absolute top-4 right-4"
                aria-label="북마크"
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill={bookmarkIds.includes(application.jobId) ? '#2563eb' : '#ffffff'} xmlns="http://www.w3.org/2000/svg">
                  <path
                    d="M6 3.75C6 3.33579 6.33579 3 6.75 3H17.25C17.6642 3 18 3.33579 18 3.75V21L12 16.5L6 21V3.75Z"
                    stroke={bookmarkIds.includes(application.jobId) ? '#2563eb' : '#94a3b8'}
                    strokeWidth="1.8"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
              <div>
                <p className="text-gray-500">{application.company}</p>
                <button onClick={() => router.push(`/jobs/${application.jobId}`)} className="font-semibold hover:text-primary transition-colors text-left">
                  {application.title}
                </button>
                <p className="text-sm text-gray-500">지원일: {application.appliedAt}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_STYLE[application.status] || 'bg-gray-100 text-gray-700'}`}>
                {application.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </main>
  )
}
