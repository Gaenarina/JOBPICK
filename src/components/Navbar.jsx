'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { useNotifications } from '@/context/NotificationContext'
import SlideMenu from './SlideMenu'
import NotificationPanel from './NotificationPanel'
import { Bell, ClipboardList } from 'lucide-react'

export default function Navbar() {
  const pathname = usePathname()
  const { isAuthenticated } = useAuth()
  const { unreadCount } = useNotifications()
  const [menuOpen, setMenuOpen] = useState(false)
  const [notificationOpen, setNotificationOpen] = useState(false)

  const showMinimal = pathname === '/login' || pathname === '/signup'

  return (
    <>
      <nav className="flex items-center justify-between px-4 sm:px-8 py-5 md:py-6 min-h-[72px] md:min-h-[76px] bg-white shadow-sm">
        <Link href="/" className="flex items-center gap-2 font-bold text-2xl md:text-3xl text-primary">
  <img
    src="/jobpick-logo.png"
    alt="JOB PICK"
    className="w-9 h-9 md:w-10 md:h-10 object-contain"
  />
  <span>JOB PICK</span>
</Link>

        <div className="flex items-center gap-4">
          {showMinimal ? (
            <>
              <Link href="/login" className="text-gray-800 text-sm hover:text-primary transition-colors">
                로그인
              </Link>
              <Link href="/signup" className="text-gray-800 text-sm hover:text-primary transition-colors">
                회원가입
              </Link>
            </>
          ) : (
            <>
              <button
                onClick={() => setNotificationOpen(true)}
                className="relative p-2 text-xl hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="알림"
              >
                <Bell className="w-6 h-6 text-gray-800" aria-hidden />
                {unreadCount > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 flex items-center justify-center bg-primary text-white text-xs font-medium rounded-full">
                    {unreadCount}
                  </span>
                )}
              </button>

              <button
                onClick={() => setMenuOpen(true)}
                className="hidden md:inline-flex px-4 py-2 bg-gray-800 text-white rounded-md text-sm hover:bg-gray-700 transition-colors"
              >
                메뉴
              </button>

              {!isAuthenticated && (
                <>
                  <Link href="/login" className="text-gray-800 text-sm hover:text-primary transition-colors">
                    로그인
                  </Link>
                  <Link href="/signup" className="text-gray-800 text-sm hover:text-primary transition-colors">
                    회원가입
                  </Link>
                </>
              )}
            </>
          )}
        </div>
      </nav>

      <SlideMenu isOpen={menuOpen} onClose={() => setMenuOpen(false)} />
      <NotificationPanel isOpen={notificationOpen} onClose={() => setNotificationOpen(false)} />
    </>
  )
}