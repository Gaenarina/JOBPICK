'use client'

function getUserStorageKey(baseKey, userId) {
  if (userId === undefined || userId === null || String(userId).trim() === '') {
    return null
  }
  return `jobpick_${baseKey}__${String(userId).trim()}`
}

function readJson(key, fallback) {
  if (typeof window === 'undefined' || !key) return fallback
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

function writeJson(key, value) {
  if (typeof window === 'undefined' || !key) return
  localStorage.setItem(key, JSON.stringify(value))
}

export function getResumes(userId) {
  const key = getUserStorageKey('resumes', userId)
  return key ? readJson(key, []) : []
}

export function addResumes(files, userId) {
  const key = getUserStorageKey('resumes', userId)
  if (!key) return []
  const prev = readJson(key, [])
  const merged = [...files, ...prev].slice(0, 20)
  writeJson(key, merged)
  return merged
}

export function removeResume(resumeId, userId) {
  const key = getUserStorageKey('resumes', userId)
  if (!key) return []
  const prev = readJson(key, [])
  const next = prev.filter((item) => item.id !== resumeId)
  writeJson(key, next)
  return next
}

export function getApplications(userId) {
  const key = getUserStorageKey('applications', userId)
  return key ? readJson(key, []) : []
}

export function upsertApplication(application, userId) {
  const key = getUserStorageKey('applications', userId)
  if (!key) return []
  const prev = readJson(key, [])
  const next = [application, ...prev.filter((item) => item.jobId !== application.jobId)]
  writeJson(key, next)
  return next
}

export function getBookmarks(userId) {
  const key = getUserStorageKey('bookmarks', userId)
  return key ? readJson(key, []) : []
}

export function toggleBookmark(job, userId) {
  const key = getUserStorageKey('bookmarks', userId)
  if (!key) return []
  const prev = readJson(key, [])
  const exists = prev.some((item) => item.id === job.id)
  const next = exists ? prev.filter((item) => item.id !== job.id) : [job, ...prev]
  writeJson(key, next)
  return next
}

export function getRecentJobs() {
  return readJson('jobpick_recent_jobs', [])
}

export function pushRecentJob(job) {
  const prev = getRecentJobs()
  const next = [job, ...prev.filter((item) => item.id !== job.id)].slice(0, 20)
  writeJson('jobpick_recent_jobs', next)
  return next
}
