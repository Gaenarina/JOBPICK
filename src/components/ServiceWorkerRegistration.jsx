'use client'

import { useEffect } from 'react'

export default function ServiceWorkerRegistration() {
  useEffect(() => {
    // 개발 서버에서는 이전 캐시로 인해 코드 변경 사항이 가려지는 일을 방지한다.
    if (process.env.NODE_ENV !== 'production') return
    if (!('serviceWorker' in navigator)) return

    const register = async () => {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js', {
          scope: '/',
          updateViaCache: 'none',
        })

        // 페이지 재방문 시 SW 변경 사항을 확인한다.
        await registration.update()
      } catch (error) {
        console.warn('[JOBPICK PWA] Service Worker 등록 실패:', error)
      }
    }

    if (document.readyState === 'complete') {
      register()
      return
    }

    window.addEventListener('load', register, { once: true })
    return () => window.removeEventListener('load', register)
  }, [])

  return null
}
