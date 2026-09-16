'use client'

import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import {
  collection,
  doc,
  onSnapshot,
  updateDoc,
  writeBatch,
} from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { useAuth } from '@/context/AuthContext'

const NotificationContext = createContext(null)

function toMillis(createdAt) {
  if (!createdAt) return 0
  if (typeof createdAt.toMillis === 'function') return createdAt.toMillis()
  if (typeof createdAt.toDate === 'function') return createdAt.toDate().getTime()
  if (typeof createdAt.seconds === 'number') return createdAt.seconds * 1000
  const parsed = new Date(createdAt)
  const time = parsed.getTime()
  return Number.isNaN(time) ? 0 : time
}

function formatNotificationTime(createdAt) {
  const createdAtMs = toMillis(createdAt)
  if (!createdAtMs) return ''

  const diffMs = Date.now() - createdAtMs
  const minutes = Math.floor(diffMs / 60000)

  if (minutes < 1) return '방금 전'
  if (minutes < 60) return `${minutes}분 전`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}시간 전`

  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}일 전`

  return new Date(createdAtMs).toLocaleDateString('ko-KR')
}

function mapNotificationDoc(docSnap) {
  const data = docSnap.data() || {}

  return {
    id: docSnap.id,
    category: data.category || 'company',
    icon: data.icon || 'sparkles',
    title: data.title || '',
    content: data.content || '',
    time: formatNotificationTime(data.createdAt),
    read: Boolean(data.read),
    createdAtMs: toMillis(data.createdAt),
  }
}

export function NotificationProvider({ children }) {
  const { user } = useAuth()
  const [notifications, setNotifications] = useState([])
  const uid = user?.uid || null

  useEffect(() => {
    if (!uid) {
      setNotifications([])
      return undefined
    }

    const notificationsRef = collection(db, 'users', uid, 'notifications')

    const unsubscribe = onSnapshot(
      notificationsRef,
      (snapshot) => {
        const next = snapshot.docs
          .map(mapNotificationDoc)
          .sort((a, b) => (b.createdAtMs || 0) - (a.createdAtMs || 0))
          .map(({ createdAtMs, ...notification }) => notification)

        setNotifications(next)
      },
      (error) => {
        console.error('알림 구독 실패:', error)
        setNotifications([])
      }
    )

    return () => unsubscribe()
  }, [uid])

  const unreadCount = notifications.filter((n) => !n.read).length

  const markAsRead = useCallback(
    async (id) => {
      if (!uid || !id) return

      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      )

      try {
        await updateDoc(doc(db, 'users', uid, 'notifications', String(id)), {
          read: true,
        })
      } catch (error) {
        console.error('알림 읽음 처리 실패:', error)
      }
    },
    [uid]
  )

  const markAllAsRead = useCallback(async () => {
    if (!uid) return

    const unread = notifications.filter((n) => !n.read)
    if (!unread.length) return

    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))

    try {
      const batch = writeBatch(db)
      unread.forEach((n) => {
        batch.update(doc(db, 'users', uid, 'notifications', String(n.id)), {
          read: true,
        })
      })
      await batch.commit()
    } catch (error) {
      console.error('알림 전체 읽음 처리 실패:', error)
    }
  }, [notifications, uid])

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
