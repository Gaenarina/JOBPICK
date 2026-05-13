'use client'

import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import {
  onAuthStateChanged,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  sendPasswordResetEmail,
  deleteUser,
} from 'firebase/auth'
import { doc, serverTimestamp, setDoc } from 'firebase/firestore'
import { auth, db } from '@/lib/firebase'
import { updateProfile } from 'firebase/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setUser(firebaseUser)
      setLoading(false)
    })

    return () => unsubscribe()
  }, [])

  const signup = async (email, password, name = '') => {
    const credential = await createUserWithEmailAndPassword(auth, email, password)

    await updateProfile(credential.user, {
      displayName: name,
    })

    await setDoc(
      doc(db, 'users', credential.user.uid),
      {
        uid: credential.user.uid,
        email: credential.user.email,
        name,
        createdAt: serverTimestamp(),
        updatedAt: serverTimestamp(),
      },
      { merge: true }
    )

    return credential.user
  }

  const login = async (email, password) => {
    const credential = await signInWithEmailAndPassword(auth, email, password)
    return credential.user
  }

  const logout = async () => {
    await signOut(auth)
  }

  const sendPasswordReset = async (email) => {
    await sendPasswordResetEmail(auth, email)
  }

  const deleteAccount = async () => {
    if (!auth.currentUser) {
      throw new Error('로그인이 필요합니다.')
    }
    await deleteUser(auth.currentUser)
  }

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      signup,
      logout,
      sendPasswordReset,
      deleteAccount,
      isAuthenticated: !!user,
      mounted: !loading,
    }),
    [user, loading]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}