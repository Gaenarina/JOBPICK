'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { addResumes, getResumes, removeResume } from '@/lib/userStorage'

export default function ResumeManagePage() {
  const router = useRouter()
  const { user, isAuthenticated, mounted } = useAuth()
  const resumeUserId = user?.uid || user?.id || ''
  const [resumes, setResumes] = useState([])
  const fileInputRef = useRef(null)

  useEffect(() => {
    if (mounted && !isAuthenticated) router.replace('/login')
    if (mounted && isAuthenticated) setResumes(getResumes(resumeUserId))
  }, [mounted, isAuthenticated, router, resumeUserId])

  if (!mounted || !isAuthenticated) return null

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files || [])
    if (!files.length) return

    const validTypes = ['.pdf', '.doc', '.docx']
    const validFiles = files.filter((f) => {
      const ext = '.' + f.name.split('.').pop().toLowerCase()
      return validTypes.includes(ext)
    })

    if (!validFiles.length) {
      alert('PDF, DOC, DOCX 파일만 업로드 가능합니다.')
      e.target.value = ''
      return
    }

    const dateStr = new Date()
      .toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      })
      .replace(/\. /g, '.')
      .replace(/\.$/, '')

    try {
      const uploadedResumes = []

      for (const file of validFiles) {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('userId', resumeUserId)

        const res = await fetch('/api/resume/upload', {
          method: 'POST',
          body: formData,
        })

        const data = await res.json()

        if (!res.ok) {
          throw new Error(data.error || '업로드 실패')
        }

        uploadedResumes.push({
          id: data.docId,
          docId: data.docId,
          name: file.name,
          size: Math.round(file.size / 1024) + ' KB',
          date: dateStr,
          status: data.status || 'INIT',
        })
      }

      setResumes(addResumes(uploadedResumes, resumeUserId))
    } catch (error) {
      console.error(error)
      alert('이력서 업로드 실패')
    } finally {
      e.target.value = ''
    }
  }

  const handleDeleteResume = (resumeId) => {
    setResumes(removeResume(resumeId, resumeUserId))
  }

  return (
    <main className="max-w-4xl mx-auto p-8">
      <div className="flex items-center justify-between gap-4 mb-6">
        <h1 className="text-3xl font-bold">이력서 관리</h1>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleUploadClick}
            className="px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors"
          >
            새 이력서 등록하기
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.doc,.docx"
            multiple
            className="hidden"
            onChange={handleFileSelect}
          />
        </div>
      </div>

      {resumes.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-2xl p-8 text-gray-500">
          등록된 이력서가 없습니다.
        </div>
      ) : (
        <div className="space-y-3">
          {resumes.map((resume) => (
            <div
              key={resume.id}
              className="bg-white border border-gray-200 rounded-xl p-4 flex items-center justify-between gap-3"
            >
              <div>
                <p className="font-semibold">{resume.name}</p>
                <p className="text-sm text-gray-500">
                  {resume.size} · {resume.date}
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleDeleteResume(resume.id)}
                className="px-3 py-1 rounded-md bg-red-50 text-red-600 text-sm hover:bg-red-100 transition-colors"
              >
                삭제
              </button>
            </div>
          ))}
        </div>
      )}
    </main>
  )
}