
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import {
  getBookmarks,
  toggleBookmark,
  updateBookmarkMemo,
} from '@/lib/userStorage'

function getJobKey(job) {
  return String(job?.id || job?.jobId || '')
}

function getMatchScore(job) {
  if (
    job?.matchRate !== undefined &&
    job?.matchRate !== null &&
    job.matchRate !== ''
  ) {
    return Math.round(Number(job.matchRate))
  }

  if (
    job?.finalScore !== undefined &&
    job?.finalScore !== null &&
    job.finalScore !== ''
  ) {
    return Math.round(Number(job.finalScore))
  }

  return null
}

export default function BookmarksPage() {
  const router = useRouter()
  const { user, isAuthenticated, mounted } = useAuth()
  const resumeUserId = user?.uid || user?.id || ''

  const [jobs, setJobs] = useState([])
  const [editingId, setEditingId] = useState('')
  const [draftMemo, setDraftMemo] = useState('')

  useEffect(() => {
    if (mounted && !isAuthenticated) {
      router.replace('/login')
    }
  }, [mounted, isAuthenticated, router])

  useEffect(() => {
    if (!mounted || !isAuthenticated) return
    setJobs(getBookmarks(resumeUserId))
  }, [mounted, isAuthenticated, resumeUserId])

  const startEditMemo = (job) => {
    const jobKey = getJobKey(job)
    setEditingId(jobKey)
    setDraftMemo(job.memo || '')
  }

  const cancelEditMemo = () => {
    setEditingId('')
    setDraftMemo('')
  }

  const saveMemo = (job) => {
    const next = updateBookmarkMemo(
      getJobKey(job),
      draftMemo,
      resumeUserId
    )
    setJobs(next)
    cancelEditMemo()
  }

  const deleteMemo = (job) => {
    const next = updateBookmarkMemo(
      getJobKey(job),
      '',
      resumeUserId
    )
    setJobs(next)

    if (editingId === getJobKey(job)) {
      cancelEditMemo()
    }
  }

  if (!mounted || !isAuthenticated) return null

  return (
    <main className="max-w-4xl mx-auto p-4 sm:p-6 md:p-8">
      <h1 className="text-2xl sm:text-3xl font-bold mb-6">
        관심기업
      </h1>

      {jobs.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-2xl p-5 sm:p-8 text-gray-500">
          북마크한 공고가 없습니다.
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => {
            const jobKey = getJobKey(job)
            const matchScore = getMatchScore(job)
            const isEditing = editingId === jobKey
            const memo = String(job.memo || '').trim()

            return (
              <div
                key={jobKey || job.title}
                className="relative min-w-0 bg-white border border-gray-200 rounded-xl p-4"
              >
                {/* 기존 북마크 기능 유지 */}
                <button
                  type="button"
                  onClick={() => {
                    if (isEditing) cancelEditMemo()
                    setJobs(toggleBookmark(job, resumeUserId))
                  }}
                  className="absolute top-2 right-2 z-10 flex h-11 w-11 items-center justify-center rounded-lg hover:bg-blue-50 sm:top-4 sm:right-4"
                  aria-label="북마크"
                >
                  <svg
                    width="22"
                    height="22"
                    viewBox="0 0 24 24"
                    fill="#2563eb"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M6 3.75C6 3.33579 6.33579 3 6.75 3H17.25C17.6642 3 18 3.33579 18 3.75V21L12 16.5L6 21V3.75Z"
                      stroke="#2563eb"
                      strokeWidth="1.8"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>

                {/* 회사 및 공고 정보 */}
                <p className="pr-12 text-gray-500 break-words">
                  {job.company}
                </p>

                <button
                  type="button"
                  onClick={() =>
                    router.push(`/jobs/${job.id || job.jobId}`)
                  }
                  className="block max-w-full pr-12 font-semibold text-left break-words hover:text-primary transition-colors"
                >
                  {job.title}
                </button>

                {Number.isFinite(matchScore) && (
                  <p className="text-sm text-primary font-medium mt-1">
                    AI 적합도 {matchScore}점
                  </p>
                )}

                <div className="flex flex-wrap gap-2 mt-2">
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
                </div>

                {/* 메모 */}
                <div className="mt-4 pt-3 border-t border-gray-100">
                  <p className="text-sm font-medium text-gray-700 mb-2">
                    메모
                  </p>

                  {isEditing ? (
                    <div>
                      <textarea
                        value={draftMemo}
                        onChange={(e) =>
                          setDraftMemo(e.target.value)
                        }
                        maxLength={300}
                        rows={3}
                        placeholder="메모할 내용을 적어보세요."
                        className="w-full rounded-lg border border-gray-200 bg-slate-50 px-3 py-2 text-base sm:text-sm text-gray-700 outline-none focus:border-primary"
                      />

                      <div className="mt-2 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => saveMemo(job)}
                          className="min-h-[44px] px-3 py-1.5 rounded-lg bg-primary text-white text-sm"
                        >
                          저장
                        </button>

                        <button
                          type="button"
                          onClick={cancelEditMemo}
                          className="min-h-[44px] px-3 py-1.5 rounded-lg bg-slate-100 text-gray-700 text-sm"
                        >
                          취소
                        </button>
                      </div>
                    </div>
                  ) : memo ? (
                    <div>
                      <p className="text-sm text-gray-600 whitespace-pre-wrap break-words">
                        “{memo}”
                      </p>

                      <div className="mt-2 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => startEditMemo(job)}
                          className="min-h-[44px] px-3 py-1.5 rounded-lg bg-slate-100 text-gray-700 text-sm"
                        >
                          메모 수정
                        </button>

                        <button
                          type="button"
                          onClick={() => deleteMemo(job)}
                          className="min-h-[44px] px-3 py-1.5 rounded-lg bg-red-50 text-red-600 text-sm"
                        >
                          삭제
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => startEditMemo(job)}
                      className="min-h-[44px] px-3 py-1.5 rounded-lg bg-slate-100 text-gray-700 text-sm"
                    >
                      메모 작성
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </main>
  )
}
