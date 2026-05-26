'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Home, Briefcase, GraduationCap, User } from 'lucide-react'

const NAV_ITEMS = [
  { href: '/', label: '홈', icon: Home },
  { href: '/dashboard', label: '채용정보', icon: Briefcase },
  { href: '/intern', label: '신입인턴', icon: GraduationCap },
  { href: '/mypage', label: '마이페이지', icon: User },
]

export default function MobileBottomNav() {
  const pathname = usePathname()

  if (pathname === '/login' || pathname === '/signup') {
    return null
  }

  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-30 border-t border-gray-200 bg-white/95 backdrop-blur-sm pb-[env(safe-area-inset-bottom)]"
      aria-label="하단 메뉴"
    >
      <div className="flex items-stretch justify-around max-w-lg mx-auto h-16">
        {NAV_ITEMS.map((item) => {
          const active =
            item.href === '/'
              ? pathname === '/'
              : pathname === item.href || pathname.startsWith(`${item.href}/`)

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-1 flex-col items-center justify-center gap-0.5 text-[11px] font-medium transition-colors ${
                active ? 'text-primary' : 'text-gray-500'
              }`}
            >
              <item.icon className="w-5 h-5" aria-hidden />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
