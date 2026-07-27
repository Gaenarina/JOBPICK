'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import {
  addResumes,
  getBookmarks,
  getResumes,
  pushRecentJob,
  removeResume,
  toggleBookmark,
} from '@/lib/userStorage'
import { FileText, Sparkles, X } from 'lucide-react'

import {
  ROLE_OPTIONS,
  LOCATION_OPTIONS,
  EMPLOYMENT_TYPE_OPTIONS,
} from '@/lib/matchingPreferenceOptions'

const MATCHED_JOBS_STORAGE_PREFIX = 'jobpick_matched_jobs'

function getJobKey(job) {
  return String(job?.id || job?.jobId || '')
}

function getResumeDocId(resume) {
  return resume?.docId || resume?.resumeId || resume?.id
}

function getMatchedJobsStorageKey(userId, resumeId) {
  return `${MATCHED_JOBS_STORAGE_PREFIX}_${userId || 'anonymous'}_${resumeId || 'unknown'}`
}

function toDisplayText(value, fallback = '') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }

  if (typeof value === 'string' || typeof value === 'number') {
    return String(value).trim()
  }

  if (Array.isArray(value)) {
    const text = value
      .map((item) => toDisplayText(item, ''))
      .filter(Boolean)
      .join(', ')

    return text || fallback
  }

  if (typeof value === 'object') {
    return (
      value.name ||
      value.title ||
      value.value ||
      value.type ||
      value.label ||
      value.text ||
      value.description ||
      fallback
    )
  }

  return fallback
}

function normalizeMatchRate(job) {
  const rawScore =
    job.matchRate ??
    job.finalScore ??
    job.final_score ??
    job.score ??
    job.matchScore ??
    job.match_score ??
    job.similarity ??
    0

  const numberScore = Number(rawScore)

  if (!Number.isFinite(numberScore)) {
    return 0
  }

  if (numberScore > 0 && numberScore <= 1) {
    return Math.round(numberScore * 100)
  }

  return Math.round(numberScore)
}

function normalizeJobs(jobs) {
  return (jobs || []).map((job) => {
    const source = job.jobPosting
      ? {
          ...job.jobPosting,
          ...job,
        }
      : job

    const jobId = source.id || source.jobId || job.id || job.jobId

    return {
      ...source,
      id: String(jobId || ''),
      jobId: String(jobId || ''),
      sourceUrl:
        source.sourceUrl ||
        source.url ||
        source.jobPosting?.sourceUrl ||
        source.meta?.sourceUrl ||
        '',
      title: toDisplayText(source.title, '제목 없음'),
      company: toDisplayText(source.company || source.companyName, '회사명 없음'),
      location: toDisplayText(source.location, ''),
      career: toDisplayText(source.career || source.experience, ''),
      category: toDisplayText(source.category || source.jobCategory, ''),
      salary: toDisplayText(source.salary, ''),
      matchRate: normalizeMatchRate(source),
    }
  })
}

function getJobRecommendRank(job) {
  const badges = getMatchBadges(job)
  const recommendType = String(job?.recommendType || job?.recommend_type || '')
  const text = `${recommendType} ${badges.join(' ')}`
  const unmetConditions = job?.unmetConditions || job?.unmet_conditions || []

  if (unmetConditions.length > 0 || text.includes('부적합') || text.includes('미충족')) {
    return 0
  }

  if (text.includes('정보') && text.includes('부족')) {
    return 1
  }

  if (text.includes('지원') && text.includes('가능')) {
    return 2
  }

  if (text.includes('보통')) {
    return 3
  }

  if (text.includes('AI') && text.includes('적합')) {
    return 5
  }

  return 1
}

function getTopMatches(jobs, count = 5) {
  return [...(jobs || [])]
    .sort((a, b) => {
      const rankDiff = getJobRecommendRank(b) - getJobRecommendRank(a)
      if (rankDiff !== 0) return rankDiff

      return Number(b.matchRate || 0) - Number(a.matchRate || 0)
    })
    .slice(0, count)
}

function extractMatchedJobsFromResponse(data) {
  const root = data?.result || data || {}
  const groups = root?.groups || root?.matchingResults || root || {}

  return (
    groups.topFitMatches ||
    groups.top_fit_matches ||
    groups.matches ||
    root.topFitMatches ||
    root.top_fit_matches ||
    root.matches ||
    data?.topFitMatches ||
    data?.matches ||
    []
  )
}

function formatScore(value, digits = 2) {
  const numberValue = Number(value ?? 0)

  if (!Number.isFinite(numberValue)) {
    return Number(0).toFixed(digits)
  }

  return numberValue.toFixed(digits)
}

function getMatchBadges(job) {
  const badges = job?.matchBadges || job?.match_badges || []

  if (Array.isArray(badges) && badges.length > 0) {
    return badges.map((badge) => String(badge))
  }

  if (typeof badges === 'string' && badges.trim()) {
    return [badges.trim()]
  }

  const recommendType = job?.recommendType || job?.recommend_type
  return recommendType ? [String(recommendType)] : []
}

function getBadgeClassName(badge) {
  const text = String(badge || '')
  const isPositive =
    text.includes('AI') ||
    (text.includes('적합') && !text.includes('부적합')) ||
    (text.includes('?곹빀') && !text.includes('遺?곹빀'))
  const isNegative = text.includes('부적합') || text.includes('미충족') || text.includes('遺?곹빀')
  const isAccessible = text.includes('지원') || text.includes('가능') || text.includes('吏??') || text.includes('媛??')
  const isInfoPoor = text.includes('정보') || text.includes('부족') || text.includes('?뺣낫') || text.includes('遺議?')

  if (isPositive && !isNegative) {
    return 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
  }

  if (isAccessible) {
    return 'bg-sky-50 text-sky-700 border-sky-200 hover:bg-sky-100'
  }

  if (isNegative) {
    return 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100'
  }

  if (isInfoPoor) {
    return 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100'
  }

  return 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
}

function getPrimaryBadge(job) {
  return getMatchBadges(job)[0] || job?.recommendType || '보통'
}

function isNcsUsed(job, ncs) {
  return Boolean(ncs?.used ?? ncs?.ncs_used ?? job?.ncsTotal > 0)
}

function getReadableScoringMode(job, ncs) {
  if (
    job?.scoringMode === 'RULE_25_SEMANTIC_50_NCS_25' ||
    job?.scoringMode === 'RULE_15_SEMANTIC_70_NCS_15' ||
    job?.scoringMode === 'SEMANTIC_70_NCS_30' ||
    isNcsUsed(job, ncs)
  ) {
    return 'NCS 보완 평가'
  }

  if (
    job?.scoringMode === 'RULE_50_SEMANTIC_50' ||
    job?.scoringMode === 'RULE_30_SEMANTIC_70'
  ) {
    return '명시 조건 중심 평가'
  }

  return '기본 매칭 평가'
}

