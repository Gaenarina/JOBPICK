const VERSION = 'jobpick-sw-v3'
const STATIC_CACHE = `${VERSION}-static`

const OFFLINE_URL = '/offline'

const PRECACHE_URLS = [OFFLINE_URL]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => !key.startsWith(VERSION)).map((key) => caches.delete(key)))
      )
      .then(() => self.clients.claim())
  )
})

function shouldSkipRequest(request) {
  if (request.method !== 'GET') {
    return true
  }

  try {
    const url = new URL(request.url)

    if (url.origin !== self.location.origin) {
      return true
    }

    if (url.pathname.startsWith('/api/')) {
      return true
    }

    if (url.pathname.startsWith('/_next/')) {
      return true
    }

    if (url.pathname.startsWith('/__nextjs')) {
      return true
    }

    return false
  } catch {
    return true
  }
}

self.addEventListener('fetch', (event) => {
  const { request } = event

  if (shouldSkipRequest(request)) {
    return
  }

  if (request.mode !== 'navigate') {
    return
  }

  event.respondWith(
    fetch(request).catch(async () => {
      const offlinePage = await caches.match(OFFLINE_URL)
      if (offlinePage) {
        return offlinePage
      }

      throw new Error('offline page unavailable')
    })
  )
})
