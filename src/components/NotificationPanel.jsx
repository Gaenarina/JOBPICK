'use client'

import { useNotifications } from '@/context/NotificationContext'
import { Bell, CalendarClock, CheckCheck, FileText, Sparkles, X } from 'lucide-react'

export default function NotificationPanel({ isOpen, onClose }) {
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications()

  if (!isOpen) return null

  const renderIcon = (iconKey) => {
    const cls = 'w-6 h-6 text-gray-700'
    if (iconKey === 'file') return <FileText className={cls} aria-hidden />
    if (iconKey === 'sparkles') return <Sparkles className={cls} aria-hidden />
    if (iconKey === 'calendar') return <CalendarClock className={cls} aria-hidden />
    if (iconKey === 'bell') return <Bell className={cls} aria-hidden />
    return <Bell className={cls} aria-hidden />
  }

  return (
    <>
      <div
        className="fixed inset-0 bg-black/30 z-40 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className="fixed top-0 right-0 h-full w-96 max-w-[calc(100vw-2rem)] bg-white shadow-xl z-50 flex flex-col animate-slide-in"
        role="dialog"
        aria-label="알림"
      >
        <div className="p-4 border-b border-gray-100">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-lg font-bold">알림</h2>
            <button
              onClick={onClose}
              className="p-2 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="알림 닫기"
            >
              <X className="w-5 h-5" aria-hidden />
            </button>
          </div>
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              {unreadCount > 0 ? `새 알림 ${unreadCount}개` : '새 알림 없음'}
            </p>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="flex items-center gap-1.5 text-sm text-primary font-medium hover:underline"
              >
                <CheckCheck className="w-4 h-4" aria-hidden />
                전체 읽음
              </button>
            )}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          <ul className="divide-y divide-gray-100">
            {notifications.map((notification) => (
              <li key={notification.id}>
                <button
                  onClick={() => !notification.read && markAsRead(notification.id)}
                  className={`w-full text-left p-4 hover:bg-gray-50 transition-colors flex gap-3 ${
                    !notification.read ? 'bg-blue-50/50' : ''
                  }`}
                >
                  <span className="flex-shrink-0 mt-0.5">{renderIcon(notification.icon)}</span>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-800 mb-0.5">{notification.title}</p>
                    <p className="text-sm text-gray-500 line-clamp-2">{notification.content}</p>
                    <p className="text-xs text-gray-400 mt-2">{notification.time}</p>
                  </div>
                  {!notification.read && (
                    <span className="flex-shrink-0 w-2 h-2 mt-2 rounded-full bg-primary" />
                  )}
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </>
  )
}
