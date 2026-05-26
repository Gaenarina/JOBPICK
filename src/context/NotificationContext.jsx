'use client'

import { createContext, useContext, useState } from 'react'

const NotificationContext = createContext(null)

const INITIAL_NOTIFICATIONS = [
  { id: 1, category: 'resume', icon: 'file', title: '토스 서류 합격', content: 'Product Designer 포지션 서류전형에 합격하셨습니다!', time: '1시간 전', read: false },
  { id: 2, category: 'company', icon: 'sparkles', title: '새로운 매칭 공고', content: '지민님과 95% 일치하는 당근마켓 공고가 올라왔어요', time: '3시간 전', read: false },
  { id: 3, category: 'application', icon: 'calendar', title: '면접 일정 안내', content: '우아한형제들 면접이 2024.02.15 14:00에 예정되어 있습니다', time: '5시간 전', read: true },
  { id: 4, category: 'resume', icon: 'bell', title: '이력서 업데이트 추천', content: '이력서를 업데이트하면 더 정확한 매칭을 받을 수 있어요', time: '1일 전', read: true },
]

export function NotificationProvider({ children }) {
  const [notifications, setNotifications] = useState(INITIAL_NOTIFICATIONS)

  const unreadCount = notifications.filter((n) => !n.read).length

  const markAsRead = (id) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)))
  }

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
  }

  const getBadgeByCategory = () => {
    const counts = { resume: 0, application: 0, company: 0 }
    notifications
      .filter((n) => !n.read)
      .forEach((n) => {
        if (n.category === 'resume') counts.resume++
        else if (n.category === 'application') counts.application++
        else if (n.category === 'company') counts.company++
      })
    return counts
  }

  const badgeCounts = getBadgeByCategory()

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        markAsRead,
        markAllAsRead,
        badgeCounts,
      }}
    >
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotifications() {
  const context = useContext(NotificationContext)
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider')
  }
  return context
}
