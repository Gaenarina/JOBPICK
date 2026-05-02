'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'

function InputIconLock() {
  const common = { stroke: '#64748b', strokeWidth: '2', fill: 'none', strokeLinecap: 'round', strokeLinejoin: 'round' }
  return (
    <svg width="18" height="18" viewBox="0 0 24 24">
      <rect x="5.5" y="10.5" width="13" height="9.5" rx="2" {...common} />
      <path d="M8.5 10.5V8.5C8.5 6.6 10.1 5 12 5C13.9 5 15.5 6.6 15.5 8.5V10.5" {...common} />
    </svg>
  )
}

export default function ResetPasswordPage() {
  const router = useRouter()
  const { resetPasswordWithToken, mounted } = useAuth()
  const [token, setToken] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    setToken(params.get('token') || '')
  }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    setErrorMessage('')
    setSuccessMessage('')
    if (!token) {
      setErrorMessage('유효하지 않은 링크입니다.')
      return
    }
    if (password !== passwordConfirm) {
      setErrorMessage('비밀번호가 일치하지 않습니다.')
      return
    }
    if (password.length < 8) {
      setErrorMessage('비밀번호는 최소 8자 이상 입력해주세요.')
      return
    }
    const result = resetPasswordWithToken(token, password)
    if (!result.ok) {
      setErrorMessage('링크가 만료되었거나 유효하지 않습니다. 비밀번호 찾기를 다시 시도해 주세요.')
      return
    }
    setSuccessMessage('비밀번호가 변경되었습니다. 다시 로그인해주세요.')
    setTimeout(() => {
      router.replace('/login')
    }, 2000)
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
        <h1 className="text-2xl font-bold text-center mb-6">새 비밀번호 설정</h1>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium">새 비밀번호</label>
            <div className="flex items-center border border-gray-200 rounded-lg px-4 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
              <span className="mr-2 opacity-80">
                <InputIconLock />
              </span>
              <input
                type="password"
                placeholder="8자 이상"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="flex-1 py-3 border-none outline-none"
                required
                minLength={8}
              />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium">새 비밀번호 확인</label>
            <div className="flex items-center border border-gray-200 rounded-lg px-4 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
              <span className="mr-2 opacity-80">
                <InputIconLock />
              </span>
              <input
                type="password"
                placeholder="한 번 더 입력"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                className="flex-1 py-3 border-none outline-none"
                required
                minLength={8}
              />
            </div>
          </div>
          <button
            type="submit"
            className="w-full py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary-dark transition-colors"
          >
            비밀번호 변경하기
          </button>
          {errorMessage && <p className="text-sm text-red-600 text-center">{errorMessage}</p>}
          {successMessage && <p className="text-sm text-green-700 text-center font-medium">{successMessage}</p>}
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
