'use client'

import { useEffect, useState } from 'react'
import {
  Sparkles,
  CheckCircle2,
  ShieldCheck,
  CircleHelp,
  AlertTriangle,
  XCircle,
  Target,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'

const TIP_INTERVAL = 10000

const MATCHING_TIPS = [
  {
    icon: Sparkles,
    badge: 'JOBPICK TIP',
    title: 'AI 매칭 결과는 5가지 유형으로 표시돼요',
    description:
      '분석이 끝나면 공고가 AI 적합, 지원 가능, 보통, 정보 부족, 부적합으로 구분됩니다.',
    subText:
      '단순 점수뿐 아니라 지원조건과 판단 근거를 함께 확인해 보세요.',
    iconClass: 'bg-blue-50 text-primary',
  },
  {
    icon: CheckCircle2,
    badge: 'AI 적합',
    title: 'AI 적합은 어떤 공고인가요?',
    description:
      '직무 적합도가 높고, 이를 뒷받침할 판단 근거도 충분한 공고입니다.',
    subText:
      '추천도가 높은 공고지만 실제 지원 전에는 공고 원문도 함께 확인해 주세요.',
    iconClass: 'bg-emerald-50 text-emerald-600',
  },
  {
    icon: ShieldCheck,
    badge: '지원 가능',
    title: '지원 가능은 무슨 뜻인가요?',
    description:
      '학력·경력·기술·자격증 등 필수 지원조건을 상당 부분 충족한 공고입니다.',
    subText:
      '세부 자격요건과 우대사항을 확인하면 지원 여부를 판단하는 데 도움이 됩니다.',
    iconClass: 'bg-blue-50 text-blue-600',
  },
  {
    icon: CircleHelp,
    badge: '보통',
    title: '보통으로 표시된 공고도 확인해 보세요',
    description:
      '일부 조건은 이력서와 일치하지만 적극적인 추천 기준에는 아직 미치지 않은 공고입니다.',
    subText:
      '관련 경험이나 기술을 이력서에 더 구체적으로 작성하면 결과가 달라질 수 있어요.',
    iconClass: 'bg-gray-100 text-gray-600',
  },
  {
    icon: AlertTriangle,
    badge: '정보 부족',
    title: '정보 부족은 부적합과 달라요',
    description:
      '공고 또는 이력서의 정보가 부족해 AI가 정확하게 판단하기 어려운 경우입니다.',
    subText:
      '이력서의 경력, 기술, 자격증 정보를 보완한 뒤 다시 확인해 보세요.',
    iconClass: 'bg-amber-50 text-amber-600',
  },
  {
    icon: XCircle,
    badge: '부적합',
    title: '부적합은 필수조건도 함께 확인해요',
    description:
      '필수조건을 충족하지 못했거나 현재 이력서와의 매칭 수준이 낮은 공고입니다.',
    subText:
      '점수만 보기보다 어떤 필수조건이 미충족되었는지 함께 확인하는 것이 중요해요.',
    iconClass: 'bg-red-50 text-red-600',
  },
  {
    icon: Target,
    badge: '점수 보는 법',
    title: '매칭 결과에는 3가지 점수가 있어요',
    description:
      '적합도, 자격 통과 가능성, 판단 근거 충분도를 함께 보고 최종 매칭 결과를 결정합니다.',
    subText:
      '한 가지 점수만 보기보다 세 점수를 함께 비교하면 결과를 더 정확하게 이해할 수 있어요.',
    iconClass: 'bg-violet-50 text-violet-600',
  },
]

export default function AiMatchingTipModal({
  open,
  loadingStep = 'AI 매칭 분석 중...',
}) {
  const [tipIndex, setTipIndex] = useState(0)
  const [direction, setDirection] = useState('next')

  useEffect(() => {
    if (!open) {
      setTipIndex(0)
      setDirection('next')
      return undefined
    }

    const timer = setTimeout(() => {
      setDirection('next')
      setTipIndex((prev) => (prev + 1) % MATCHING_TIPS.length)
    }, TIP_INTERVAL)

    return () => clearTimeout(timer)
  }, [open, tipIndex])

  if (!open) return null

  const tip = MATCHING_TIPS[tipIndex]
  const Icon = tip.icon

  const goPrev = () => {
    setDirection('prev')
    setTipIndex(
      (prev) => (prev - 1 + MATCHING_TIPS.length) % MATCHING_TIPS.length
    )
  }

  const goNext = () => {
    setDirection('next')
    setTipIndex((prev) => (prev + 1) % MATCHING_TIPS.length)
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/45 px-4 backdrop-blur-[2px]">
      <div className="w-full max-w-xl overflow-hidden rounded-3xl border border-white/60 bg-white shadow-2xl">

        {/* 현재 AI 분석 상태 */}
        <div className="border-b border-gray-100 px-6 py-5 md:px-8">
          <div className="flex items-center gap-3">
            <div className="h-5 w-5 shrink-0 rounded-full border-2 border-gray-200 border-t-primary animate-spin" />

            <div>
              <p className="text-sm font-semibold text-gray-900">
                AI 매칭 분석 중
              </p>

              <p
                key={loadingStep}
                className="mt-0.5 text-xs text-gray-500 animate-fade-in"
              >
                {loadingStep}
              </p>
            </div>

            <div className="ml-auto">
              <span className="text-xs font-medium text-gray-400">
                {tipIndex + 1} / {MATCHING_TIPS.length}
              </span>
            </div>
          </div>
        </div>

        {/* TIP 카드 */}
        <div className="overflow-hidden px-6 pb-6 pt-7 md:px-8 md:pb-8">
          <div
            key={tipIndex}
            className={
              direction === 'prev'
                ? 'animate-slide-in-left'
                : 'animate-slide-in'
            }
          >
            <div
              className={`flex h-12 w-12 items-center justify-center rounded-2xl ${tip.iconClass}`}
            >
              <Icon className="h-6 w-6" />
            </div>

            <div className="mt-5">
              <span className="inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-gray-500">
                {tip.badge}
              </span>

              <h2 className="mt-3 text-xl font-bold leading-snug text-gray-900 md:text-2xl">
                {tip.title}
              </h2>

              <p className="mt-4 text-sm leading-7 text-gray-700 md:text-base">
                {tip.description}
              </p>

              <p className="mt-3 text-sm leading-6 text-gray-500">
                {tip.subText}
              </p>
            </div>
          </div>

          {/* 이전 / 다음 + 페이지 점 */}
          <div className="mt-7 flex items-center justify-between">
            <button
              type="button"
              onClick={goPrev}
              className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-200 text-gray-500 transition-colors hover:bg-slate-50 hover:text-gray-800"
              aria-label="이전 팁"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>

            <div className="flex items-center gap-1.5">
              {MATCHING_TIPS.map((_, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => {
                    setDirection(index < tipIndex ? 'prev' : 'next')
                    setTipIndex(index)
                  }}
                  aria-label={`${index + 1}번째 팁`}
                  className={`h-2 rounded-full transition-all duration-300 ${
                    index === tipIndex
                      ? 'w-5 bg-primary'
                      : 'w-2 bg-gray-200 hover:bg-gray-300'
                  }`}
                />
              ))}
            </div>

            <button
              type="button"
              onClick={goNext}
              className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-200 text-gray-500 transition-colors hover:bg-slate-50 hover:text-gray-800"
              aria-label="다음 팁"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {/* 사용방법 안내 */}
          <p className="mt-6 border-t border-gray-100 pt-5 text-center text-xs text-gray-400">
            자세한 매칭 기준과 결과 해석 방법은{' '}
            <span className="font-medium text-gray-500">사용방법 탭</span>에서
            확인할 수 있어요.
          </p>
        </div>
      </div>
    </div>
  )
}