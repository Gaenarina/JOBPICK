'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { addResumes, getResumes, removeResume } from '@/lib/userStorage'


function deepClone(value) {
  if (value === undefined) return undefined
  return JSON.parse(JSON.stringify(value))
}

function getAnalysisRoot(data) {
  return (
    data?.effectiveAnalysis ||
    data?.editedAnalysis ||
    data?.originalAnalysis ||
    data?.resume ||
    null
  )
}

function toStringArray(value) {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => String(item ?? '').trim())
    .filter(Boolean)
}

function normalizeObjectList(value, emptyItem, textField = 'description') {
  if (!Array.isArray(value)) return []

  return value.map((item) => {
    if (item && typeof item === 'object' && !Array.isArray(item)) {
      return {
        ...deepClone(emptyItem),
        ...deepClone(item),
      }
    }

    return {
      ...deepClone(emptyItem),
      [textField]: String(item ?? ''),
    }
  })
}

function createResumeEditForm(resumeData = {}) {
  const source = resumeData && typeof resumeData === 'object' ? resumeData : {}
  const sourceSkills =
    source.skills && typeof source.skills === 'object' && !Array.isArray(source.skills)
      ? source.skills
      : source.mentionedSkills &&
          typeof source.mentionedSkills === 'object' &&
          !Array.isArray(source.mentionedSkills)
        ? source.mentionedSkills
        : {}

  return {
    ...deepClone(source),
    basicInfo: {
      name: '',
      address: '',
      birthDate: '',
      phone: '',
      age: '',
      email: '',
      ...(deepClone(source.basicInfo) || {}),
    },
    jobCategory: source.jobCategory || '',
    skills: {
      ...(deepClone(sourceSkills) || {}),
      languages: toStringArray(sourceSkills.languages),
      frameworks: toStringArray(sourceSkills.frameworks),
      tools: toStringArray(sourceSkills.tools),
      etc: toStringArray(sourceSkills.etc),
    },
    coreCompetencies: toStringArray(source.coreCompetencies),
    education: normalizeObjectList(
      source.education,
      {
        school: '',
        major: '',
        minor: '',
        degree: '',
        status: '',
        startDate: '',
        endDate: '',
        gpa: '',
      },
      'school'
    ),
    experience: normalizeObjectList(
      source.experience,
      {
        organization: '',
        department: '',
        position: '',
        role: '',
        startDate: '',
        endDate: '',
        description: '',
      }
    ),
    certifications: normalizeObjectList(
      source.certifications,
      {
        name: '',
        grade: '',
        date: '',
      },
      'name'
    ),
    languageTests: normalizeObjectList(
      source.languageTests || source.languages,
      {
        language: '',
        testName: '',
        score: '',
        date: '',
      },
      'testName'
    ),
    projects: normalizeObjectList(
      source.projects,
      {
        name: '',
        role: '',
        startDate: '',
        endDate: '',
        description: '',
        technologies: [],
      }
    ).map((item) => ({
      ...item,
      technologies: toStringArray(item.technologies || item.skills),
    })),
    activities: normalizeObjectList(
      source.activities,
      {
        name: '',
        organization: '',
        role: '',
        startDate: '',
        endDate: '',
        description: '',
      }
    ),
    selfIntroduction: source.selfIntroduction || '',
  }
}

function hasMeaningfulValue(value) {
  if (value === null || value === undefined) return false
  if (typeof value === 'string') return Boolean(value.trim())
  if (typeof value === 'number' || typeof value === 'boolean') return true
  if (Array.isArray(value)) return value.some(hasMeaningfulValue)
  if (typeof value === 'object') return Object.values(value).some(hasMeaningfulValue)
  return false
}

function cleanTagList(value) {
  return [...new Set(toStringArray(value))]
}

function prepareResumeDataForSave(editForm) {
  const form = createResumeEditForm(editForm || {})
  const ageText = String(form.basicInfo?.age ?? '').trim()
  const parsedAge = ageText === '' ? '' : Number(ageText)

  return {
    ...form,
    basicInfo: {
      ...form.basicInfo,
      age: ageText === '' || !Number.isFinite(parsedAge) ? ageText : parsedAge,
    },
    skills: {
      ...form.skills,
      languages: cleanTagList(form.skills?.languages),
      frameworks: cleanTagList(form.skills?.frameworks),
      tools: cleanTagList(form.skills?.tools),
      etc: cleanTagList(form.skills?.etc),
    },
    coreCompetencies: cleanTagList(form.coreCompetencies),
    education: (form.education || []).filter(hasMeaningfulValue),
    experience: (form.experience || []).filter(hasMeaningfulValue),
    certifications: (form.certifications || []).filter(hasMeaningfulValue),
    languageTests: (form.languageTests || []).filter(hasMeaningfulValue),
    projects: (form.projects || [])
      .map((item) => ({
        ...item,
        technologies: cleanTagList(item.technologies),
      }))
      .filter(hasMeaningfulValue),
    activities: (form.activities || []).filter(hasMeaningfulValue),
  }
}

