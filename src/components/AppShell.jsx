'use client'

import MobileBottomNav from '@/components/MobileBottomNav'

export default function AppShell({ children }) {
  return (
    <>
      <div className="pb-20 md:pb-0">{children}</div>
      <MobileBottomNav />
    </>
  )
}
