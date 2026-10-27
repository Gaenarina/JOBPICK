import { AuthProvider } from '@/context/AuthContext'
import { NotificationProvider } from '@/context/NotificationContext'
import Navbar from '@/components/Navbar'
import AppShell from '@/components/AppShell'
import ServiceWorkerRegistration from '@/components/ServiceWorkerRegistration'
import './globals.css'

export const metadata = {
  title: 'JOBPICK',
  description: 'AI 기반 이력서/채용공고 매칭 서비스',
  applicationName: 'JOBPICK',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    title: 'JOBPICK',
    statusBarStyle: 'default',
  },
}

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#2563eb',
}

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>
        <AuthProvider>
          <NotificationProvider>
            <ServiceWorkerRegistration />
            <Navbar />
            <AppShell>{children}</AppShell>
          </NotificationProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
