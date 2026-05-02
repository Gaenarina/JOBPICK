'use client'

import { useEffect } from 'react'

export default function ServiceWorkerRegistration() {
  useEffect(() => {
    if (typeof window === 'undefined') return
    if (!('serviceWorker' in navigator)) return

    const register = async () => {
      try {
        const reg = await navigator.serviceWorker.register('/sw.js', { scope: '/' })
        if (process.env.NODE_ENV !== 'production') {
          console.info('[PWA] service worker registered', { scope: reg.scope })
        }
      } catch (error) {
        console.warn('[PWA] service worker registration failed', error)
      }
    }

    register()
  }, [])

  return null
}
