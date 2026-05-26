'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { ClipboardList, User, Mail, Lock, Eye, EyeOff } from 'lucide-react'

export default function SignupPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false)
  const [termsAgreed, setTermsAgreed] = useState(false)
  const [marketingAgreed, setMarketingAgreed] = useState(false)
  const { signup } = useAuth()
  const router = useRouter()

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!termsAgreed) {
      alert('필수 항목을 모두 입력해주세요.')
      return
    }

    if (password !== passwordConfirm) {
      alert('비밀번호가 일치하지 않습니다.')
      return
    }

    if (password.length < 8) {
      alert('비밀번호는 최소 8자 이상 입력해주세요.')
      return
    }

    try {
      await signup(email, password, name)
      router.replace('/') // 또는 '/dashboard'
    } catch (error) {
      console.error(error)
      alert(`회원가입 실패: ${error.message}`)
    }
  }

  return (
    <main className="min-h-[calc(100vh-60px)] flex items-center justify-center p-8 bg-gradient-to-br from-sky-100 to-sky-50">
      <div className="w-full max-w-[420px] bg-white rounded-2xl p-10 shadow-lg">
        <div className="flex items-center justify-center gap-2 font-bold text-xl text-gray-800 mb-6">
          <ClipboardList className="w-7 h-7 text-primary" aria-hidden />
          <span>JOB PICK</span>
        </div>
        <h1 className="text-2xl font-bold text-center mb-6">회원가입</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium">이름</label>
            <div className="flex items-center border border-gray-200 rounded-lg px-4 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
              <User className="w-4 h-4 text-gray-400 mr-2" aria-hidden />
              <input
                type="text"
                placeholder="홍길동"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="flex-1 py-3 border-none outline-none"
                required
              />
            </div>
          </div>
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
                placeholder="........"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="flex-1 py-3 border-none outline-none"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="ml-1 p-1"
              >
                {showPassword ? <EyeOff className="w-5 h-5 text-gray-600" aria-hidden /> : <Eye className="w-5 h-5 text-gray-600" aria-hidden />}
              </button>
            </div>
            <span className="text-xs text-gray-500">최소 8자 이상 입력해주세요</span>
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium">비밀번호 확인</label>
            <div className="flex items-center border border-gray-200 rounded-lg px-4 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
              <Lock className="w-4 h-4 text-gray-400 mr-2" aria-hidden />
              <input
                type={showPasswordConfirm ? 'text' : 'password'}
                placeholder="........"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                className="flex-1 py-3 border-none outline-none"
                required
              />
              <button
                type="button"
                onClick={() => setShowPasswordConfirm(!showPasswordConfirm)}
                className="ml-1 p-1"
              >
                {showPasswordConfirm ? <EyeOff className="w-5 h-5 text-gray-600" aria-hidden /> : <Eye className="w-5 h-5 text-gray-600" aria-hidden />}
              </button>
            </div>
          </div>
          <div className="flex flex-col gap-3">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={termsAgreed} onChange={(e) => setTermsAgreed(e.target.checked)} required />
              (필수) 이용약관 및 개인정보 처리방침에 동의합니다
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={marketingAgreed} onChange={(e) => setMarketingAgreed(e.target.checked)} />
              (선택) 마케팅 정보 수신에 동의합니다
            </label>
          </div>
          <button
            type="submit"
            className="w-full py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary-dark transition-colors"
          >
            회원가입
          </button>
          <p className="text-center text-sm text-gray-500">
            이미 계정이 있으신가요?{' '}
            <Link href="/login" className="text-primary font-medium hover:underline">
              로그인
            </Link>
          </p>
        </form>
      </div>
    </main>
  )
}
