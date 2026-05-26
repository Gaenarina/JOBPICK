'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { getBookmarks, getRecentJobs, getResumes } from '@/lib/userStorage'
import { updateProfile } from 'firebase/auth'
import { doc, serverTimestamp, setDoc } from 'firebase/firestore'
import { ref, uploadBytes, getDownloadURL, deleteObject } from 'firebase/storage'
import { auth, db, storage } from '@/lib/firebase'
import { Camera, FileText, Eye, Building2, PencilLine, Trash2, UserRoundX } from 'lucide-react'

const ACTIVITY_ITEMS = [
  { href: '/mypage/resumes', icon: FileText, label: '이력서 관리', key: 'resumes' },
  { href: '/mypage/recent', icon: Eye, label: '최근 본 공고', key: 'recent' },
  { href: '/mypage/bookmarks', icon: Building2, label: '관심기업', key: 'bookmarks' },
  { href: '/mypage/matching-history', icon: Eye, label: 'AI 매칭 기록', key: 'matching-history' },
]

export default function MyPage() {
  const { user, isAuthenticated, mounted, logout, deleteAccount } = useAuth()
  const router = useRouter()
  const resumeUserId = user?.uid || user?.id || ''
  const avatarInputRef = useRef(null)

  const [nickname, setNickname] = useState('')
  const [savingNickname, setSavingNickname] = useState(false)
  const [uploadingPhoto, setUploadingPhoto] = useState(false)
  const [withdrawStep, setWithdrawStep] = useState(0)
  const [isEditingProfile, setIsEditingProfile] = useState(false)

  useEffect(() => {
    if (mounted && !isAuthenticated) {
      router.replace('/login')
    }
  }, [mounted, isAuthenticated, router])

  useEffect(() => {
    if (user) {
      setNickname(user.displayName || user.email?.split('@')[0] || '')
    }
  }, [user])

  const handleLogout = () => {
    logout()
    router.replace('/')
  }

  const handleSaveNickname = async () => {
    const u = auth.currentUser
    if (!u || !nickname.trim()) return
    setSavingNickname(true)
    try {
      await updateProfile(u, { displayName: nickname.trim() })
      await setDoc(
        doc(db, 'users', u.uid),
        { name: nickname.trim(), updatedAt: serverTimestamp() },
        { merge: true }
      )
      alert('닉네임이 저장되었습니다.')
    } catch (error) {
      console.error(error)
      alert(error.message || '저장에 실패했습니다.')
    } finally {
      setSavingNickname(false)
    }
  }

  const handleAvatarSelect = async (e) => {
    const file = e.target.files?.[0]
    if (!file || !user) return
    if (!file.type.startsWith('image/')) {
      alert('이미지 파일(JPG, PNG 등)만 업로드할 수 있습니다.')
      e.target.value = ''
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      alert('5MB 이하 이미지를 선택해 주세요.')
      e.target.value = ''
      return
    }

    setUploadingPhoto(true)
    try {
      const storageRef = ref(storage, `avatars/${user.uid}/profile`)
      await uploadBytes(storageRef, file)
      const url = await getDownloadURL(storageRef)
      await updateProfile(auth.currentUser, { photoURL: url })
      await setDoc(
        doc(db, 'users', user.uid),
        { photoURL: url, updatedAt: serverTimestamp() },
        { merge: true }
      )
    } catch (error) {
      console.error(error)
      alert(error.message || '프로필 사진 업로드에 실패했습니다.')
    } finally {
      setUploadingPhoto(false)
      e.target.value = ''
    }
  }

  const handleRemovePhoto = async () => {
    const u = auth.currentUser
    if (!u || !user?.photoURL) return

    setUploadingPhoto(true)
    try {
      try {
        await deleteObject(ref(storage, `avatars/${user.uid}/profile`))
      } catch {
        /* 객체가 없을 수 있음 */
      }
      await updateProfile(u, { photoURL: '' })
      await setDoc(
        doc(db, 'users', user.uid),
        { photoURL: '', updatedAt: serverTimestamp() },
        { merge: true }
      )
    } catch (error) {
      console.error(error)
      alert(error.message || '사진 삭제에 실패했습니다.')
    } finally {
      setUploadingPhoto(false)
    }
  }

  const handleWithdrawFinal = async () => {
    try {
      await deleteAccount()
      router.replace('/')
    } catch (error) {
      console.error(error)
      alert(
        error.message ||
          '탈퇴 처리에 실패했습니다. 보안을 위해 다시 로그인한 뒤 시도해 주세요.'
      )
    } finally {
      setWithdrawStep(0)
    }
  }

  if (!mounted || !isAuthenticated) {
    return (
      <main className="min-h-[60vh] flex items-center justify-center">
        <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </main>
    )
  }

  const displayName = user.displayName || user.email?.split('@')[0] || '회원'
  const email = user.email || ''
  const initial = (nickname || displayName).charAt(0)

  const resumes = getResumes(resumeUserId)
  const recentJobs = getRecentJobs()
  const bookmarks = getBookmarks(resumeUserId)
  const statsByKey = {
    resumes: resumes.length,
    recent: recentJobs.length,
    bookmarks: bookmarks.length,
  }

  return (
    <main className="max-w-3xl mx-auto p-4 md:p-8 pb-24 md:pb-8">
      <h1 className="text-2xl md:text-3xl font-bold mb-6">마이페이지</h1>

      {/* 프로필 편집 카드 */}
      <div className="bg-white border border-gray-200 rounded-2xl p-5 md:p-6 shadow-sm mb-8">
        <div className="flex flex-col md:flex-row md:items-start gap-6">
          <div className="flex flex-col items-center md:items-start gap-3">
            <div className="relative w-24 h-24 md:w-28 md:h-28 rounded-2xl bg-slate-100 overflow-hidden flex-shrink-0 ring-1 ring-gray-200">
              {user.photoURL ? (
                <img
                  src={user.photoURL}
                  alt=""
                  className="w-full h-full object-cover"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <div className="w-full h-full bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center text-white text-3xl md:text-4xl font-bold">
                  {initial}
                </div>
              )}
              {uploadingPhoto && (
                <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                  <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
                </div>
              )}
            </div>

            {isEditingProfile && (
              <div className="flex flex-wrap gap-2 justify-center md:justify-start">
                <button
                  type="button"
                  onClick={() => avatarInputRef.current?.click()}
                  disabled={uploadingPhoto}
                  className="inline-flex items-center gap-2 text-sm px-3.5 py-2 rounded-xl bg-slate-900 text-white font-medium hover:bg-slate-800 disabled:opacity-50 transition-colors"
                >
                  <Camera className="w-4 h-4" aria-hidden />
                  사진 업로드
                </button>
                {user.photoURL && (
                  <button
                    type="button"
                    onClick={handleRemovePhoto}
                    disabled={uploadingPhoto}
                    className="inline-flex items-center gap-2 text-sm px-3.5 py-2 rounded-xl bg-white text-gray-700 font-medium border border-gray-200 hover:bg-gray-50 disabled:opacity-50 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" aria-hidden />
                    사진 삭제
                  </button>
                )}
                <input
                  ref={avatarInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleAvatarSelect}
                />
              </div>
            )}
          </div>

          <div className="flex-1 min-w-0 w-full">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-xl md:text-2xl font-bold text-gray-900 truncate">{displayName}</h2>
                <p className="text-sm md:text-base text-gray-500 break-all">{email}</p>
              </div>
              <button
                type="button"
                onClick={() => setIsEditingProfile(!isEditingProfile)}
                className="flex items-center gap-2 text-gray-400 hover:text-primary transition-colors"
                aria-label="프로필 편집"
              >
                <PencilLine className="w-5 h-5" aria-hidden />
              </button>
            </div>

            {isEditingProfile && (
              <div className="mt-5 flex flex-col sm:flex-row gap-2 sm:items-end">
                <div className="flex-1">
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">닉네임</label>
                  <div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2.5 focus-within:ring-2 focus-within:ring-primary/15 focus-within:border-primary">
                    <PencilLine className="w-4 h-4 text-gray-400" aria-hidden />
                    <input
                      type="text"
                      value={nickname}
                      onChange={(e) => setNickname(e.target.value)}
                      maxLength={40}
                      className="w-full bg-transparent outline-none text-base text-gray-800"
                      placeholder="닉네임을 입력하세요"
                    />
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleSaveNickname}
                  disabled={savingNickname || !nickname.trim()}
                  className="shrink-0 inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-white font-medium text-sm hover:bg-primary-dark disabled:opacity-50 transition-colors"
                >
                  {savingNickname ? '저장 중...' : '저장'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 내 활동 */}
      <section className="mb-8">
        <h3 className="text-lg md:text-xl font-bold mb-4">내 활동</h3>
        <div className="bg-white rounded-xl shadow-sm overflow-hidden divide-y divide-gray-100">
          {ACTIVITY_ITEMS.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className="flex items-center justify-between px-4 py-4 hover:bg-gray-50 transition-colors min-h-[52px]"
            >
              <div className="flex items-center gap-3 min-w-0">
                <item.icon className="w-5 h-5 text-gray-500 flex-shrink-0" aria-hidden />
                <span className="font-medium truncate">{item.label}</span>
                {statsByKey[item.key] > 0 && (
                  <span className="px-2 py-0.5 bg-primary text-white text-xs font-medium rounded-full flex-shrink-0">
                    {statsByKey[item.key]}
                  </span>
                )}
              </div>
              <span className="text-gray-400 flex-shrink-0">›</span>
            </Link>
          ))}
        </div>
      </section>

      {/* 로그아웃 버튼 */}
      <button
        onClick={handleLogout}
        className="w-full py-4 rounded-xl border-2 border-red-500 bg-red-50 text-red-600 font-semibold flex items-center justify-center gap-2 hover:bg-red-100 transition-colors"
      >
        <UserRoundX className="w-5 h-5" aria-hidden />
        로그아웃
      </button>

      <div className="mt-6 flex justify-center">
        <button
          type="button"
          onClick={() => setWithdrawStep(1)}
          className="text-xs md:text-sm text-gray-400 hover:text-red-500 underline underline-offset-2 transition-colors"
        >
          회원탈퇴
        </button>
      </div>

      {withdrawStep === 1 && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-2xl p-6 max-w-sm w-full shadow-xl">
            <p className="text-base font-medium text-gray-800 mb-6 text-center">
              정말 탈퇴하시겠습니까?
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setWithdrawStep(0)}
                className="flex-1 py-3 rounded-xl border border-gray-200 text-gray-700 font-medium"
              >
                취소
              </button>
              <button
                type="button"
                onClick={() => setWithdrawStep(2)}
                className="flex-1 py-3 rounded-xl bg-primary text-white font-medium"
              >
                다음
              </button>
            </div>
          </div>
        </div>
      )}

      {withdrawStep === 2 && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-2xl p-6 max-w-sm w-full shadow-xl">
            <p className="text-base font-medium text-gray-800 mb-6 text-center leading-relaxed">
              탈퇴 후 복구할 수 없습니다. 계속하시겠습니까?
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setWithdrawStep(0)}
                className="flex-1 py-3 rounded-xl border border-gray-200 text-gray-700 font-medium"
              >
                취소
              </button>
              <button
                type="button"
                onClick={handleWithdrawFinal}
                className="flex-1 py-3 rounded-xl bg-red-600 text-white font-medium"
              >
                탈퇴하기
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
