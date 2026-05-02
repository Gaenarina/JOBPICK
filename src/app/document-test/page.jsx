'use client'

import { useState } from 'react'

export default function DocumentTestPage() {
  const [docId, setDocId] = useState('')
  const [result, setResult] = useState('')
  const [file, setFile] = useState(null)

  const handleUpload = async () => {
    if (!file) {
      alert('파일을 먼저 선택하세요.')
      return
    }

    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch('/api/resume/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.error || '업로드 실패')
      }

      if (data.docId) {
        setDocId(data.docId)
      }

      setResult(JSON.stringify(data, null, 2))
    } catch (error) {
      setResult(
        JSON.stringify(
          { error: error.message || '업로드 중 오류가 발생했습니다.' },
          null,
          2
        )
      )
    }
  }

  const handleGet = async () => {
    if (!docId) {
      alert('docId를 입력하세요.')
      return
    }

    try {
      const res = await fetch(`/api/documents/${docId}`)
      const data = await res.json()
      setResult(JSON.stringify(data, null, 2))
    } catch (error) {
      setResult(
        JSON.stringify(
          { error: error.message || '문서 조회 중 오류가 발생했습니다.' },
          null,
          2
        )
      )
    }
  }

  const handleProcessing = async () => {
    if (!docId) {
      alert('docId를 입력하세요.')
      return
    }

    try {
      const res = await fetch(`/api/documents/${docId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: 'PROCESSING',
        }),
      })

      const data = await res.json()
      setResult(JSON.stringify(data, null, 2))
    } catch (error) {
      setResult(
        JSON.stringify(
          { error: error.message || '상태 변경 중 오류가 발생했습니다.' },
          null,
          2
        )
      )
    }
  }

  const handleDone = async () => {
    if (!docId) {
      alert('docId를 입력하세요.')
      return
    }

    try {
      const res = await fetch(`/api/documents/${docId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: 'DONE',
          result: {
            score: 0.82,
            message: 'AI 분석 완료(임시)',
          },
        }),
      })

      const data = await res.json()
      setResult(JSON.stringify(data, null, 2))
    } catch (error) {
      setResult(
        JSON.stringify(
          { error: error.message || 'DONE 처리 중 오류가 발생했습니다.' },
          null,
          2
        )
      )
    }
  }

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-4">문서 상태 테스트</h1>

      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-2">1. 이력서 업로드</h2>

        <div className="flex items-center gap-3 flex-wrap">
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                setFile(e.target.files[0])
              }
            }}
            className="border px-3 py-2 rounded"
          />

          <button
            onClick={handleUpload}
            className="px-4 py-2 bg-blue-600 text-white rounded"
          >
            이력서 업로드
          </button>
        </div>
      </div>

      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-2">2. docId 확인 및 문서 테스트</h2>

        <input
          value={docId}
          onChange={(e) => setDocId(e.target.value)}
          placeholder="docId 입력"
          className="border px-3 py-2 rounded w-full max-w-xl"
        />

        <div className="flex gap-3 mt-4 flex-wrap">
          <button
            onClick={handleGet}
            className="px-4 py-2 bg-gray-700 text-white rounded"
          >
            문서 조회
          </button>

          <button
            onClick={handleProcessing}
            className="px-4 py-2 bg-orange-500 text-white rounded"
          >
            PROCESSING
          </button>

          <button
            onClick={handleDone}
            className="px-4 py-2 bg-green-600 text-white rounded"
          >
            DONE
          </button>
        </div>
      </div>
    
      <pre className="mt-6 bg-gray-100 p-4 rounded whitespace-pre-wrap">
        {result}
      </pre>
    </main>
  )
}