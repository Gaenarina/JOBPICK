'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { addResumes, getResumes, removeResume } from '@/lib/userStorage'

export default function ResumeManagePage() {
  const router = useRouter()
  const { user, isAuthenticated, mounted } = useAuth()
  const resumeUserId = user?.uid || user?.id || ''
  const [resumes, setResumes] = useState([])
  const fileInputRef = useRef(null)

  // 분석 내용 보기 모달용 state
  const [analysisOpen, setAnalysisOpen] = useState(false)
  const [selectedResume, setSelectedResume] = useState(null)
  const [analysisData, setAnalysisData] = useState(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [analysisSaving, setAnalysisSaving] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [editedText, setEditedText] = useState('')

  useEffect(() => {
    if (mounted && !isAuthenticated) router.replace('/login')
    if (mounted && isAuthenticated) setResumes(getResumes(resumeUserId))
  }, [mounted, isAuthenticated, router, resumeUserId])

  if (!mounted || !isAuthenticated) return null

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files || [])
    if (!files.length) return

    const validTypes = ['.pdf', '.doc', '.docx']
    const validFiles = files.filter((f) => {
      const ext = '.' + f.name.split('.').pop().toLowerCase()
      return validTypes.includes(ext)
    })

    if (!validFiles.length) {
      alert('PDF, DOC, DOCX 파일만 업로드 가능합니다.')
      e.target.value = ''
      return
    }

    const dateStr = new Date()
      .toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      })
      .replace(/\. /g, '.')
      .replace(/\.$/, '')

    try {
      const uploadedResumes = []

      for (const file of validFiles) {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('userId', resumeUserId)

        const res = await fetch('/api/resume/upload', {
          method: 'POST',
          body: formData,
        })

        const data = await res.json()

        if (!res.ok) {
          throw new Error(data.error || '업로드 실패')
        }

        // 업로드 성공 후 AI 분석/매칭 시작
        const processRes = await fetch(`/api/resume/${data.docId}/process`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            userId: resumeUserId,
          }),
        })

        const processData = await processRes.json().catch(() => ({}))

        if (!processRes.ok) {
          console.error('AI 분석/매칭 실패:', processData)
          throw new Error(processData.error || 'AI 분석/매칭 실패')
        }

        uploadedResumes.push({
          id: data.docId,
          docId: data.docId,
          name: file.name,
          size: Math.round(file.size / 1024) + ' KB',
          date: dateStr,
          status: processData.status || data.status || 'DONE',
        })
      }

      setResumes(addResumes(uploadedResumes, resumeUserId))
    } catch (error) {
      console.error(error)
      alert(error.message || '이력서 업로드 실패')
    } finally {
      e.target.value = ''
    }
  }

  const handleDeleteResume = (resumeId) => {
    setResumes(removeResume(resumeId, resumeUserId))
  }

  const handleOpenAnalysis = async (resume) => {
    const docId = resume.docId || resume.id

    if (!docId) {
      alert('이력서 문서 ID가 없습니다.')
      return
    }

    setSelectedResume(resume)
    setAnalysisOpen(true)
    setAnalysisLoading(true)
    setAnalysisData(null)
    setEditMode(false)
    setEditedText('')

    try {
      const res = await fetch(`/api/resume/${docId}/analysis`)
      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.error || '분석 결과 조회 실패')
      }

      setAnalysisData(data)

      const editableAnalysis =
        data.effectiveAnalysis ||
        data.editedAnalysis ||
        data.originalAnalysis ||
        data.resume ||
        {}

      setEditedText(JSON.stringify(editableAnalysis, null, 2))
    } catch (error) {
      console.error(error)
      alert('이력서 분석 내용을 불러오지 못했습니다.')
    } finally {
      setAnalysisLoading(false)
    }
  }

  const handleCloseAnalysis = () => {
    setAnalysisOpen(false)
    setSelectedResume(null)
    setAnalysisData(null)
    setEditMode(false)
    setEditedText('')
  }

  const handleSaveAnalysis = async () => {
    const docId = selectedResume?.docId || selectedResume?.id

    if (!docId) {
      alert('이력서 문서 ID가 없습니다.')
      return
    }

    let parsedAnalysis

    try {
      parsedAnalysis = JSON.parse(editedText)
    } catch (error) {
      alert('JSON 형식이 올바르지 않습니다.')
      return
    }

    try {
      setAnalysisSaving(true)

      const res = await fetch(`/api/resume/${docId}/analysis`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          editedAnalysis: parsedAnalysis,
        }),
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.error || '분석 내용 저장 실패')
      }

      setAnalysisData((prev) => ({
        ...prev,
        editedAnalysis: data.editedAnalysis,
        effectiveAnalysis: data.effectiveAnalysis,
        isAnalysisEdited: data.isAnalysisEdited,
        analysisVersion: data.analysisVersion,
        analysisUpdatedAt: data.analysisUpdatedAt || prev?.analysisUpdatedAt,
      }))

      setEditedText(JSON.stringify(data.effectiveAnalysis || parsedAnalysis, null, 2))
      setEditMode(false)
      alert('이력서 분석 내용이 저장되었습니다.')
    } catch (error) {
      console.error(error)
      alert('이력서 분석 내용을 저장하지 못했습니다.')
    } finally {
      setAnalysisSaving(false)
    }
  }

  return (
    <main className="max-w-4xl mx-auto p-8">
      <div className="flex items-center justify-between gap-4 mb-6">
        <h1 className="text-3xl font-bold">이력서 관리</h1>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleUploadClick}
            className="px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors"
          >
            새 이력서 등록하기
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.doc,.docx"
            multiple
            className="hidden"
            onChange={handleFileSelect}
          />
        </div>
      </div>

      {resumes.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-2xl p-8 text-gray-500">
          등록된 이력서가 없습니다.
        </div>
      ) : (
        <div className="space-y-3">
          {resumes.map((resume) => (
            <div
              key={resume.id}
              className="bg-white border border-gray-200 rounded-xl p-4 flex items-center justify-between gap-3"
            >
              <div>
                <p className="font-semibold">{resume.name}</p>
                <p className="text-sm text-gray-500">
                  {resume.size} · {resume.date}
                  {resume.status && ` · ${resume.status}`}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleOpenAnalysis(resume)}
                  className="px-3 py-1 rounded-md bg-blue-50 text-blue-600 text-sm hover:bg-blue-100 transition-colors"
                >
                  분석 내용 보기
                </button>

                <button
                  type="button"
                  onClick={() => handleDeleteResume(resume.id)}
                  className="px-3 py-1 rounded-md bg-red-50 text-red-600 text-sm hover:bg-red-100 transition-colors"
                >
                  삭제
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {analysisOpen && (
        <ResumeAnalysisModal
          selectedResume={selectedResume}
          analysisData={analysisData}
          analysisLoading={analysisLoading}
          analysisSaving={analysisSaving}
          editMode={editMode}
          editedText={editedText}
          setEditMode={setEditMode}
          setEditedText={setEditedText}
          onClose={handleCloseAnalysis}
          onSave={handleSaveAnalysis}
        />
      )}
    </main>
  )
}

function ResumeAnalysisModal({
  selectedResume,
  analysisData,
  analysisLoading,
  analysisSaving,
  editMode,
  editedText,
  setEditMode,
  setEditedText,
  onClose,
  onSave,
}) {
  const analysisRoot =
    analysisData?.effectiveAnalysis ||
    analysisData?.editedAnalysis ||
    analysisData?.originalAnalysis ||
    analysisData?.resume ||
    null

  // Firestore 구조가 effectiveAnalysis.resumeData 형태라서 resumeData를 우선 사용
  const analysis = analysisRoot?.resumeData || analysisRoot

  const skillList = getSkillList(analysis?.skills || analysis?.mentionedSkills)
  const languageList = analysis?.languageTests || analysis?.languages || []
  const activityList = analysis?.activities || []
  const projectList = analysis?.projects || []
  const certificationList = analysis?.certifications || []
  const educationList = analysis?.education || []
  const experienceList = analysis?.experience || []
  const coreCompetencies = analysis?.coreCompetencies || []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-3xl max-h-[85vh] overflow-y-auto bg-white rounded-2xl shadow-xl p-6">
        <div className="flex items-start justify-between gap-4 mb-5">
          <div>
            <h2 className="text-2xl font-bold">이력서 분석 내용</h2>
            <p className="text-sm text-gray-500 mt-1">
              AI가 이력서를 어떻게 분석했는지 확인하고, 필요한 경우 수정할 수 있습니다.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 rounded-md text-gray-500 hover:bg-gray-100"
          >
            닫기
          </button>
        </div>

        {analysisLoading ? (
          <div className="py-12 text-center text-gray-500">
            분석 내용을 불러오는 중입니다...
          </div>
        ) : !analysisData ? (
          <div className="py-12 text-center text-gray-500">
            분석 내용을 불러오지 못했습니다.
          </div>
        ) : (
          <>
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 mb-5 text-sm text-gray-600">
              <p>
                파일명:{' '}
                <span className="font-medium text-gray-800">
                  {analysisData.filename || selectedResume?.name || '-'}
                </span>
              </p>
              <p>
                분석 상태:{' '}
                <span className="font-medium text-gray-800">
                  {analysisData.analysisStatus || '-'}
                </span>
              </p>
              <p>
                수정 여부:{' '}
                <span className="font-medium text-gray-800">
                  {analysisData.isAnalysisEdited ? '수정됨' : '원본 분석 결과'}
                </span>
              </p>
              <p>
                분석 버전:{' '}
                <span className="font-medium text-gray-800">
                  v{analysisData.analysisVersion || 1}
                </span>
              </p>
            </div>

            {!analysis ? (
              <div className="py-10 text-center text-gray-500">
                아직 분석 결과가 없습니다. 이력서 분석이 완료된 뒤 다시 확인해주세요.
              </div>
            ) : editMode ? (
              <div>
                <p className="mb-2 text-sm text-gray-500">
                  아래 JSON 내용을 수정한 뒤 저장하면, 수정된 내용이 effectiveAnalysis에 반영됩니다.
                </p>
                <textarea
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  className="w-full h-96 border border-gray-300 rounded-xl p-4 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-500"
                />
              </div>
            ) : (
              <div className="space-y-4">
                <AnalysisSection title="기본 정보" value={analysis.basicInfo} />
                <AnalysisSection title="희망/분석 직무" value={analysis.jobCategory} />
                <AnalysisSection title="기술 스택" value={skillList} />
                <AnalysisSection title="핵심 역량" value={coreCompetencies} />
                <AnalysisSection title="학력" value={educationList} />
                <AnalysisSection title="경력" value={experienceList} />
                <AnalysisSection title="총 경력" value={analysis.experienceSummary} />
                <AnalysisSection title="자격증" value={certificationList} />
                <AnalysisSection title="어학" value={languageList} />
                <AnalysisSection title="프로젝트" value={projectList} />
                <AnalysisSection title="활동" value={activityList} />
                <AnalysisSection title="자기소개" value={analysis.selfIntroduction} />

                <details className="border border-gray-200 rounded-xl p-4">
                  <summary className="cursor-pointer font-semibold">
                    전체 분석 원본 데이터 보기
                  </summary>
                  <pre className="mt-3 bg-gray-50 rounded-lg p-3 text-xs overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(analysisRoot, null, 2)}
                  </pre>
                </details>
              </div>
            )}

            <div className="flex justify-end gap-2 mt-6">
              {editMode ? (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      setEditMode(false)
                      setEditedText(JSON.stringify(analysisRoot || {}, null, 2))
                    }}
                    className="px-4 py-2 rounded-lg border border-gray-300 text-sm hover:bg-gray-50"
                  >
                    취소
                  </button>

                  <button
                    type="button"
                    onClick={onSave}
                    disabled={analysisSaving}
                    className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:bg-gray-400"
                  >
                    {analysisSaving ? '저장 중...' : '저장하기'}
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => setEditMode(true)}
                  disabled={!analysis}
                  className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:bg-gray-400"
                >
                  수정하기
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function AnalysisSection({ title, value }) {
  return (
    <div className="border border-gray-200 rounded-xl p-4">
      <h3 className="font-semibold mb-2">{title}</h3>

      {Array.isArray(value) ? (
        value.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {value.map((item, index) => (
              <span
                key={index}
                className="px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-sm"
              >
                {typeof item === 'object' ? formatObjectOneLine(item) : String(item)}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">분석된 내용 없음</p>
        )
      ) : typeof value === 'object' && value !== null ? (
        <pre className="bg-gray-50 rounded-lg p-3 text-sm overflow-x-auto whitespace-pre-wrap">
          {JSON.stringify(value, null, 2)}
        </pre>
      ) : (
        <p className="text-sm text-gray-700 whitespace-pre-wrap">
          {value || '분석된 내용 없음'}
        </p>
      )}
    </div>
  )
}

function getSkillList(skills) {
  if (!skills) return []

  if (Array.isArray(skills)) {
    return skills
  }

  if (typeof skills === 'object') {
    return [
      ...(skills.languages || []),
      ...(skills.frameworks || []),
      ...(skills.tools || []),
      ...(skills.etc || []),
    ]
  }

  return [String(skills)]
}

function formatObjectOneLine(value) {
  if (!value || typeof value !== 'object') {
    return String(value || '')
  }

  const parts = []

  if (value.school) parts.push(value.school)
  if (value.major) parts.push(value.major)
  if (value.degree) parts.push(value.degree)
  if (value.status) parts.push(value.status)

  if (value.organization) parts.push(value.organization)
  if (value.position) parts.push(value.position)
  if (value.startDate || value.endDate) {
    parts.push(`${value.startDate || ''}~${value.endDate || ''}`)
  }

  if (value.name) parts.push(value.name)
  if (value.date) parts.push(value.date)
  if (value.grade) parts.push(value.grade)

  if (parts.length > 0) {
    return parts.join(' / ')
  }

  return JSON.stringify(value)
}