function mergeResumeData(originalResumeData, editedResumeData) {
  const original =
    originalResumeData && typeof originalResumeData === 'object'
      ? originalResumeData
      : {}

  return {
    ...deepClone(original),
    ...deepClone(editedResumeData),
    basicInfo: {
      ...(deepClone(original.basicInfo) || {}),
      ...(deepClone(editedResumeData.basicInfo) || {}),
    },
    skills: {
      ...(deepClone(original.skills) || {}),
      ...(deepClone(editedResumeData.skills) || {}),
    },
  }
}

function buildEditedAnalysis(analysisRoot, editForm) {
  const root = analysisRoot && typeof analysisRoot === 'object' ? analysisRoot : {}
  const preparedResumeData = prepareResumeDataForSave(editForm)

  if (root.resumeData && typeof root.resumeData === 'object') {
    return {
      ...deepClone(root),
      resumeData: mergeResumeData(root.resumeData, preparedResumeData),
    }
  }

  return mergeResumeData(root, preparedResumeData)
}

export default function ResumeManagePage() {
  const router = useRouter()
  const { user, isAuthenticated, mounted } = useAuth()
  const resumeUserId = user?.uid || user?.id || ''
  const [resumes, setResumes] = useState([])
  const [selectedResumeId, setSelectedResumeId] = useState('')
  const fileInputRef = useRef(null)

  // 분석 내용 보기 모달용 state
  const [analysisOpen, setAnalysisOpen] = useState(false)
  const [selectedResume, setSelectedResume] = useState(null)
  const [analysisData, setAnalysisData] = useState(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [analysisSaving, setAnalysisSaving] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [editForm, setEditForm] = useState(null)

  useEffect(() => {
    if (mounted && !isAuthenticated) {
      router.replace('/login')
      return
    }

    if (mounted && isAuthenticated) {
      const savedResumes = getResumes(resumeUserId)
      setResumes(savedResumes)

      // 이 페이지에서 마지막으로 선택했던 이력서를 복원합니다.
      // 저장된 선택값이 없거나 삭제된 이력서라면 첫 번째 이력서를 기본 선택합니다.
      const storageKey = `jobpick-selected-resume-${resumeUserId}`
      const savedSelectedResumeId =
        typeof window !== 'undefined' ? localStorage.getItem(storageKey) : ''

      const hasSavedResume = savedResumes.some(
        (resume) => (resume.docId || resume.id) === savedSelectedResumeId
      )

      const initialSelectedId = hasSavedResume
        ? savedSelectedResumeId
        : savedResumes[0]?.docId || savedResumes[0]?.id || ''

      setSelectedResumeId(initialSelectedId)

      if (typeof window !== 'undefined') {
        if (initialSelectedId) {
          localStorage.setItem(storageKey, initialSelectedId)
        } else {
          localStorage.removeItem(storageKey)
        }
      }
    }
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

      const nextResumes = addResumes(uploadedResumes, resumeUserId)
      setResumes(nextResumes)

      // 기존 선택 이력서가 없다면 새로 등록된 첫 이력서를 선택합니다.
      if (!selectedResumeId && nextResumes.length > 0) {
        const nextSelectedId = nextResumes[0].docId || nextResumes[0].id
        setSelectedResumeId(nextSelectedId)

        if (typeof window !== 'undefined') {
          localStorage.setItem(
            `jobpick-selected-resume-${resumeUserId}`,
            nextSelectedId
          )
        }
      }
    } catch (error) {
      console.error(error)
      alert(error.message || '이력서 업로드 실패')
    } finally {
      e.target.value = ''
    }
  }

  const handleSelectResume = (resume) => {
    const resumeId = resume.docId || resume.id
    if (!resumeId) return

    setSelectedResumeId(resumeId)

    if (typeof window !== 'undefined') {
      localStorage.setItem(
        `jobpick-selected-resume-${resumeUserId}`,
        resumeId
      )
    }
  }

  const handleDeleteResume = (resumeId) => {
    const nextResumes = removeResume(resumeId, resumeUserId)
    setResumes(nextResumes)

    if (selectedResumeId === resumeId) {
      const nextSelectedId =
        nextResumes[0]?.docId || nextResumes[0]?.id || ''

      setSelectedResumeId(nextSelectedId)

      if (typeof window !== 'undefined') {
        const storageKey = `jobpick-selected-resume-${resumeUserId}`

        if (nextSelectedId) {
          localStorage.setItem(storageKey, nextSelectedId)
        } else {
          localStorage.removeItem(storageKey)
        }
      }
    }
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
    setEditForm(null)

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

      const editableResumeData = editableAnalysis?.resumeData || editableAnalysis || {}
      setEditForm(createResumeEditForm(editableResumeData))
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
    setEditForm(null)
  }

  const handleSaveAnalysis = async () => {
    const docId = selectedResume?.docId || selectedResume?.id

    if (!docId) {
      alert('이력서 문서 ID가 없습니다.')
      return
    }

    if (!editForm) {
      alert('수정할 분석 내용이 없습니다.')
      return
    }

    const analysisRoot = getAnalysisRoot(analysisData) || {}
    const editedAnalysis = buildEditedAnalysis(analysisRoot, editForm)

    try {
      setAnalysisSaving(true)

      const res = await fetch(`/api/resume/${docId}/analysis`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          editedAnalysis,
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

      const savedAnalysis =
        data.effectiveAnalysis || data.editedAnalysis || editedAnalysis
      const savedResumeData = savedAnalysis?.resumeData || savedAnalysis || {}

      setEditForm(createResumeEditForm(savedResumeData))
      setEditMode(false)
      alert('이력서 분석 내용이 저장되었습니다.')
    } catch (error) {
      console.error(error)
      alert(error.message || '이력서 분석 내용을 저장하지 못했습니다.')
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
          {resumes.map((resume) => {
            const resumeId = resume.docId || resume.id
            const isSelected = selectedResumeId === resumeId
            const hasSelectedResume = Boolean(selectedResumeId)

            return (
              <div
                key={resume.id}
                onClick={() => handleSelectResume(resume)}
                role="button"
                tabIndex={0}
                aria-pressed={isSelected}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    handleSelectResume(resume)
                  }
                }}
                className={`relative flex cursor-pointer items-center justify-between gap-3 rounded-xl border p-4 transition-all duration-200 ${
                  isSelected
                    ? 'border-blue-500 bg-blue-50/70 shadow-md ring-2 ring-blue-100'
                    : hasSelectedResume
                      ? 'border-gray-200 bg-white opacity-55 hover:border-blue-200 hover:opacity-100 hover:shadow-sm'
                      : 'border-gray-200 bg-white hover:border-blue-200 hover:shadow-sm'
                }`}
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p
                      className={`font-semibold ${
                        isSelected ? 'text-blue-900' : 'text-gray-900'
                      }`}
                    >
                      {resume.name}
                    </p>

                    {isSelected && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-blue-600 px-2.5 py-1 text-xs font-semibold text-white shadow-sm">
                        <span aria-hidden="true">✓</span>
                        현재 선택됨
                      </span>
                    )}
                  </div>

                  <p
                    className={`mt-1 text-sm ${
                      isSelected ? 'text-blue-700' : 'text-gray-500'
                    }`}
                  >
                    {resume.size} · {resume.date}
                    {resume.status && ` · ${resume.status}`}
                  </p>

                  {isSelected && (
                    <p className="mt-2 text-xs font-medium text-blue-600">
                      현재 매칭에 사용할 이력서로 선택되어 있습니다.
                    </p>
                  )}
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  {!isSelected && (
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation()
                        handleSelectResume(resume)
                      }}
                      className="rounded-md border border-gray-200 bg-white px-3 py-1 text-sm font-medium text-gray-600 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
                    >
                      이 이력서 선택
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      handleOpenAnalysis(resume)
                    }}
                    className="rounded-md bg-blue-50 px-3 py-1 text-sm text-blue-600 transition-colors hover:bg-blue-100"
                  >
                    분석 내용 보기
                  </button>

                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      handleDeleteResume(resumeId)
                    }}
                    className="rounded-md bg-red-50 px-3 py-1 text-sm text-red-600 transition-colors hover:bg-red-100"
                  >
                    삭제
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {analysisOpen && (
        <ResumeAnalysisModal
          selectedResume={selectedResume}
          analysisData={analysisData}
          analysisLoading={analysisLoading}
          analysisSaving={analysisSaving}
          editMode={editMode}
          editForm={editForm}
          setEditMode={setEditMode}
          setEditForm={setEditForm}
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
  editForm,
  setEditMode,
  setEditForm,
  onClose,
  onSave,
}) {
  const analysisRoot = getAnalysisRoot(analysisData)

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
      <div className="w-full max-w-4xl max-h-[90vh] overflow-y-auto bg-white rounded-2xl shadow-xl p-6">
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
              <ResumeAnalysisEditForm
                value={editForm}
                onChange={setEditForm}
              />
            ) : (
              <div className="space-y-4">
                <BasicInfoSection value={analysis.basicInfo} />
                <AnalysisSection title="희망/분석 직무" value={analysis.jobCategory} />
                <AnalysisSection title="기술 스택" value={skillList} />
                <AnalysisSection title="핵심 역량" value={coreCompetencies} />
                <AnalysisSection title="학력" value={educationList} />
                <AnalysisSection title="경력" value={experienceList} />
                <ExperienceSummarySection value={analysis.experienceSummary} />
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
                      setEditForm(createResumeEditForm(analysis || {}))
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
                  onClick={() => {
                    setEditForm(createResumeEditForm(analysis || {}))
                    setEditMode(true)
                  }}
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


function ResumeAnalysisEditForm({ value, onChange }) {
  if (!value) {
    return (
      <div className="py-10 text-center text-sm text-gray-500">
        수정할 분석 내용이 없습니다.
      </div>
    )
  }

  const updateRootField = (field, nextValue) => {
    onChange((prev) => ({
      ...prev,
      [field]: nextValue,
    }))
  }

  const updateBasicInfo = (field, nextValue) => {
    onChange((prev) => ({
      ...prev,
      basicInfo: {
        ...(prev?.basicInfo || {}),
        [field]: nextValue,
      },
    }))
  }

  const updateSkillList = (field, nextValue) => {
    onChange((prev) => ({
      ...prev,
      skills: {
        ...(prev?.skills || {}),
        [field]: nextValue,
      },
    }))
  }

  const updateArrayItem = (section, index, field, nextValue) => {
    onChange((prev) => ({
      ...prev,
      [section]: (prev?.[section] || []).map((item, itemIndex) => {
        if (itemIndex !== index) return item

        const updatedItem = {
          ...item,
          [field]: nextValue,
        }

        if (section === 'experience' && field === 'organization') {
          if (Object.prototype.hasOwnProperty.call(item, 'company')) {
            updatedItem.company = nextValue
          }
          if (Object.prototype.hasOwnProperty.call(item, 'companyName')) {
            updatedItem.companyName = nextValue
          }
        }

        if (section === 'experience' && field === 'position') {
          if (Object.prototype.hasOwnProperty.call(item, 'jobTitle')) {
            updatedItem.jobTitle = nextValue
          }
        }

        if (section === 'experience' && field === 'description') {
          if (Object.prototype.hasOwnProperty.call(item, 'responsibilities')) {
            updatedItem.responsibilities = nextValue
          }
          if (Object.prototype.hasOwnProperty.call(item, 'tasks')) {
            updatedItem.tasks = nextValue
          }
        }

        if ((section === 'projects' || section === 'activities') && field === 'name') {
          if (Object.prototype.hasOwnProperty.call(item, 'title')) {
            updatedItem.title = nextValue
          }
        }

        if (section === 'activities' && field === 'role') {
          if (Object.prototype.hasOwnProperty.call(item, 'position')) {
            updatedItem.position = nextValue
          }
        }

        return updatedItem
      }),
    }))
  }

  const addArrayItem = (section, emptyItem) => {
    onChange((prev) => ({
      ...prev,
      [section]: [...(prev?.[section] || []), deepClone(emptyItem)],
    }))
  }

  const removeArrayItem = (section, index) => {
    onChange((prev) => ({
      ...prev,
      [section]: (prev?.[section] || []).filter(
        (_, itemIndex) => itemIndex !== index
      ),
    }))
  }

  const updateProjectTechnologies = (index, nextValue) => {
    updateArrayItem('projects', index, 'technologies', nextValue)
  }

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-700">
        JSON을 직접 수정하지 않고 항목별 입력창에서 내용을 변경할 수 있습니다.
        저장하면 기존 분석 데이터의 내부 정보는 유지되고, 수정한 항목만 최종 분석에 반영됩니다.
      </div>

      <EditSection title="기본 정보">
        <div className="grid gap-4 md:grid-cols-2">
          <FormField
            label="이름"
            value={value.basicInfo?.name}
            onChange={(nextValue) => updateBasicInfo('name', nextValue)}
          />
          <FormField
            label="생년월일"
            value={value.basicInfo?.birthDate}
            onChange={(nextValue) => updateBasicInfo('birthDate', nextValue)}
            placeholder="예: 2003-05-19"
          />
          <FormField
            label="나이"
            type="number"
            value={value.basicInfo?.age}
            onChange={(nextValue) => updateBasicInfo('age', nextValue)}
          />
          <FormField
            label="전화번호"
            value={value.basicInfo?.phone}
            onChange={(nextValue) => updateBasicInfo('phone', nextValue)}
          />
          <FormField
            label="이메일"
            type="email"
            value={value.basicInfo?.email}
            onChange={(nextValue) => updateBasicInfo('email', nextValue)}
          />
          <FormField
            label="주소"
            value={value.basicInfo?.address}
            onChange={(nextValue) => updateBasicInfo('address', nextValue)}
          />
        </div>
      </EditSection>

      <EditSection title="희망/분석 직무">
        <FormField
          label="직무 분야"
          value={value.jobCategory}
          onChange={(nextValue) => updateRootField('jobCategory', nextValue)}
          placeholder="예: 백엔드 개발, 디자인, 마케팅"
        />
      </EditSection>

      <EditSection
        title="기술 스택"
        description="기술을 입력하고 Enter 또는 추가 버튼을 눌러 등록하세요."
      >
        <div className="grid gap-5 md:grid-cols-2">
          <TagEditor
            label="프로그래밍 언어"
            values={value.skills?.languages || []}
            onChange={(nextValue) => updateSkillList('languages', nextValue)}
            placeholder="예: Java, Python"
          />
          <TagEditor
            label="프레임워크·라이브러리"
            values={value.skills?.frameworks || []}
            onChange={(nextValue) => updateSkillList('frameworks', nextValue)}
            placeholder="예: Spring, React"
          />
          <TagEditor
            label="도구·소프트웨어"
            values={value.skills?.tools || []}
            onChange={(nextValue) => updateSkillList('tools', nextValue)}
            placeholder="예: Figma, Git"
          />
          <TagEditor
            label="기타 기술"
            values={value.skills?.etc || []}
            onChange={(nextValue) => updateSkillList('etc', nextValue)}
            placeholder="그 밖의 기술"
          />
        </div>
      </EditSection>

      <EditSection title="핵심 역량">
        <TagEditor
          label="핵심 역량"
          values={value.coreCompetencies || []}
          onChange={(nextValue) => updateRootField('coreCompetencies', nextValue)}
          placeholder="예: 문제 해결, 협업"
        />
      </EditSection>

      <EditSection
        title="학력"
        actionLabel="학력 추가"
        onAction={() =>
          addArrayItem('education', {
            school: '',
            major: '',
            minor: '',
            degree: '',
            status: '',
            startDate: '',
            endDate: '',
            gpa: '',
          })
        }
      >
        <EditableItemList
          items={value.education || []}
          emptyText="등록된 학력 정보가 없습니다."
          renderItem={(item, index) => (
            <EditableItemCard
              key={index}
              title={`학력 ${index + 1}`}
              onRemove={() => removeArrayItem('education', index)}
            >
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  label="학교명"
                  value={item.school}
                  onChange={(nextValue) =>
                    updateArrayItem('education', index, 'school', nextValue)
                  }
                />
                <FormField
                  label="전공"
                  value={item.major}
                  onChange={(nextValue) =>
                    updateArrayItem('education', index, 'major', nextValue)
                  }
                />
                <FormField
                  label="부전공·복수전공"
                  value={item.minor}
                  onChange={(nextValue) =>
                    updateArrayItem('education', index, 'minor', nextValue)
                  }
                />
                <FormField
                  label="학위·학력"
                  value={item.degree}
                  onChange={(nextValue) =>
                    updateArrayItem('education', index, 'degree', nextValue)
                  }
                  placeholder="예: 학사, 고졸"
                />
                <FormField
                  label="상태"
                  value={item.status}
                  onChange={(nextValue) =>
                    updateArrayItem('education', index, 'status', nextValue)
                  }
                  placeholder="예: 재학, 졸업"
                />
                <FormField
                  label="학점"
                  value={item.gpa}
                  onChange={(nextValue) =>
                    updateArrayItem('education', index, 'gpa', nextValue)
                  }
                />
                <FormField
                  label="입학일"
                  value={item.startDate}
                  onChange={(nextValue) =>
                    updateArrayItem('education', index, 'startDate', nextValue)
                  }
                  placeholder="예: 2022-03"
                />
                <FormField
                  label="졸업일·종료일"
                  value={item.endDate}
                  onChange={(nextValue) =>
                    updateArrayItem('education', index, 'endDate', nextValue)
                  }
                  placeholder="예: 재학중 또는 2026-02"
                />
              </div>
            </EditableItemCard>
          )}
        />
      </EditSection>

      <EditSection
        title="경력"
        actionLabel="경력 추가"
        onAction={() =>
          addArrayItem('experience', {
            organization: '',
            department: '',
            position: '',
            role: '',
            startDate: '',
            endDate: '',
            description: '',
          })
        }
      >
        <EditableItemList
          items={value.experience || []}
          emptyText="등록된 경력 정보가 없습니다."
          renderItem={(item, index) => (
            <EditableItemCard
              key={index}
              title={`경력 ${index + 1}`}
              onRemove={() => removeArrayItem('experience', index)}
            >
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  label="회사·기관명"
                  value={item.organization || item.company || item.companyName}
                  onChange={(nextValue) =>
                    updateArrayItem('experience', index, 'organization', nextValue)
                  }
                />
                <FormField
                  label="부서"
                  value={item.department}
                  onChange={(nextValue) =>
                    updateArrayItem('experience', index, 'department', nextValue)
                  }
                />
                <FormField
                  label="직위"
                  value={item.position || item.jobTitle}
                  onChange={(nextValue) =>
                    updateArrayItem('experience', index, 'position', nextValue)
                  }
                />
                <FormField
                  label="역할"
                  value={item.role}
                  onChange={(nextValue) =>
                    updateArrayItem('experience', index, 'role', nextValue)
                  }
                />
                <FormField
                  label="근무 시작일"
                  value={item.startDate}
                  onChange={(nextValue) =>
                    updateArrayItem('experience', index, 'startDate', nextValue)
                  }
                />
                <FormField
                  label="근무 종료일"
                  value={item.endDate}
                  onChange={(nextValue) =>
                    updateArrayItem('experience', index, 'endDate', nextValue)
                  }
                  placeholder="예: 재직중"
                />
              </div>
              <div className="mt-4">
                <TextareaField
                  label="담당 업무·경력 내용"
                  value={
                    item.description ||
                    item.responsibilities ||
                    item.tasks ||
                    ''
                  }
                  onChange={(nextValue) =>
                    updateArrayItem('experience', index, 'description', nextValue)
                  }
                  rows={4}
                />
              </div>
            </EditableItemCard>
          )}
        />
      </EditSection>

      <EditSection
        title="자격증"
        actionLabel="자격증 추가"
        onAction={() =>
          addArrayItem('certifications', {
            name: '',
            grade: '',
            date: '',
          })
        }
      >
        <EditableItemList
          items={value.certifications || []}
          emptyText="등록된 자격증 정보가 없습니다."
          renderItem={(item, index) => (
            <EditableItemCard
              key={index}
              title={`자격증 ${index + 1}`}
              onRemove={() => removeArrayItem('certifications', index)}
            >
              <div className="grid gap-4 md:grid-cols-3">
                <FormField
                  label="자격증명"
                  value={item.name}
                  onChange={(nextValue) =>
                    updateArrayItem('certifications', index, 'name', nextValue)
                  }
                />
                <FormField
                  label="등급·점수"
                  value={item.grade}
                  onChange={(nextValue) =>
                    updateArrayItem('certifications', index, 'grade', nextValue)
                  }
                />
                <FormField
                  label="취득일"
                  value={item.date}
                  onChange={(nextValue) =>
                    updateArrayItem('certifications', index, 'date', nextValue)
                  }
                  placeholder="예: 2022-05"
                />
              </div>
            </EditableItemCard>
          )}
        />
      </EditSection>

      <EditSection
        title="어학"
        actionLabel="어학성적 추가"
        onAction={() =>
          addArrayItem('languageTests', {
            language: '',
            testName: '',
            score: '',
            date: '',
          })
        }
      >
        <EditableItemList
          items={value.languageTests || []}
          emptyText="등록된 어학 정보가 없습니다."
          renderItem={(item, index) => (
            <EditableItemCard
              key={index}
              title={`어학 ${index + 1}`}
              onRemove={() => removeArrayItem('languageTests', index)}
            >
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  label="언어"
                  value={item.language}
                  onChange={(nextValue) =>
                    updateArrayItem('languageTests', index, 'language', nextValue)
                  }
                  placeholder="예: 영어"
                />
                <FormField
                  label="시험명"
                  value={item.testName}
                  onChange={(nextValue) =>
                    updateArrayItem('languageTests', index, 'testName', nextValue)
                  }
                  placeholder="예: TOEIC"
                />
                <FormField
                  label="점수·등급"
                  value={item.score}
                  onChange={(nextValue) =>
                    updateArrayItem('languageTests', index, 'score', nextValue)
                  }
                />
                <FormField
                  label="응시일"
                  value={item.date}
                  onChange={(nextValue) =>
                    updateArrayItem('languageTests', index, 'date', nextValue)
                  }
                  placeholder="예: 2023-10"
                />
              </div>
            </EditableItemCard>
          )}
        />
      </EditSection>

      <EditSection
        title="프로젝트"
        actionLabel="프로젝트 추가"
        onAction={() =>
          addArrayItem('projects', {
            name: '',
            role: '',
            startDate: '',
            endDate: '',
            description: '',
            technologies: [],
          })
        }
      >
        <EditableItemList
          items={value.projects || []}
          emptyText="등록된 프로젝트 정보가 없습니다."
          renderItem={(item, index) => (
            <EditableItemCard
              key={index}
              title={`프로젝트 ${index + 1}`}
              onRemove={() => removeArrayItem('projects', index)}
            >
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  label="프로젝트명"
                  value={item.name || item.title}
                  onChange={(nextValue) =>
                    updateArrayItem('projects', index, 'name', nextValue)
                  }
                />
                <FormField
                  label="담당 역할"
                  value={item.role}
                  onChange={(nextValue) =>
                    updateArrayItem('projects', index, 'role', nextValue)
                  }
                />
                <FormField
                  label="시작일"
                  value={item.startDate}
                  onChange={(nextValue) =>
                    updateArrayItem('projects', index, 'startDate', nextValue)
                  }
                />
                <FormField
                  label="종료일"
                  value={item.endDate}
                  onChange={(nextValue) =>
                    updateArrayItem('projects', index, 'endDate', nextValue)
                  }
                />
              </div>
              <div className="mt-4">
                <TagEditor
                  label="사용 기술"
                  values={item.technologies || []}
                  onChange={(nextValue) =>
                    updateProjectTechnologies(index, nextValue)
                  }
                  placeholder="예: React, Firebase"
                />
              </div>
              <div className="mt-4">
                <TextareaField
                  label="프로젝트 설명"
                  value={item.description}
                  onChange={(nextValue) =>
                    updateArrayItem('projects', index, 'description', nextValue)
                  }
                  rows={4}
                />
              </div>
            </EditableItemCard>
          )}
        />
      </EditSection>

      <EditSection
        title="활동"
        actionLabel="활동 추가"
        onAction={() =>
          addArrayItem('activities', {
            name: '',
            organization: '',
            role: '',
            startDate: '',
            endDate: '',
            description: '',
          })
        }
      >
        <EditableItemList
          items={value.activities || []}
          emptyText="등록된 활동 정보가 없습니다."
          renderItem={(item, index) => (
            <EditableItemCard
              key={index}
              title={`활동 ${index + 1}`}
              onRemove={() => removeArrayItem('activities', index)}
            >
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  label="활동명"
                  value={item.name || item.title}
                  onChange={(nextValue) =>
                    updateArrayItem('activities', index, 'name', nextValue)
                  }
                />
                <FormField
                  label="기관·단체명"
                  value={item.organization}
                  onChange={(nextValue) =>
                    updateArrayItem('activities', index, 'organization', nextValue)
                  }
                />
                <FormField
                  label="역할"
                  value={item.role || item.position}
                  onChange={(nextValue) =>
                    updateArrayItem('activities', index, 'role', nextValue)
                  }
                />
                <FormField
                  label="시작일"
                  value={item.startDate}
                  onChange={(nextValue) =>
                    updateArrayItem('activities', index, 'startDate', nextValue)
                  }
                />
                <FormField
                  label="종료일"
                  value={item.endDate}
                  onChange={(nextValue) =>
                    updateArrayItem('activities', index, 'endDate', nextValue)
                  }
                />
              </div>
              <div className="mt-4">
                <TextareaField
                  label="활동 내용"
                  value={item.description}
                  onChange={(nextValue) =>
                    updateArrayItem('activities', index, 'description', nextValue)
                  }
                  rows={4}
                />
              </div>
            </EditableItemCard>
          )}
        />
      </EditSection>

      <EditSection title="자기소개">
        <TextareaField
          label="자기소개 내용"
          value={value.selfIntroduction}
          onChange={(nextValue) =>
            updateRootField('selfIntroduction', nextValue)
          }
          rows={10}
          placeholder="자기소개 내용을 입력하세요."
        />
      </EditSection>
    </div>
  )
}

function EditSection({
  title,
  description,
  actionLabel,
  onAction,
  children,
}) {
  return (
    <section className="rounded-xl border border-gray-200 p-4 md:p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-gray-900">{title}</h3>
          {description && (
            <p className="mt-1 text-xs text-gray-500">{description}</p>
          )}
        </div>

        {actionLabel && onAction && (
          <button
            type="button"
            onClick={onAction}
            className="rounded-lg bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100"
          >
            + {actionLabel}
          </button>
        )}
      </div>

      {children}
    </section>
  )
}

function FormField({
  label,
  value,
  onChange,
  type = 'text',
  placeholder = '',
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-gray-700">
        {label}
      </span>
      <input
        type={type}
        value={value ?? ''}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
      />
    </label>
  )
}

function TextareaField({
  label,
  value,
  onChange,
  rows = 5,
  placeholder = '',
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-gray-700">
        {label}
      </span>
      <textarea
        value={value ?? ''}
        onChange={(event) => onChange(event.target.value)}
        rows={rows}
        placeholder={placeholder}
        className="w-full resize-y rounded-lg border border-gray-300 px-3 py-2.5 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
      />
    </label>
  )
}

function TagEditor({ label, values, onChange, placeholder }) {
  const [draft, setDraft] = useState('')
  const normalizedValues = toStringArray(values)

  const addTag = () => {
    const nextTags = draft
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)

    if (!nextTags.length) return

    onChange([...new Set([...normalizedValues, ...nextTags])])
    setDraft('')
  }

  const removeTag = (tagIndex) => {
    onChange(normalizedValues.filter((_, index) => index !== tagIndex))
  }

  return (
    <div>
      <p className="mb-1.5 text-sm font-medium text-gray-700">{label}</p>

      <div className="mb-2 flex min-h-[34px] flex-wrap gap-2">
        {normalizedValues.length > 0 ? (
          normalizedValues.map((tag, index) => (
            <span
              key={`${tag}-${index}`}
              className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-700"
            >
              {tag}
              <button
                type="button"
                onClick={() => removeTag(index)}
                className="ml-1 text-blue-400 hover:text-red-500"
                aria-label={`${tag} 삭제`}
              >
                ×
              </button>
            </span>
          ))
        ) : (
          <span className="text-sm text-gray-400">등록된 내용 없음</span>
        )}
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault()
              addTag()
            }
          }}
          placeholder={placeholder}
          className="min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        />
        <button
          type="button"
          onClick={addTag}
          className="rounded-lg border border-blue-200 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
        >
          추가
        </button>
      </div>
    </div>
  )
}

