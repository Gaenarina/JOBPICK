'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useNotifications } from '@/context/NotificationContext'
import { Home, Briefcase, GraduationCap, FileText, Eye, Building2, User, X } from 'lucide-react'

export default function SlideMenu({ isOpen, onClose }) {
  const pathname = usePathname()
  const { badgeCounts } = useNotifications()

  if (!isOpen) return null

  const mainItems = [
    { href: '/', icon: Home, label: '홈' },
    { href: '/dashboard', icon: Briefcase, label: '채용정보' },
    { href: '/intern', icon: GraduationCap, label: '신입·인턴' },
  ]

  const myPageItems = [
    { href: '/mypage/resumes', icon: FileText, label: '이력서 관리', badge: badgeCounts.resume },
    { href: '/mypage/recent', icon: Eye, label: '최근 본 공고' },
    { href: '/mypage/bookmarks', icon: Building2, label: '관심기업', badge: badgeCounts.company },
    { href: '/mypage', icon: User, label: '마이페이지' },
  ]

  return (
    <>
      <div
        className="fixed inset-0 bg-black/30 z-40 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className="fixed top-0 right-0 h-full w-72 bg-white shadow-xl z-50 flex flex-col animate-slide-in"
        role="dialog"
        aria-label="메뉴"
      >
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <h2 className="text-lg font-bold text-primary">메뉴</h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="메뉴 닫기"
          >
            <X className="w-5 h-5" aria-hidden />
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto p-4">
          <div className="mb-6">
            <p className="text-xs text-gray-400 font-medium mb-3">메인</p>
            <ul className="space-y-1">
              {mainItems.map((item) => {
                const isActive = pathname === item.href
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={onClose}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                        isActive ? 'bg-primary text-white' : 'text-gray-700'
                      }`}
                    >
                      <item.icon className="w-5 h-5" aria-hidden />
                      <span>{item.label}</span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          </div>
          <div>
            <p className="text-xs text-gray-400 font-medium mb-3">마이페이지</p>
            <ul className="space-y-1">
              {myPageItems.map((item) => {
                const isActive = pathname === item.href
                return (
                <li key={item.href + item.label}>
                  <Link
                    href={item.href}
                    onClick={onClose}
                    className={`flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                      isActive ? 'bg-primary text-white' : 'text-gray-700'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <item.icon className="w-5 h-5" aria-hidden />
                      <span>{item.label}</span>
                    </div>
                    {item.badge !== undefined && item.badge > 0 && (
                      <span className="min-w-[20px] h-5 px-1.5 flex items-center justify-center bg-primary text-white text-xs font-medium rounded-full">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                </li>
              )})}
            </ul>
          </div>
        </nav>
      </aside>
    </>
  )
}