function getSummaryMessage(job, ncs) {
  const badge = getPrimaryBadge(job)
  const text = `${badge} ${job?.recommendType || ''}`

  if (text.includes('부적합') || text.includes('遺?곹빀')) {
    return '이 공고는 일부 필수 조건이 이력서와 맞지 않아 추천 우선순위가 낮습니다.'
  }

  if (text.includes('정보') || text.includes('부족') || text.includes('?뺣낫') || text.includes('遺議?')) {
    return '공고에 세부 조건이 부족하여 제한된 정보로 보완 평가했습니다.'
  }

  if (isNcsUsed(job, ncs)) {
    return '공고에 세부 조건이 부족하여 NCS 직무 기준으로 보완 평가했습니다.'
  }

  if (text.includes('AI') || text.includes('적합') || text.includes('?곹빀')) {
    return '이력서와 공고의 조건 및 직무 내용이 전반적으로 잘 맞습니다.'
  }

  if (text.includes('지원') || text.includes('가능') || text.includes('吏??') || text.includes('媛??')) {
    return '기본 자격 조건 통과 가능성이 비교적 높지만 세부 조건은 추가 확인이 필요합니다.'
  }

  return '이력서와 공고 정보를 종합해 기본 적합도를 계산했습니다.'
}

function formatRoundedScore(value) {
  const numberValue = Number(value ?? 0)
  return Number.isFinite(numberValue) ? `${Math.round(numberValue)}점` : '0점'
}

function formatPercent(value) {
  const numberValue = Number(value ?? 0)
  if (!Number.isFinite(numberValue)) return '0%'
  return `${Math.round(numberValue * 100)}%`
}

function describeConditionMatch(matched, total) {
  const matchedCount = Number(matched ?? 0)
  const totalCount = Number(total ?? 0)

  if (!totalCount) return '요구 조건 없음'
  return `필수조건 ${totalCount}개 중 ${matchedCount}개 충족`
}

function formatRuleDetail(score, maxScore, matched, total) {
  const totalCount = Number(total ?? 0)

  if (!totalCount) {
    return '요구 조건 없음, 평가 제외'
  }

  return `${formatScore(score)}/${formatScore(maxScore, 1)} (${describeConditionMatch(matched, total)})`
}

function getSemanticLevel(similarity) {
  const value = Number(similarity ?? 0)

  if (value >= 0.7) return '높은 수준'
  if (value >= 0.4) return '보통 수준'
  if (value > 0) return '낮은 수준'
  return '확인하기 어려운 수준'
}

function buildReasonList(job, matchDetail, semantic, ncs) {
  const reasons = []
  const skills = matchDetail.skills || {}
  const qualifications = matchDetail.qualifications || {}
  const skillTotal = Number(skills.totalCount ?? 0)
  const skillMatches = Number(skills.matchCount ?? 0)
  const qualTotal = Number(qualifications.totalCount ?? 0)
  const qualMatches =
    Number(qualifications.matchedQuals?.length ?? qualifications.matchCount ?? 0)

  if (skillTotal > 0 && skillMatches === 0) {
    reasons.push('필수 기술 조건과 일치하는 기술 스택이 확인되지 않았습니다.')
  } else if (skillTotal > 0) {
    reasons.push(`필수 기술 조건 ${skillTotal}개 중 ${skillMatches}개가 일치했습니다.`)
  }

  if (qualTotal > 0) {
    reasons.push(`필수 자격요건 ${qualTotal}개 중 ${qualMatches}개가 일치했습니다.`)
  }

  if ((job.ruleEvidenceCount ?? 0) < 2) {
    reasons.push('공고에 명확한 필수 조건이 부족합니다.')
  }

  if (isNcsUsed(job, ncs)) {
    const unit = ncs.matchedUnitName || ncs.matched_unit_name || ''
    reasons.push(
      unit
        ? `이력서 내용은 ${unit} 능력단위와 일부 유사합니다.`
        : '명시 조건이 부족해 NCS 직무역량 기준으로 보완 평가했습니다.'
    )
  }

  const semanticLevel = getSemanticLevel(semantic.fullSimilarity)
  reasons.push(`이력서와 공고 전체 내용의 의미 유사도는 ${semanticLevel}입니다.`)

  return reasons.slice(0, 3)
}

