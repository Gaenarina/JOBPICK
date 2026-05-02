'use client'

import { useState } from 'react'

export default function UploadTestPage() {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState("")

  const handleUpload = async () => {
    if (!file) {
      alert("파일을 선택하세요.")
      return
    }

    const formData = new FormData()
    formData.append("file", file)
    formData.append("userId", "anonymous")

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      })

      const data = await res.json()
      setResult(JSON.stringify(data, null, 2))
    } catch (error) {
      console.error(error)
      setResult("업로드 중 오류 발생")
    }
  }

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-4">업로드 테스트</h1>

      <input
        type="file"
        onChange={(e) => {
          if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0])
          }
        }}
      />

      <button
        onClick={handleUpload}
        className="ml-3 px-4 py-2 bg-blue-600 text-white rounded"
      >
        업로드
      </button>

      <pre className="mt-6 bg-gray-100 p-4 rounded whitespace-pre-wrap">
        {result}
      </pre>
    </main>
  )
}