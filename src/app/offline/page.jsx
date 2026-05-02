export default function OfflinePage() {
  return (
    <main className="max-w-3xl mx-auto p-6 md:p-10">
      <div className="bg-white border border-gray-200 rounded-2xl p-8 text-center">
        <h1 className="text-2xl font-bold mb-2">오프라인 상태입니다</h1>
        <p className="text-gray-600 mb-6">네트워크가 연결되면 다시 시도해 주세요.</p>
        <a href="/" className="inline-flex items-center justify-center px-4 py-2 rounded-lg bg-primary text-white font-medium">
          홈으로 이동
        </a>
      </div>
    </main>
  )
}