function EditableItemList({ items, emptyText, renderItem }) {
  if (!items.length) {
    return (
      <div className="rounded-lg bg-gray-50 px-4 py-5 text-center text-sm text-gray-400">
        {emptyText}
      </div>
    )
  }

  return <div className="space-y-4">{items.map(renderItem)}</div>
}

function EditableItemCard({ title, onRemove, children }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50/50 p-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h4 className="text-sm font-semibold text-gray-800">{title}</h4>
        <button
          type="button"
          onClick={onRemove}
          className="rounded-md bg-red-50 px-2.5 py-1 text-xs font-medium text-red-600 hover:bg-red-100"
        >
          삭제
        </button>
      </div>
      {children}
    </div>
  )
}

function BasicInfoSection({ value }) {
  const basicInfo = value && typeof value === 'object' ? value : {}
  const items = [
    ['이름', basicInfo.name],
    ['주소', basicInfo.address],
    ['생년월일', basicInfo.birthDate],
    ['나이', basicInfo.age !== undefined && basicInfo.age !== '' ? `${basicInfo.age}세` : ''],
    ['이메일', basicInfo.email],
    ['전화번호', basicInfo.phone],
  ]

  return (
    <div className="rounded-xl border border-gray-200 p-4">
      <h3 className="mb-3 font-semibold">기본 정보</h3>
      <dl className="grid gap-x-6 gap-y-3 text-sm md:grid-cols-2">
        {items.map(([label, itemValue]) => (
          <div key={label} className="grid grid-cols-[88px_1fr] gap-2">
            <dt className="text-gray-500">{label}</dt>
            <dd className="break-words text-gray-800">
              {itemValue || '분석된 내용 없음'}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

function ExperienceSummarySection({ value }) {
  const displayValue =
    value && typeof value === 'object'
      ? value.display ||
        (value.totalMonths !== undefined ? `${value.totalMonths}개월` : '')
      : value

  return <AnalysisSection title="총 경력" value={displayValue} />
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
  if (value.title) parts.push(value.title)
  if (value.language) parts.push(value.language)
  if (value.testName) parts.push(value.testName)
  if (value.score) parts.push(value.score)
  if (value.date) parts.push(value.date)
  if (value.grade) parts.push(value.grade)
  if (value.role) parts.push(value.role)
  if (value.description && parts.length === 0) parts.push(value.description)

  if (parts.length > 0) {
    return parts.join(' / ')
  }

  return JSON.stringify(value)
}
