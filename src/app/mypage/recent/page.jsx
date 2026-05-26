'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { getBookmarks, getRecentJobs, toggleBookmark } from '@/lib/userStorage'

export default function RecentJobsPage() {
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

  const jobs = getRecentJobs()

  return (
    <main className="max-w-4xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">최근 본 공고</h1>
      {jobs.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-2xl p-8 text-gray-500">최근 본 공고가 없습니다.</div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <div key={job.id} className="bg-white border border-gray-200 rounded-xl p-4 relative">
              <button
                onClick={() => {
                  const next = toggleBookmark(job, resumeUserId)
                  setBookmarkIds(next.map((item) => item.id))
                }}
                className="absolute top-4 right-4"
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
              <p className="text-gray-500">{job.company}</p>
              <button onClick={() => router.push(`/jobs/${job.id}`)} className="font-semibold hover:text-primary transition-colors">
                {job.title}
              </button>
              <div className="flex gap-2 mt-2">
                <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">{job.location}</span>
                <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">{job.career}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  )
}