function ScoreDetailModal({ job, onClose }) {
  if (!job) return null

  const matchDetail = job.matchDetail || {}
  const semantic = matchDetail.semantic || {}
  const ncs = matchDetail.ncs || job.ncsDetails || {}
  const badges = getMatchBadges(job)
  const primaryBadge = getPrimaryBadge(job)
  const finalScore = job.fitScore ?? job.finalScore ?? job.matchRate ?? 0
  const ruleTotalMax = job.ruleTotalMax ?? 25
  const semanticTotalMax = job.semanticTotalMax ?? 50
  const ncsTotalMax = job.ncsTotalMax ?? ncs.maxScore ?? ncs.ncs_score_max ?? 25
  const ncsApplied = isNcsUsed(job, ncs)
  const readableMode = getReadableScoringMode(job, ncs)
  const reasons = buildReasonList(job, matchDetail, semantic, ncs)
  const unmetConditions = job.unmetConditions || []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl bg-white p-5 md:p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4 mb-5">
          <div className="min-w-0">
            <p className="text-sm text-gray-500 truncate">{job.company}</p>
            <h3 className="text-xl font-bold text-gray-900 mt-1">AI 매칭 상세 분석</h3>
            <p className="text-sm text-gray-500 mt-1 truncate">{job.title}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-700"
            aria-label="AI 매칭 상세 분석 닫기"
          >
            <X className="w-5 h-5" aria-hidden />
          </button>
        </div>

        <section className="rounded-xl border border-blue-100 bg-blue-50/70 p-4 mb-4">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <span className={`px-3 py-1 rounded border text-sm font-semibold ${getBadgeClassName(primaryBadge)}`}>
              {primaryBadge}
            </span>
            <span className="text-sm text-gray-500">판단 방식: {readableMode}</span>
          </div>
          <p className="text-sm md:text-base text-gray-700 mb-4">
            {getSummaryMessage(job, ncs)}
          </p>
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-lg bg-white/80 p-3">
              <p className="text-xs text-gray-500">적합도</p>
              <p className="text-lg font-bold text-gray-900">{formatRoundedScore(finalScore)}</p>
            </div>
            <div className="rounded-lg bg-white/80 p-3">
              <p className="text-xs text-gray-500">자격 통과 가능성</p>
              <p className="text-lg font-bold text-gray-900">{formatRoundedScore(job.accessibilityScore)}</p>
            </div>
            <div className="rounded-lg bg-white/80 p-3">
              <p className="text-xs text-gray-500">판단 근거 충분도</p>
              <p className="text-lg font-bold text-gray-900">{formatRoundedScore(job.confidenceScore)}</p>
            </div>
          </div>
        </section>

        <div className="space-y-4 text-sm text-gray-700">
          <section className="rounded-xl border border-gray-200 p-4">
            <h4 className="font-semibold text-gray-900 mb-3">점수 구성</h4>
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="font-medium text-gray-900">룰 기반 점수</p>
                {ruleTotalMax > 0 ? (
                  <p className="text-xl font-bold text-primary mt-2">
                    {formatScore(job.ruleTotal)} / {formatScore(ruleTotalMax, 0)}
                  </p>
                ) : (
                  <p className="text-xl font-bold text-gray-500 mt-2">미적용</p>
                )}
                <p className="text-xs text-gray-500 mt-2">
                  {ruleTotalMax > 0
                    ? '공고에 명시된 조건과 이력서 정보를 비교했습니다.'
                    : '공고에 명확한 조건이 없어 룰 기반 평가를 제외했습니다.'}
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="font-medium text-gray-900">의미 유사도 점수</p>
                <p className="text-xl font-bold text-primary mt-2">
                  {formatScore(job.semanticTotal)} / {formatScore(semanticTotalMax, 0)}
                </p>
                <p className="text-xs text-gray-500 mt-2">
                  이력서 내용과 공고의 업무·자격요건 간 의미적 유사도를 계산했습니다.
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="font-medium text-gray-900">NCS 직무역량 점수</p>
                {ncsApplied ? (
                  <>
                    <p className="text-xl font-bold text-primary mt-2">
                      {formatScore(job.ncsTotal ?? ncs.score)} / {formatScore(ncsTotalMax, 0)}
                    </p>
                    <p className="text-xs text-gray-500 mt-2">
                      {(ncs.matchedDutyName || ncs.matched_duty_name || 'NCS 직무')}{' '}
                      {(ncs.matchedUnitName || ncs.matched_unit_name || '능력단위')}와 가장 유사하게 판단되었습니다.
                    </p>
                  </>
                ) : (
                  <>
                    <p className="text-xl font-bold text-gray-500 mt-2">미적용</p>
                    <p className="text-xs text-gray-500 mt-2">
                      {ncs.reason || '공고에 명시된 조건이 충분하여 NCS 보완 점수를 적용하지 않았습니다.'}
                    </p>
                  </>
                )}
              </div>
            </div>
          </section>

          <section className="rounded-xl border border-gray-200 p-4">
            <h4 className="font-semibold text-gray-900 mb-2">주요 판단 근거</h4>
            <ul className="list-disc pl-5 space-y-1">
              {reasons.map((reason, index) => (
                <li key={index}>{reason}</li>
              ))}
            </ul>
          </section>

          <section
            className={`rounded-xl border p-4 ${
              unmetConditions.length
                ? 'border-red-200 bg-red-50 text-red-700'
                : 'border-emerald-100 bg-emerald-50 text-emerald-700'
            }`}
          >
            <h4 className="font-semibold mb-2">미충족 조건</h4>
            {unmetConditions.length ? (
              <ul className="list-disc pl-5 space-y-1">
                {unmetConditions.map((condition, index) => (
                  <li key={index}>{condition}</li>
                ))}
              </ul>
            ) : (
              <p>미충족 조건 없음</p>
            )}
          </section>

          <details className="rounded-xl border border-gray-200 p-4">
            <summary className="cursor-pointer font-semibold text-gray-900">
              상세 계산 보기
            </summary>
            <div className="mt-4 space-y-3 text-gray-700">
              <div>
                <h5 className="font-medium text-gray-900 mb-1">룰 기반 세부 점수</h5>
                <p>
                  - 기술 스택: {formatRuleDetail(
                    matchDetail.skills?.score,
                    matchDetail.skills?.maxScore ?? 10,
                    matchDetail.skills?.matchCount,
                    matchDetail.skills?.totalCount
                  )}
                </p>
                <p>
                  - 학력: {matchDetail.education?.used === false ? '학력 조건 없음, 평가 제외' : `${formatScore(matchDetail.education?.score)}/${formatScore(matchDetail.education?.maxScore ?? 2.5, 1)}`}
                </p>
                <p>
                  - 경력: {matchDetail.experience?.conditionUsed === false ? '경력 조건 없음, 평가 제외' : `${formatScore(matchDetail.experience?.score)}/${formatScore(matchDetail.experience?.maxScore ?? 5, 1)}`}
                </p>
                <p>
                  - 자격증: {formatRuleDetail(
                    matchDetail.certifications?.score,
                    matchDetail.certifications?.maxScore ?? 2.5,
                    matchDetail.certifications?.matchCount,
                    matchDetail.certifications?.totalCount
                  )}
                </p>
                <p>
                  - 필수 자격요건: {formatRuleDetail(
                    matchDetail.qualifications?.score,
                    matchDetail.qualifications?.maxScore ?? 5,
                    matchDetail.qualifications?.matchedQuals?.length,
                    matchDetail.qualifications?.totalCount
                  )}
                </p>
              </div>
              <div>
                <h5 className="font-medium text-gray-900 mb-1">의미 유사도 세부 값</h5>
                <p>- 전체 유사도: {formatPercent(semantic.fullSimilarity)}</p>
                <p>- 담당업무 유사도: {formatPercent(semantic.responsibilitySimilarity)}</p>
                <p>- 자격요건 유사도: {formatPercent(semantic.qualificationSimilarity)}</p>
                <p>- 필수조건 충족률: {formatPercent(semantic.requiredConditionRatio)}</p>
              </div>
              <div>
                <h5 className="font-medium text-gray-900 mb-1">NCS 세부 값</h5>
                <p>- NCS 보완 평가: {ncsApplied ? '적용' : '미적용'}</p>
                {ncsApplied && (
                  <>
                    <p>- NCS 분야: {ncs.category || ncs.ncs_category || '미적용'}</p>
                    <p>- 매칭 직무: {ncs.matchedDutyName || ncs.matched_duty_name || '없음'}</p>
                    <p>- 매칭 능력단위: {ncs.matchedUnitName || ncs.matched_unit_name || '없음'}</p>
                    <p>- NCS 유사도: {formatPercent(ncs.similarity ?? ncs.ncs_similarity)}</p>
                  </>
                )}
              </div>
            </div>
          </details>
        </div>
      </div>
    </div>
  )
}

function toggleSelectedValue(setter, value) {
  setter((prev) =>
    prev.includes(value)
      ? prev.filter((item) => item !== value)
      : [...prev, value]
  )
}

