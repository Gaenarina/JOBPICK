'use client'

const RESUME_KEY = 'jobpick_resumes'
const APPLICATION_KEY = 'jobpick_applications'
const RECENT_KEY = 'jobpick_recent_jobs'
const BOOKMARK_KEY = 'jobpick_bookmarks'

/*   */
function readJson(key, fallback) {
  if (typeof window === 'undefined') return fallback
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

function writeJson(key, value) {
  if (typeof window === 'undefined') return
  localStorage.setItem(key, JSON.stringify(value))
}

export function getResumes() {
  return readJson(RESUME_KEY, [])
}

export function addResumes(files) {
  const prev = getResumes()
  const merged = [...files, ...prev].slice(0, 20)
  writeJson(RESUME_KEY, merged)
  return merged
}

export function removeResume(resumeId) {
  const prev = getResumes()
  const next = prev.filter((item) => item.id !== resumeId)
  writeJson(RESUME_KEY, next)
  return next
}

export function getApplications() {
  return readJson(APPLICATION_KEY, [])
}

export function upsertApplication(application) {
  const prev = getApplications()
  const next = [application, ...prev.filter((item) => item.jobId !== application.jobId)]
  writeJson(APPLICATION_KEY, next)
  return next
}

export function getRecentJobs() {
  return readJson(RECENT_KEY, [])
}

export function pushRecentJob(job) {
  const prev = getRecentJobs()
  const next = [job, ...prev.filter((item) => item.id !== job.id)].slice(0, 20)
  writeJson(RECENT_KEY, next)
  return next
}

export function getBookmarks() {
  return readJson(BOOKMARK_KEY, [])
}

export function toggleBookmark(job) {
  const prev = getBookmarks()
  const exists = prev.some((item) => item.id === job.id)
  const next = exists ? prev.filter((item) => item.id !== job.id) : [job, ...prev]
  writeJson(BOOKMARK_KEY, next)
  return next
}
