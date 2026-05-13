'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { ClipboardList, Mail, Lock, Eye, EyeOff } from 'lucide-react'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showForgotPassword, setShowForgotPassword] = useState(false)
  const [resetEmail, setResetEmail] = useState('')
  const [resetSending, setResetSending] = useState(false)
  const { login, sendPasswordReset } = useAuth()
  const router = useRouter()

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!email || !password) return

    try {
      const loggedInUser = await login(email, password)
      console.log('로그인 성공:', loggedInUser)
      alert('로그인 성공')
      router.replace('/')
    } catch (error) {
      console.error('로그인 에러:', error)
      alert(`로그인 실패: ${error.message}`)
    }
  }

  const handlePasswordReset = async (e) => {
    e.preventDefault()
    const target = resetEmail.trim() || email.trim()
    if (!target) {
      alert('이메일을 입력해 주세요.')
      return
    }
    setResetSending(true)
    try {
      await sendPasswordReset(target)
      alert('비밀번호 재설정 링크가 이메일로 전송되었습니다. 메일함을 확인해 주세요.')
      setShowForgotPassword(false)
      setResetEmail('')
    } catch (error) {
      console.error(error)
      alert(error.message || '메일 전송에 실패했습니다.')
    } finally {
      setResetSending(false)
    }
  }

  return (
    <main className="min-h-[calc(100vh-72px)] flex items-center justify-center p-4 sm:p-8 bg-gradient-to-br from-sky-100 to-sky-50">
      <div className="w-full max-w-[420px] bg-white rounded-2xl p-10 shadow-lg">
        <div className="flex items-center justify-center gap-2 font-bold text-xl text-gray-800 mb-6">
          <ClipboardList className="w-7 h-7 text-primary" aria-hidden />
          <span>JOB PICK</span>
        </div>
        <h1 className="text-2xl font-bold text-center mb-6">로그인</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium">이메일</label>
            <div className="flex items-center border border-gray-200 rounded-lg px-4 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
              <Mail className="w-4 h-4 text-gray-400 mr-2" aria-hidden />
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
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium">비밀번호</label>
            <div className="flex items-center border border-gray-200 rounded-lg px-4 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
              <Lock className="w-4 h-4 text-gray-400 mr-2" aria-hidden />
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="********"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="flex-1 py-3 border-none outline-none"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="ml-1 p-1"
                aria-label={showPassword ? '비밀번호 숨기기' : '비밀번호 보기'}
              >
                {showPassword ? <EyeOff className="w-5 h-5 text-gray-600" aria-hidden /> : <Eye className="w-5 h-5 text-gray-600" aria-hidden />}
              </button>
            </div>
          </div>
          <div className="flex justify-between items-center flex-wrap gap-2">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" />
              로그인 상태 유지
            </label>
            <button
              type="button"
              onClick={() => setShowForgotPassword((v) => !v)}
              className="text-primary font-medium hover:underline text-sm"
            >
              비밀번호 찾기
            </button>
          </div>

          {showForgotPassword && (
            <div className="rounded-xl border border-blue-100 bg-sky-50/80 p-4 space-y-3">
              <p className="text-sm text-gray-700">
                가입하신 이메일을 입력하시면 비밀번호 재설정 링크를 보내드립니다.
              </p>
              <form onSubmit={handlePasswordReset} className="flex flex-col gap-2">
                <label className="text-sm font-medium">재설정 받을 이메일</label>
                <input
                  type="email"
                  placeholder="example@email.com"
                  value={resetEmail}
                  onChange={(e) => setResetEmail(e.target.value)}
                  className="w-full py-2.5 px-3 rounded-lg border border-gray-200 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
                <button
                  type="submit"
                  disabled={resetSending}
                  className="w-full py-2.5 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors disabled:opacity-60"
                >
                  {resetSending ? '전송 중...' : '재설정 링크 보내기'}
                </button>
              </form>
            </div>
          )}
          <button
            type="submit"
            className="w-full py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary-dark transition-colors"
          >
            로그인
          </button>
          <p className="text-center text-sm text-gray-500">
            아직 계정이 없으신가요?{' '}
            <Link href="/signup" className="text-primary font-medium hover:underline">
              회원가입
            </Link>
          </p>
        </form>
      </div>
    </main>
  )
}
