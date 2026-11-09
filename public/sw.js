/*
 * JOBPICK PWA Service Worker
 * - 정적 리소스: 캐시 우선
 * - 공개 채용공고 목록: 캐시 즉시 표시 + 백그라운드 업데이트
 * - 페이지 이동: 네트워크 우선 + 오프라인 안내
 * - 이력서/로그인/AI 매칭/사용자 API: 절대 캐싱하지 않음
 */

const VERSION = 'jobpick-pwa-v4'
const STATIC_CACHE = `${VERSION}-static`
const JOBS_CACHE = `${VERSION}-public-jobs`
const CACHE_NAMES = [STATIC_CACHE, JOBS_CACHE]

const OFFLINE_URL = '/offline'

// 이미 저장소에 존재하는 로고만 활용한다. 새 아이콘 파일은 만들지 않는다.
const PRECACHE_URLS = [
  OFFLINE_URL,
  '/manifest.json',
  '/brand-logo.svg',
  '/jobpick-logo.png',
]

const MAX_STATIC_ITEMS = 80
const STATIC_PATHS = new Set(['/brand-logo.svg', '/jobpick-logo.png', '/manifest.json'])

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys()
    await Promise.all(
      keys
        .filter((key) => {
          const ours = key.startsWith('jobpick-pwa-') || key.startsWith('jobpick-sw-')
          return ours && !CACHE_NAMES.includes(key)
        })
        .map((key) => caches.delete(key))
    )
    await self.clients.claim()
  })())
})

function isSameOrigin(url) {
  return url.origin === self.location.origin
}

function isPublicJobsRequest(url) {
  // Query string이 없을 때만 캐싱한다.
  return url.pathname === '/api/job-postings' && url.search === ''
}

function isStaticResource(url) {
  return url.pathname.startsWith('/_next/static/') || STATIC_PATHS.has(url.pathname)
}

async function limitStaticCache(cache) {
  const keys = await cache.keys()
  if (keys.length <= MAX_STATIC_ITEMS) return

  await Promise.all(
    keys.slice(0, keys.length - MAX_STATIC_ITEMS).map((key) => cache.delete(key))
  )
}

function serveStatic(request, event) {
  event.respondWith((async () => {
    const cache = await caches.open(STATIC_CACHE)
    const cached = await cache.match(request)
    if (cached) return cached

    const response = await fetch(request)
    if (response.ok && response.type === 'basic') {
      try {
        await cache.put(request, response.clone())
        await limitStaticCache(cache)
      } catch (error) {
        console.warn('[JOBPICK PWA] 정적 캐시 실패:', error)
      }
    }
    return response
  })())
}

function servePublicJobs(request, event) {
  // 공개 공고만 다룬다. POST 매칭 요청이나 개인 API 응답은 대상이 아니다.
  const networkResponse = fetch(request)

  const refreshCache = networkResponse
    .then(async (response) => {
      const type = response.headers.get('content-type') || ''
      if (!response.ok || response.type !== 'basic' || !type.includes('application/json')) return

      // 네트워크 응답이 브라우저에서 소비되기 전에 복제한다.
      const copy = response.clone()
      const cache = await caches.open(JOBS_CACHE)
      await cache.put(request, copy)
    })
    .catch(() => {})

  // 캐시된 공고를 사용하더라도 네트워크에서 새 데이터를 가져와 다음 요청에 반영한다.
  event.waitUntil(refreshCache)

  event.respondWith((async () => {
    const cache = await caches.open(JOBS_CACHE)
    const cached = await cache.match(request)
    if (cached) return cached

    // 최초 요청에는 캐시가 없으므로 실제 API 응답을 기다린다.
    return networkResponse
  })())
}

function serveNavigation(request, event) {
  event.respondWith((async () => {
    try {
      return await fetch(request)
    } catch (_error) {
      const cachedOffline = await caches.match(OFFLINE_URL)
      return cachedOffline || Response.error()
    }
  })())
}

self.addEventListener('fetch', (event) => {
  const request = event.request
  if (request.method !== 'GET') return

  let url
  try {
    url = new URL(request.url)
  } catch (_error) {
    return
  }

  if (!isSameOrigin(url)) return

  // 오직 공개 채용공고 API만 선택적으로 캐싱한다.
  // 브라우저 fetch()의 cache: 'no-store'와 별개인 Cache Storage 캐시다.
  if (isPublicJobsRequest(url)) {
    servePublicJobs(request, event)
    return
  }

  // 로그인/이력서/매칭 등 다른 모든 API 요청은 브라우저/서버에 그대로 맡긴다.
  if (url.pathname.startsWith('/api/')) return

  // Next.js가 사용하는 해시된 JS/CSS와 공개 로고만 정적 캐싱한다.
  if (isStaticResource(url)) {
    serveStatic(request, event)
    return
  }

  // 앱 페이지는 항상 온라인 최신 버전을 우선 사용한다.
  if (request.mode === 'navigate') {
    serveNavigation(request, event)
  }
})
