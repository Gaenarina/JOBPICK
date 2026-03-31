import { AuthProvider } from '@/context/AuthContext'
import { NotificationProvider } from '@/context/NotificationContext'
import Navbar from '@/components/Navbar'
import './globals.css'

export const metadata = {
  title: 'JOB PICK - AI 기반 이력서/채용공고 매칭',
  description: 'AI 기반 이력서/채용공고 매칭 서비스',
}

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-slate-50 text-gray-800">
        <AuthProvider>
          <NotificationProvider>
            <Navbar />
            {children}
          </NotificationProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
