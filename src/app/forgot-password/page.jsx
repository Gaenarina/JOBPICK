'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/context/AuthContext'

function InputIconMail() {
  const common = { stroke: '#64748b', strokeWidth: '2', fill: 'none', strokeLinecap: 'round', strokeLinejoin: 'round' }
  return (
    <svg width="18" height="18" viewBox="0 0 24 24">
      <rect x="3.5" y="6" width="17" height="12" rx="2" {...common} />
      <path d="M4.5 7L12 12.5L19.5 7" {...common} />
    </svg>
  )
}

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [sentUrl, setSentUrl] = useState('')
  const { requestPasswordReset, mounted } = useAuth()

  const handleSubmit = (e) => {
    e.preventDefault()
    setErrorMessage('')
    setSentUrl('')
    if (!email.trim()) return

    const result = requestPasswordReset(email.trim())
    if (!result.ok && result.reason === 'not_found') {
      setErrorMessage('가입된 메일이 아닙니다. 다시 확인해주세요.')
      return
    }
    if (result.ok && result.resetUrl) {
      setSentUrl(result.resetUrl)
    }
  }

  if (!mounted) {
    return (
      <main className="min-h-[calc(100vh-60px)] flex items-center justify-center p-8">
        <div className="animate-spin w-10 h-10 border-2 border-primary border-t-transparent rounded-full" />
      </main>
    )
  }

  return (
    <main className="min-h-[calc(100vh-60px)] flex items-center justify-center py-20 px-8 bg-gradient-to-br from-sky-100 to-sky-50">
      <div className="w-full max-w-[560px] bg-white rounded-2xl p-12 min-h-[560px] shadow-lg flex flex-col justify-center">
        <div className="flex items-center justify-center gap-2 font-bold text-xl text-gray-800 mb-6">
          <img src="/brand-logo.svg" alt="JOB PICK 로고" className="w-8 h-8 object-contain" />
          <span>JOB PICK</span>
        </div>
        <h1 className="text-2xl font-bold text-center mb-2">비밀번호 찾기</h1>
        <p className="text-sm text-gray-500 text-center mb-6">가입하신 이메일을 입력해 주세요. 비밀번호 재설정 링크를 보내드립니다.</p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium">이메일</label>
            <div className="flex items-center border border-gray-200 rounded-lg px-4 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
              <span className="mr-2 opacity-80">
                <InputIconMail />
              </span>
              <input
                type="email"
                placeholder="example@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="flex-1 py-3 border-none outline-none"
                required
              />
            </div>
          </div>
          <button
            type="submit"
            className="w-full py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary-dark transition-colors"
          >
            재설정 링크 보내기
          </button>
          {errorMessage && <p className="text-sm text-red-600 text-center">{errorMessage}</p>}
          {sentUrl && (
            <div className="rounded-lg border border-blue-200 bg-blue-50/80 p-4 text-sm text-gray-700">
              <p className="font-medium text-primary mb-2">비밀번호 재설정 링크가 발송되었습니다.</p>
              <p className="text-xs text-gray-600 mb-2">
                (데모 환경에서는 실제 메일 대신 아래 링크를 사용해 주세요.)
              </p>
              <a href={sentUrl} className="text-primary break-all underline font-medium">
                {sentUrl}
              </a>
            </div>
          )}
          <p className="text-center text-sm text-gray-500">
            <Link href="/login" className="text-primary font-medium hover:underline">
              로그인으로 돌아가기
            </Link>
          </p>
        </form>
      </div>
    </main>
  )
}
