import { AuthProvider } from '@/context/AuthContext'
import { NotificationProvider } from '@/context/NotificationContext'
import Navbar from '@/components/Navbar'
import AppShell from '@/components/AppShell'
import './globals.css'

export const metadata = {
  title: 'JOBPICK',
  description: 'AI 기반 이력서/채용공고 매칭 서비스',
}

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>
        <AuthProvider>
          <NotificationProvider>
            <Navbar />
            <AppShell>{children}</AppShell>
          </NotificationProvider>
        </AuthProvider>
      </body>
    </html>
  )
}