function PreferenceOptionGroup({
  title,
  options,
  selectedValues,
  onToggle,
}) {
  return (
    <div>
      <p className="mb-2 text-sm font-semibold text-gray-800">
        {title}
      </p>

      <div className="flex flex-wrap gap-2">
        {options.map((option) => {
          const isSelected = selectedValues.includes(option.value)

          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={isSelected}
              onClick={() => onToggle(option.value)}
              className={`rounded-full border px-3 py-2 text-sm font-medium transition-colors ${
                isSelected
                  ? 'border-primary bg-primary text-white'
                  : 'border-gray-200 bg-white text-gray-600 hover:border-primary hover:text-primary'
              }`}
            >
              {isSelected ? `✓ ${option.label}` : option.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function LandingPage() {
  const router = useRouter()
  const { user, isAuthenticated, mounted } = useAuth()
  const resumeUserId = user?.uid || user?.id || ''
  const [jobs, setJobs] = useState([])

  const [matchedJobs, setMatchedJobs] = useState([])
  const [matchPage, setMatchPage] = useState(1)
  const matchItemsPerPage = 10
  const [isLoadingJobs, setIsLoadingJobs] = useState(false)
  const [selectedPopularCategory, setSelectedPopularCategory] = useState('전체')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  const [resumes, setResumes] = useState([])
  const fileInputRef = useRef(null)
  const [showSavedResumes, setShowSavedResumes] = useState(true)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisDone, setAnalysisDone] = useState(false)
  const [selectedResume, setSelectedResume] = useState(null)
  const [bookmarkIds, setBookmarkIds] = useState([])
  const [scoreDetailJob, setScoreDetailJob] = useState(null)
  const [desiredRoles, setDesiredRoles] = useState([])
  const [desiredLocations, setDesiredLocations] = useState([])
  const [employmentTypes, setEmploymentTypes] = useState([])
  const [pendingFile, setPendingFile] = useState(null)
  const [showPreferenceModal, setShowPreferenceModal] = useState(false)

  // 등록된 이력서의 희망 채용 조건 수정
  const [editingResume, setEditingResume] = useState(null)
  const [editDesiredRoles, setEditDesiredRoles] = useState([])
  const [editDesiredLocations, setEditDesiredLocations] = useState([])
  const [editEmploymentTypes, setEditEmploymentTypes] = useState([])
  const [isUpdatingPreferences, setIsUpdatingPreferences] = useState(false)

  const handleGetStarted = () => {
    router.push('/login')
  }

  const handleShowSavedClick = () => {
    if (!isAuthenticated) {
      router.push('/login')
      return
    }
    setShowSavedResumes((prev) => !prev)
  }

  const handleNewUploadClick = () => {
    if (!isAuthenticated) {
      router.push('/login')
      return
    }

    setPendingFile(null)
    setDesiredRoles([])
    setDesiredLocations([])
    setEmploymentTypes([])

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
      fileInputRef.current.click()
    }
  }

  const fetchJobs = async () => {
    setIsLoadingJobs(true)
    try {
      const res = await fetch('/api/job-postings', {
        cache: 'no-store',
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || '공고 목록 불러오기 실패')
      }
      setJobs(normalizeJobs(data.jobs || []))
    } catch (error) {
      console.error(error)
    } finally {
      setIsLoadingJobs(false)
    }
  }

  const restoreMatchedJobsFromStorage = (resume) => {
    try {
      const resumeId = getResumeDocId(resume)
      const userId = user?.uid || user?.id || ''

      if (!resumeId) return false

      const storageKey = getMatchedJobsStorageKey(userId, resumeId)
      const savedMatchedJobs = localStorage.getItem(storageKey)

      if (!savedMatchedJobs) return false

      const parsed = JSON.parse(savedMatchedJobs)
      const savedJobs = Array.isArray(parsed) ? parsed : parsed.jobs || []
      const normalized = getTopMatches(normalizeJobs(savedJobs), 5)

      if (normalized.length > 0) {
        setSelectedResume(resume)
        setMatchedJobs(normalized)
        setAnalysisDone(true)
        return true
      }
      return false
    } catch (error) {
      console.error('저장된 매칭 결과 불러오기 실패:', error)
      return false
    }
  }

  const runAiMatchingByResume = async (resume, forceRefresh = false) => {
    const resumeId = getResumeDocId(resume)

    if (!resumeId) {
      alert('이력서 문서 ID를 찾을 수 없습니다.')
      return
    }

    const userId = user?.uid || user?.id || ''

    setSelectedResume(resume)
    setIsAnalyzing(true)
    setAnalysisDone(false)
    setMatchedJobs([])
    setMatchPage(1)

    try {
      if (forceRefresh) {
        const storageKey = getMatchedJobsStorageKey(userId, resumeId)
        localStorage.removeItem(storageKey)
      }

      const res = await fetch(`/api/resume/${resumeId}/process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          docId: resumeId,
          resumeId,
          userId,
          forceRefresh,
          force: forceRefresh,
        }),
      })

      const data = await res.json().catch(() => ({}))
      console.log('메인 AI 매칭 응답:', data)

      if (!res.ok) {
        throw new Error(data.error || 'AI 매칭 실패')
      }

      const rawMatches = extractMatchedJobsFromResponse(data)
      const topMatches = normalizeJobs(rawMatches)

      setMatchedJobs(topMatches)

      const storageKey = getMatchedJobsStorageKey(userId, resumeId)
      localStorage.setItem(
        storageKey,
        JSON.stringify({
          resumeId,
          jobs: topMatches,
          savedAt: new Date().toISOString(),
          forceRefresh,
          analysisSource:
            data?.result?.analysisSource ||
            data?.analysisSource ||
            '',
          resumeAnalysisVersion:
            data?.result?.resumeAnalysisVersion ||
            data?.resumeAnalysisVersion ||
            null,
          isAnalysisEdited:
            data?.result?.isAnalysisEdited ??
            data?.isAnalysisEdited ??
            false,
        })
      )

      setResumes((prev) =>
        prev.map((item) =>
          getResumeDocId(item) === resumeId
            ? { ...item, status: 'DONE' }
            : item
        )
      )

      setSelectedResume((prev) =>
        getResumeDocId(prev) === resumeId
          ? { ...prev, status: 'DONE' }
          : prev
      )

      setAnalysisDone(true)

      if (!topMatches.length) {
        alert('매칭 결과가 비어 있습니다. 백엔드 matches 반환값을 확인해주세요.')
      }
    } catch (error) {
      console.error(error)

      setResumes((prev) =>
        prev.map((item) =>
          getResumeDocId(item) === resumeId
            ? { ...item, status: 'FAILED' }
            : item
        )
      )

      alert(error.message || 'AI 매칭 중 오류가 발생했습니다.')
      setAnalysisDone(false)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const checkResumeStatus = async (resume, shouldRunMatching = false) => {
    const resumeId = getResumeDocId(resume)
    if (!resumeId) return null

    try {
      const res = await fetch(`/api/resume/${resumeId}`)
      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.error || '상태 조회 실패')
      }

      const latestStatus = data.status || 'INIT'

      setResumes((prev) =>
        prev.map((item) =>
          getResumeDocId(item) === resumeId
            ? { ...item, status: latestStatus }
            : item
        )
      )

      setSelectedResume((prev) =>
        getResumeDocId(prev) === resumeId
          ? { ...prev, status: latestStatus }
          : prev
      )

      if (latestStatus === 'PROCESSING') {
        setIsAnalyzing(true)
        setAnalysisDone(false)
      }

      if (latestStatus === 'DONE') {
        if (shouldRunMatching) {
          await runAiMatchingByResume({ ...resume, status: latestStatus }, false)
        } else {
          setIsAnalyzing(false)
          setAnalysisDone(false)
        }
      }

      if (latestStatus === 'FAILED') {
        setIsAnalyzing(false)
        setAnalysisDone(false)
      }

      return latestStatus
    } catch (error) {
      console.error(error)
      return null
    }
  }

  const startStatusPolling = (resume) => {
    let count = 0
    const maxCount = 10

    const timer = setInterval(async () => {
      count += 1
      const status = await checkResumeStatus(resume, true)
      if (status === 'DONE' || status === 'FAILED' || count >= maxCount) {
        clearInterval(timer)
      }
    }, 2000)
  }

  const handleFileSelect = (e) => {
    if (!isAuthenticated) {
      router.push('/login')
      e.target.value = ''
      return
    }

    const files = Array.from(e.target.files || [])
    if (!files.length) return

    const validTypes = ['.pdf', '.doc', '.docx']
    const validFiles = files.filter((file) => {
      const ext = '.' + file.name.split('.').pop().toLowerCase()
      return validTypes.includes(ext)
    })

    if (!validFiles.length) {
      alert('PDF, DOC, DOCX 파일만 업로드 가능합니다.')
      e.target.value = ''
      return
    }

    setPendingFile(validFiles[0])
    setShowPreferenceModal(true)
    e.target.value = ''
  }

  const handleCancelUpload = () => {
    if (isAnalyzing) return

    setShowPreferenceModal(false)
    setPendingFile(null)
    setDesiredRoles([])
    setDesiredLocations([])
    setEmploymentTypes([])
  }

  const handleConfirmUpload = async () => {
    if (!pendingFile) {
      alert('업로드할 이력서 파일을 찾을 수 없습니다.')
      return
    }

    const file = pendingFile
    const matchPreferences = {
      desiredRoles,
      desiredLocations,
      employmentTypes,
    }

    try {
      setIsAnalyzing(true)
      setAnalysisDone(false)
      setMatchedJobs([])

      const formData = new FormData()
      formData.append('file', file)
      formData.append('userId', user?.uid || user?.id || 'anonymous')
      formData.append('matchPreferences', JSON.stringify(matchPreferences))

      const res = await fetch('/api/resume/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || '업로드 실패')
      }

      const dateStr = new Date()
        .toLocaleDateString('ko-KR', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
        })
        .replace(/\. /g, '.')
        .replace(/\.$/, '')

      const docId = data.docId || data.resumeId || data.id || String(Date.now())

      const mappedResume = {
        id: docId,
        docId,
        name: file.name,
        size: Math.round(file.size / 1024) + ' KB',
        date: dateStr,
        status: data.status || 'INIT',
        matchPreferences: data.matchPreferences || matchPreferences,
      }

      setResumes(addResumes([mappedResume], resumeUserId))
      setShowSavedResumes(true)
      setSelectedResume(mappedResume)
      setShowPreferenceModal(false)
      setPendingFile(null)

      await runAiMatchingByResume(mappedResume, true)

      setDesiredRoles([])
      setDesiredLocations([])
      setEmploymentTypes([])
    } catch (error) {
      console.error(error)
      alert(error.message || '업로드 중 오류가 발생했습니다.')
      setIsAnalyzing(false)
    }
  }

  useEffect(() => {
    if (!mounted) return

    const savedResumes = getResumes(resumeUserId)
    setResumes(savedResumes)
    setBookmarkIds(getBookmarks(resumeUserId).map((item) => getJobKey(item)))
    fetchJobs()

    if (savedResumes.length > 0) {
      restoreMatchedJobsFromStorage(savedResumes[0])
    }

    const handlePageShow = () => {
      if (savedResumes.length > 0) {
        restoreMatchedJobsFromStorage(savedResumes[0])
      }
    }

    window.addEventListener('pageshow', handlePageShow)
    return () => {
      window.removeEventListener('pageshow', handlePageShow)
    }
  }, [mounted, resumeUserId])

  const name = user?.displayName || user?.name || '회원'

  const handleResumeAnalyze = (resume) => {
    const restored = restoreMatchedJobsFromStorage(resume)
    if (restored) return
    runAiMatchingByResume(resume, false)
  }

  const handleDeleteResume = (resumeId) => {
    const next = removeResume(resumeId, resumeUserId)
    setResumes(next)

    const storageKey = getMatchedJobsStorageKey(resumeUserId, resumeId)
    localStorage.removeItem(storageKey)

    if (getResumeDocId(selectedResume) === resumeId) {
      setSelectedResume(null)
      setAnalysisDone(false)
      setMatchedJobs([])
    }
  }

  const handleGoJob = (job) => {
    pushRecentJob(job)
    router.push(`/jobs/${job.id || job.jobId}`)
  }

  const handleGoPopularJob = (job) => {
    pushRecentJob(job)
    if (job.sourceUrl) {
      window.open(job.sourceUrl, '_blank', 'noopener,noreferrer')
      return
    }
    alert('원본 공고 링크를 찾을 수 없습니다.')
  }

  const handleToggleBookmark = (job) => {
    if (!isAuthenticated) {
      router.push('/login')
      return
    }
    const next = toggleBookmark(job, resumeUserId)
    setBookmarkIds(next.map((item) => getJobKey(item)))
  }

  const handleOpenPreferenceEdit = async (resume) => {
    const resumeId = getResumeDocId(resume)

    if (!resumeId) {
      alert('이력서 문서 ID를 찾을 수 없습니다.')
      return
    }

    try {
      const res = await fetch(`/api/resume/${resumeId}/preferences`, {
        cache: 'no-store',
      })

      const data = await res.json().catch(() => ({}))

      if (!res.ok) {
        throw new Error(data.error || '기존 조건을 불러오지 못했습니다.')
      }

      const matchPreferences = data.matchPreferences || {}

      setEditDesiredRoles(
        Array.isArray(matchPreferences.desiredRoles)
          ? matchPreferences.desiredRoles
          : []
      )
      setEditDesiredLocations(
        Array.isArray(matchPreferences.desiredLocations)
          ? matchPreferences.desiredLocations
          : []
      )
      setEditEmploymentTypes(
        Array.isArray(matchPreferences.employmentTypes)
          ? matchPreferences.employmentTypes
          : []
      )
      setEditingResume(resume)
    } catch (error) {
      console.error(error)
      alert(error.message || '이력서 조건을 불러오는 중 오류가 발생했습니다.')
    }
  }

  const handleClosePreferenceEdit = () => {
    if (isUpdatingPreferences) return

    setEditingResume(null)
    setEditDesiredRoles([])
    setEditDesiredLocations([])
    setEditEmploymentTypes([])
  }

  const handleSavePreferenceEdit = async () => {
    const resumeId = getResumeDocId(editingResume)

    if (!resumeId) {
      alert('이력서 문서 ID를 찾을 수 없습니다.')
      return
    }

    const matchPreferences = {
      desiredRoles: editDesiredRoles,
      desiredLocations: editDesiredLocations,
      employmentTypes: editEmploymentTypes,
    }

    try {
      setIsUpdatingPreferences(true)

      const res = await fetch(`/api/resume/${resumeId}/preferences`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          matchPreferences,
        }),
      })

      const data = await res.json().catch(() => ({}))

      if (!res.ok) {
        throw new Error(data.error || '조건 수정에 실패했습니다.')
      }

      const savedPreferences = data.matchPreferences || matchPreferences
      const updatedResume = {
        ...editingResume,
        matchPreferences: savedPreferences,
      }

      setResumes((prev) =>
        prev.map((resume) =>
          getResumeDocId(resume) === resumeId
            ? {
                ...resume,
                matchPreferences: savedPreferences,
              }
            : resume
        )
      )

      setSelectedResume((prev) =>
        getResumeDocId(prev) === resumeId
          ? {
              ...prev,
              matchPreferences: savedPreferences,
            }
          : prev
      )

      setEditingResume(null)
      setEditDesiredRoles([])
      setEditDesiredLocations([])
      setEditEmploymentTypes([])

      await runAiMatchingByResume(updatedResume, true)
    } catch (error) {
      console.error(error)
      alert(error.message || '이력서 조건 수정 중 오류가 발생했습니다.')
    } finally {
      setIsUpdatingPreferences(false)
    }
  }

  const handleRematch = (resume) => {
    if (!resume) {
      alert('먼저 이력서를 선택해주세요.')
      return
    }

    runAiMatchingByResume(resume, true)
  }

  // AI 추천 매칭 리스트 페이징 데이터
  const totalMatchPages = Math.ceil(matchedJobs.length / matchItemsPerPage)
  const matchStartIndex = (matchPage - 1) * matchItemsPerPage
  const matchEndIndex = matchStartIndex + matchItemsPerPage
  const pagedMatchedJobs = matchedJobs.slice(matchStartIndex, matchEndIndex)

  console.log('matchedJobs:', matchedJobs)
  console.log('matchedJobs length:', matchedJobs.length)
  console.log('totalMatchPages:', totalMatchPages)

  // 인기 커리어 리스트 페이징 데이터
  const filteredJobs = jobs.filter((job) => {
    if (selectedPopularCategory === '전체') return true
    return job.category === selectedPopularCategory
  })
  const totalPages = Math.ceil(filteredJobs.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const popularJobs = filteredJobs.slice(startIndex, endIndex)

  useEffect(() => {
    setCurrentPage(1)
  }, [selectedPopularCategory])

  return (
    <main className="max-w-5xl mx-auto p-4 md:p-8">
      {isAuthenticated ? (
        <section className="py-6 md:py-8">
          <h1 className="text-2xl md:text-4xl font-bold mb-1">
            안녕하세요, <span className="text-primary">{name}</span> 님!
          </h1>
          <p className="text-gray-500 text-base md:text-lg">
            AI 기반 이력서/채용공고 매칭 서비스예요.
          </p>
        </section>
      ) : (
        <section className="text-center py-10 md:py-12">
          <h1 className="text-3xl md:text-5xl font-bold text-primary mb-2">
            로그인을 해주세요!
          </h1>
          <p className="text-gray-500 mb-6 text-base md:text-lg">
            AI 기반 이력서/채용공고 매칭 서비스예요.
          </p>
          <button
            onClick={handleGetStarted}
            className="px-8 py-3 md:py-4 md:text-lg bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition-colors"
          >
            로그인하고 시작하기
          </button>
        </section>
      )}

      {/* AI 매칭 추천 블록 */}
      <section
        className={`mt-8 md:mt-10 ${
          !isAuthenticated ? 'blur-sm opacity-60 select-none pointer-events-none' : ''
        }`}
      >
        <div className="bg-blue-50 rounded-2xl p-5 md:p-8 border border-blue-200 relative">
          <h2 className="text-2xl md:text-2xl font-bold mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 md:w-6 md:h-6 text-primary" aria-hidden />
            AI 커리어 매칭 분석
          </h2>

          <p className="text-gray-500 text-base md:text-base mb-4">
            로그인 후 이력서를 업로드하면 AI가 분석하여 맞춤 채용공고를 추천해드립니다.
          </p>

          <div className="relative border-2 border-dashed border-gray-200 rounded-xl md:rounded-2xl p-5 md:p-8 bg-white">
            {!isAuthenticated && (
              <div className="absolute inset-0 z-20 flex items-center justify-center">
                <button
                  type="button"
                  onClick={() => router.push('/login')}
                  className="w-full h-full flex flex-col items-center justify-center gap-2 bg-black/30 text-white rounded-2xl"
                  aria-label="로그인 안내"
                >
                  <span className="text-lg font-medium">로그인 후 이용 가능합니다</span>
                  <span className="text-sm underline">로그인하러 가기</span>
                </button>
              </div>
            )}

            <div className="flex flex-wrap gap-3 mb-4">
              <button
                type="button"
                onClick={handleShowSavedClick}
                className={`px-5 py-2.5 rounded-xl text-sm md:text-base font-medium ${
                  showSavedResumes ? 'bg-primary text-white' : 'bg-slate-100 text-gray-700'
                }`}
              >
                등록한 이력서 불러오기
              </button>

              <button
                type="button"
                onClick={handleNewUploadClick}
                className="px-5 py-2.5 rounded-xl text-sm md:text-base font-medium bg-slate-900 text-white"
              >
                새 이력서 등록하기
              </button>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.doc,.docx"
                className="hidden"
                onChange={handleFileSelect}
              />
            </div>

            <p className="text-sm md:text-base text-gray-500 mb-3">
              PDF, DOC, DOCX 파일을 업로드하거나, 등록한 이력서를 선택해 분석해보세요.
            </p>

            {showSavedResumes && (
              <div className="flex flex-col gap-3">
                {resumes.length === 0 ? (
                  <p className="text-sm text-gray-500">
                    등록된 이력서가 없습니다. 새 이력서를 등록해 주세요.
                  </p>
                ) : (
                  resumes.map((resume) => (
                    <div
                      key={resume.id}
                      className={`flex items-center justify-between gap-3 p-4 border rounded-lg bg-white ${
                        getResumeDocId(selectedResume) === getResumeDocId(resume)
                          ? 'border-primary'
                          : 'border-gray-200'
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() =>
                          isAuthenticated ? handleResumeAnalyze(resume) : router.push('/login')
                        }
                        className="flex items-center gap-4 text-left flex-1"
                      >
                        <FileText className="w-6 h-6 text-gray-500" aria-hidden />
                        <div className="flex flex-col">
                          <span className="font-medium">{resume.name}</span>
                          <span className="text-sm text-gray-500">
                            {resume.size} · {resume.date}
                          </span>
                          <span className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-600 w-fit mt-1">
                            {resume.status === 'INIT' && '업로드 완료'}
                            {resume.status === 'PROCESSING' && '분석 중'}
                            {resume.status === 'DONE' && '분석 완료'}
                            {resume.status === 'FAILED' && '실패'}
                          </span>
                        </div>
                      </button>

                      <div className="flex flex-wrap justify-end gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            isAuthenticated
                              ? handleDeleteResume(getResumeDocId(resume))
                              : router.push('/login')
                          }
                          className="h-fit rounded-lg bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-100"
                        >
                          삭제
                        </button>

                        <button
                          type="button"
                          onClick={() => handleOpenPreferenceEdit(resume)}
                          disabled={isAnalyzing || isUpdatingPreferences}
                          className="h-fit rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          조건 수정
                        </button>

                        <button
                          type="button"
                          onClick={() => handleRematch(resume)}
                          disabled={isAnalyzing || isUpdatingPreferences}
                          className="h-fit rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          재분석
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {isAnalyzing && (
              <div className="mt-4 p-4 bg-white/80 rounded-lg flex items-center gap-3 text-sm text-gray-700">
                <div className="w-5 h-5 border-2 border-gray-200 border-t-primary rounded-full animate-spin" />
                <span>AI가 이력서와 채용공고를 최신 정보로 다시 분석하고 있어요...</span>
              </div>
            )}
          </div>

          {/* AI 추천 공고 목록 노출 영역 */}
          {analysisDone && (
            <div className="mt-6 bg-white rounded-xl md:rounded-2xl p-5 md:p-6 border border-blue-200">
              <p className="text-base md:text-base text-gray-600 mb-3">
                {name} 님의 이력서 기준으로 아래 채용 공고를 추천드려요.
              </p>

              <div className="flex flex-col gap-4">
                {pagedMatchedJobs.length === 0 ? (
                  <p className="text-sm md:text-base text-gray-500">
                    표시할 추천 공고가 없습니다.
                  </p>
                ) : (
                  pagedMatchedJobs.map((job) => {
                    const jobKey = getJobKey(job)
                    const badges = getMatchBadges(job)

                    return (
                      <div
                        key={jobKey}
                        className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 border border-gray-200 rounded-xl p-5 md:p-6"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="text-sm md:text-base text-gray-500 mb-1">
                            {job.company}
                          </p>
                          <button
                            onClick={() => handleGoJob(job)}
                            className="font-semibold text-base md:text-lg text-left hover:text-primary transition-colors block"
                          >
                            {job.title}
                          </button>
                          <div className="flex gap-2 mt-2 flex-wrap">
                            {job.category && (
                              <span className="text-xs md:text-sm px-2 py-1 bg-blue-50 rounded text-blue-600">
                                {job.category}
                              </span>
                            )}
                            {job.location && (
                              <span className="text-xs md:text-sm px-2 py-1 bg-slate-100 rounded text-gray-500">
                                {job.location}
                              </span>
                            )}
                            {job.career && (
                              <span className="text-xs md:text-sm px-2 py-1 bg-slate-100 rounded text-gray-500">
                                {job.career}
                              </span>
                            )}
                            {job.salary && (
                              <span className="text-xs md:text-sm px-2 py-1 bg-slate-100 rounded text-gray-500">
                                {job.salary}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex flex-row sm:flex-col items-start sm:items-end justify-between sm:justify-start gap-2 flex-shrink-0 sm:pt-7">
                          <div className="flex items-center gap-3">
                          {job.matchRate > 0 && (
                            <span className="text-primary font-bold text-lg md:text-xl whitespace-nowrap">
                              {job.matchRate}점
                            </span>
                          )}
                          <button onClick={() => handleToggleBookmark(job)} aria-label="북마크">
                            <svg
                              width="22"
                              height="22"
                              viewBox="0 0 24 24"
                              fill={bookmarkIds.includes(jobKey) ? '#2563eb' : '#ffffff'}
                              xmlns="http://www.w3.org/2000/svg"
                            >
                              <path
                                d="M6 3.75C6 3.33579 6.33579 3 6.75 3H17.25C17.6642 3 18 3.33579 18 3.75V21L12 16.5L6 21V3.75Z"
                                stroke={bookmarkIds.includes(jobKey) ? '#2563eb' : '#94a3b8'}
                                strokeWidth="1.8"
                                strokeLinejoin="round"
                              />
                            </svg>
                          </button>
                          </div>

                          {badges.length > 0 && (
                            <div className="flex flex-wrap justify-start sm:justify-end gap-2">
                              {badges.map((badge) => (
                                <button
                                  key={`${jobKey}-${badge}`}
                                  type="button"
                                  onClick={() => setScoreDetailJob(job)}
                                  className={`text-xs md:text-sm px-2 py-1 rounded border font-medium transition-colors ${getBadgeClassName(badge)}`}
                                >
                                  {badge}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })
                )}
              </div>

              {/* AI 매칭결과 전용 페이지네이션 */}
              {totalMatchPages > 1 && (
                <div className="flex justify-center items-center gap-2 mt-6">
                  {Array.from({ length: totalMatchPages }, (_, i) => i + 1).map((page) => (
                    <button
                      key={page}
                      onClick={() => setMatchPage(page)}
                      className={`min-w-[40px] h-10 px-3 rounded-lg text-sm font-medium transition-colors ${
                        matchPage === page
                          ? 'bg-primary text-white'
                          : 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      {page}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {isAuthenticated && (
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() => router.push('/dashboard')}
                className="px-6 py-2.5 md:py-3 md:text-base bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition-colors"
              >
                채용정보로 이동
              </button>
            </div>
          )}
        </div>
      </section>

      {/* 인기 커리어 영역 */}
      <section className="mt-10 md:mt-12">
        <h2 className="text-2xl md:text-3xl font-bold mb-4 md:mb-6">
          인기 커리어
        </h2>

        <div className="mb-4">
          <select
            value={selectedPopularCategory}
            onChange={(e) => setSelectedPopularCategory(e.target.value)}
            className="px-4 py-3 border border-gray-200 rounded-xl text-sm md:text-base bg-white w-full sm:w-auto min-h-[48px]"
          >
            <option value="전체">전체</option>
            <option value="IT/개발">IT/개발</option>
            <option value="디자인">디자인</option>
            <option value="마케팅">마케팅</option>
            <option value="영업·고객상담">영업·고객상담</option>
            <option value="사무·총무">사무·총무</option>
            <option value="교육">교육</option>
            <option value="의료/바이오">의료/바이오</option>
            <option value="운전/운송/배송">운전/운송/배송</option>
            <option value="건축/시설">건축/시설</option>
          </select>
        </div>

        {isLoadingJobs ? (
          <div className="p-8 md:p-10 bg-white rounded-2xl border border-gray-200 text-center">
            <div className="w-10 h-10 border-2 border-gray-200 border-t-primary rounded-full animate-spin mx-auto mb-4" />
            <p className="text-sm md:text-base text-gray-500">
              DB 공고를 불러오는 중입니다...
            </p>
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-4 md:gap-6">
              {popularJobs.length === 0 ? (
                <div className="bg-white rounded-2xl p-6 md:p-8 border border-gray-200 text-sm md:text-base text-gray-500">
                  표시할 공고가 없습니다.
                </div>
              ) : (
                popularJobs.map((job) => {
                  const jobKey = getJobKey(job)

                  return (
                    <div
                      key={jobKey}
                      className="relative bg-white rounded-2xl p-6 md:p-8 shadow-sm border border-gray-200"
                    >
                      <button
                        onClick={() => handleToggleBookmark(job)}
                        className="absolute top-5 right-5 md:top-6 md:right-6"
                        aria-label="북마크"
                      >
                        <svg
                          width="22"
                          height="22"
                          viewBox="0 0 24 24"
                          fill={bookmarkIds.includes(jobKey) ? '#2563eb' : '#ffffff'}
                          xmlns="http://www.w3.org/2000/svg"
                        >
                          <path
                            d="M6 3.75C6 3.33579 6.33579 3 6.75 3H17.25C17.6642 3 18 3.33579 18 3.75V21L12 16.5L6 21V3.75Z"
                            stroke={bookmarkIds.includes(jobKey) ? '#2563eb' : '#94a3b8'}
                            strokeWidth="1.8"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </button>

                      <button
                        onClick={() => handleGoPopularJob(job)}
                        className="font-bold text-lg md:text-2xl mb-2 hover:text-primary transition-colors text-left pr-10 block"
                      >
                        {job.title}
                      </button>

                      <p className="text-base md:text-lg text-gray-500 mb-3">
                        {job.company}
                      </p>

                      <div className="flex gap-2 flex-wrap">
                        {job.category && (
                          <span className="text-xs md:text-sm px-2 py-1 bg-blue-50 rounded text-blue-600">
                            {job.category}
                          </span>
                        )}
                        {job.location && (
                          <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">
                            {job.location}
                          </span>
                        )}
                        {job.career && (
                          <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">
                            {job.career}
                          </span>
                        )}
                        {job.salary && (
                          <span className="text-xs px-2 py-1 bg-slate-100 rounded text-gray-500">
                            {job.salary}
                          </span>
                        )}
                      </div>
                    </div>
                  )
                })
              )}
            </div>

            {/* 인기 커리어 전용 페이지네이션 */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center gap-2 mt-6">
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page)}
                    className={`min-w-[40px] h-10 px-3 rounded-lg text-sm font-medium transition-colors ${
                      currentPage === page
                        ? 'bg-primary text-white'
                        : 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    {page}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </section>
      {editingResume && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-5 shadow-xl md:p-7">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h3 className="text-xl font-bold text-gray-900">
                  채용 조건 수정
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                  수정된 조건은 이력서와 함께 저장되며, 저장 후 채용공고를 다시 추천합니다.
                </p>
              </div>

              <button
                type="button"
                onClick={handleClosePreferenceEdit}
                disabled={isUpdatingPreferences}
                className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
                aria-label="조건 수정 닫기"
              >
                <X className="h-5 w-5" aria-hidden />
              </button>
            </div>

            <div className="mb-5 rounded-xl border border-blue-100 bg-blue-50 p-4">
              <p className="text-xs text-gray-500">수정할 이력서</p>
              <div className="mt-2 flex items-center gap-3">
                <FileText
                  className="h-6 w-6 flex-shrink-0 text-primary"
                  aria-hidden
                />
                <p className="min-w-0 truncate font-medium text-gray-900">
                  {editingResume.name ||
                    editingResume.filename ||
                    '제목 없는 이력서'}
                </p>
              </div>
            </div>

            <div className="space-y-6">
              <PreferenceOptionGroup
                title="희망 직무"
                options={ROLE_OPTIONS}
                selectedValues={editDesiredRoles}
                onToggle={(value) =>
                  toggleSelectedValue(setEditDesiredRoles, value)
                }
              />

              <PreferenceOptionGroup
                title="희망 지역"
                options={LOCATION_OPTIONS}
                selectedValues={editDesiredLocations}
                onToggle={(value) =>
                  toggleSelectedValue(setEditDesiredLocations, value)
                }
              />

              <PreferenceOptionGroup
                title="고용 형태"
                options={EMPLOYMENT_TYPE_OPTIONS}
                selectedValues={editEmploymentTypes}
                onToggle={(value) =>
                  toggleSelectedValue(setEditEmploymentTypes, value)
                }
              />
            </div>

            <p className="mt-5 text-xs text-gray-400">
              선택하지 않은 항목은 제한 없이 전체 공고를 대상으로 합니다.
            </p>

            {(editDesiredRoles.length > 0 ||
              editDesiredLocations.length > 0 ||
              editEmploymentTypes.length > 0) && (
              <button
                type="button"
                onClick={() => {
                  setEditDesiredRoles([])
                  setEditDesiredLocations([])
                  setEditEmploymentTypes([])
                }}
                disabled={isUpdatingPreferences}
                className="mt-3 text-sm font-medium text-gray-500 underline hover:text-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                조건 전체 초기화
              </button>
            )}

            <div className="mt-7 flex justify-end gap-3 border-t border-gray-100 pt-5">
              <button
                type="button"
                onClick={handleClosePreferenceEdit}
                disabled={isUpdatingPreferences}
                className="rounded-xl border border-gray-200 px-5 py-2.5 font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                취소
              </button>

              <button
                type="button"
                onClick={handleSavePreferenceEdit}
                disabled={isUpdatingPreferences}
                className="rounded-xl bg-primary px-5 py-2.5 font-medium text-white hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isUpdatingPreferences ? '조건 저장 중...' : '저장 후 재분석'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showPreferenceModal && pendingFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-5 shadow-xl md:p-7">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h3 className="text-xl font-bold text-gray-900">
                  이력서 등록 조건 설정
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                  이력서와 함께 저장할 희망 채용 조건을 선택해주세요.
                </p>
              </div>

              <button
                type="button"
                onClick={handleCancelUpload}
                disabled={isAnalyzing}
                className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
                aria-label="조건 설정 닫기"
              >
                <X className="h-5 w-5" aria-hidden />
              </button>
            </div>

            <div className="mb-5 rounded-xl border border-blue-100 bg-blue-50 p-4">
              <p className="text-xs text-gray-500">선택한 이력서</p>
              <div className="mt-2 flex items-center gap-3">
                <FileText className="h-6 w-6 text-primary" aria-hidden />
                <div className="min-w-0">
                  <p className="truncate font-medium text-gray-900">
                    {pendingFile.name}
                  </p>
                  <p className="text-sm text-gray-500">
                    {Math.round(pendingFile.size / 1024)} KB
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-6">
              <PreferenceOptionGroup
                title="희망 직무"
                options={ROLE_OPTIONS}
                selectedValues={desiredRoles}
                onToggle={(value) => toggleSelectedValue(setDesiredRoles, value)}
              />

              <PreferenceOptionGroup
                title="희망 지역"
                options={LOCATION_OPTIONS}
                selectedValues={desiredLocations}
                onToggle={(value) => toggleSelectedValue(setDesiredLocations, value)}
              />

              <PreferenceOptionGroup
                title="고용 형태"
                options={EMPLOYMENT_TYPE_OPTIONS}
                selectedValues={employmentTypes}
                onToggle={(value) => toggleSelectedValue(setEmploymentTypes, value)}
              />
            </div>

            <p className="mt-5 text-xs text-gray-400">
              선택하지 않은 항목은 제한 없이 전체 공고를 대상으로 합니다.
            </p>

            {(desiredRoles.length > 0 ||
              desiredLocations.length > 0 ||
              employmentTypes.length > 0) && (
              <button
                type="button"
                onClick={() => {
                  setDesiredRoles([])
                  setDesiredLocations([])
                  setEmploymentTypes([])
                }}
                disabled={isAnalyzing}
                className="mt-3 text-sm font-medium text-gray-500 underline hover:text-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                조건 전체 초기화
              </button>
            )}

            <div className="mt-7 flex justify-end gap-3 border-t border-gray-100 pt-5">
              <button
                type="button"
                onClick={handleCancelUpload}
                disabled={isAnalyzing}
                className="rounded-xl border border-gray-200 px-5 py-2.5 font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                취소
              </button>

              <button
                type="button"
                onClick={handleConfirmUpload}
                disabled={isAnalyzing}
                className="rounded-xl bg-primary px-5 py-2.5 font-medium text-white hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isAnalyzing ? '등록 및 분석 중...' : '등록 및 분석'}
              </button>
            </div>
          </div>
        </div>
      )}

      <ScoreDetailModal job={scoreDetailJob} onClose={() => setScoreDetailJob(null)} />
    </main>
  )
}
