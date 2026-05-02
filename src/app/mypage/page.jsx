'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { getApplications, getBookmarks, getRecentJobs, getResumes } from '@/lib/userStorage'

const ACTIVITY_ITEMS = [
  { href: '/mypage/resumes', icon: '📄', label: '이력서 관리', key: 'resumes' },
  { href: '/mypage/applications', icon: '🕐', label: '지원현황', key: 'applications' },
  { href: '/mypage/recent', icon: '👁️', label: '최근 본 공고', key: 'recent' },
  { href: '/mypage/bookmarks', icon: '🏢', label: '관심기업', key: 'bookmarks' },
]

export default function MyPage() {
  const { user, isAuthenticated, mounted, logout } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (mounted && !isAuthenticated) {
      router.replace('/login')
    }
  }, [mounted, isAuthenticated, router])

  const handleLogout = () => {
    logout()
    router.replace('/')
  }

  if (!mounted || !isAuthenticated) {
    return (
      <main className="min-h-[60vh] flex items-center justify-center">
        <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </main>
    )
  }

  const name = user?.name || '홍길동'
  const email = user?.email || 'example@email.com'
  const initial = name.charAt(0)
  const resumes = getResumes()
  const applications = getApplications()
  const recentJobs = getRecentJobs()
  const bookmarks = getBookmarks()
  const statsByKey = {
    resumes: resumes.length,
    applications: applications.length,
    recent: recentJobs.length,
    bookmarks: bookmarks.length,
  }
  const acceptedCount = applications.filter((item) => item.status === '합격').length
  const reviewingCount = applications.filter((item) => item.status === '검토 중').length

  return (
    <main className="max-w-3xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">마이페이지</h1>

      {/* 프로필 카드 */}
      <div className="bg-gradient-to-br from-blue-100 to-sky-100 rounded-2xl p-6 mb-8">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 rounded-full bg-primary flex items-center justify-center text-white text-2xl font-bold flex-shrink-0">
            {initial}
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-800">{name} 님</h2>
            <p className="text-sm text-gray-500">{email}</p>
          </div>
        </div>

        {/* 활동 통계 */}
        <div className="flex gap-4">
          <div className="flex-1 bg-white rounded-xl p-4 text-center shadow-sm">
            <p className="text-2xl font-bold text-primary">{applications.length}</p>
            <p className="text-sm text-gray-500 mt-1">지원</p>
          </div>
          <div className="flex-1 bg-white rounded-xl p-4 text-center shadow-sm">
            <p className="text-2xl font-bold text-green-600">{acceptedCount}</p>
            <p className="text-sm text-gray-500 mt-1">합격</p>
          </div>
          <div className="flex-1 bg-white rounded-xl p-4 text-center shadow-sm">
            <p className="text-2xl font-bold text-red-600">{reviewingCount}</p>
            <p className="text-sm text-gray-500 mt-1">진행중</p>
          </div>
        </div>
      </div>

      {/* 내 활동 */}
      <section className="mb-8">
        <h3 className="text-lg font-bold mb-4">내 활동</h3>
        <div className="bg-white rounded-xl shadow-sm overflow-hidden divide-y divide-gray-100">
          {ACTIVITY_ITEMS.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className="flex items-center justify-between px-4 py-4 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">{item.icon}</span>
                <span className="font-medium">{item.label}</span>
                {statsByKey[item.key] > 0 && (
                  <span className="px-2 py-0.5 bg-primary text-white text-xs font-medium rounded-full">
                    {statsByKey[item.key]}
                  </span>
                )}
              </div>
              <span className="text-gray-400">›</span>
            </Link>
          ))}
        </div>
      </section>

      {/* 로그아웃 버튼 */}
      <button
        onClick={handleLogout}
        className="w-full py-4 rounded-xl border-2 border-red-500 bg-red-50 text-red-600 font-semibold flex items-center justify-center gap-2 hover:bg-red-100 transition-colors"
      >
        <span className="text-lg">↪</span>
        로그아웃
      </button>
    </main>
  )
}
