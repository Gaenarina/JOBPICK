'use client'

import { useEffect, useState } from 'react'
import {
  Sparkles,
  CircleHelp,
  Target,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'

const TIP_INTERVAL = 6000

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
    icon: Target,
    badge: '상세 점수 보기',
    title: '추천 공고의 숫자 점수를 클릭해 보세요!',
    description:
      '공고에 표시된 매칭 점수를 클릭하면 AI가 계산한 상세 분석 내용을 확인할 수 있어요.',
    subText:
      '룰 기반 점수, 의미 유사도, NCS 직무역량 점수와 주요 판단 근거를 자세히 볼 수 있습니다.',
    iconClass: 'bg-violet-50 text-violet-600',
  },
  {
    icon: CircleHelp,
    badge: '점수 보는 법',
    title: '매칭 결과에는 3가지 점수가 있어요',
    description:
      '적합도, 자격 통과 가능성, 판단 근거 충분도를 함께 보고 최종 매칭 결과를 결정합니다.',
    subText:
      '한 가지 점수만 보기보다 세 점수를 함께 비교하면 결과를 더 정확하게 이해할 수 있어요.',
    iconClass: 'bg-slate-100 text-slate-600',
  },
  {
    icon: Sparkles,
    badge: 'AI 요약',
    title: 'AI 요약 기능으로 결과를 간단하게 확인해 보세요!',
    description:
      'AI 요약 기능을 사용하면 추천 공고의 주요 결과를 한눈에 확인할 수 있어요.',
    subText:
      '추천 근거와 확인하면 좋은 점을 간단하게 정리해서 볼 수 있습니다.',
    iconClass: 'bg-blue-50 text-primary',
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
      setTipIndex(
        (prev) => (prev + 1) % MATCHING_TIPS.length
      )
    }, TIP_INTERVAL)

    return () => clearTimeout(timer)
  }, [open, tipIndex])

  if (!open) return null

  const tip = MATCHING_TIPS[tipIndex]
  const Icon = tip.icon

  const goPrev = () => {
    setDirection('prev')

    setTipIndex(
      (prev) =>
        (prev - 1 + MATCHING_TIPS.length) %
        MATCHING_TIPS.length
    )
  }

  const goNext = () => {
    setDirection('next')

    setTipIndex(
      (prev) => (prev + 1) % MATCHING_TIPS.length
    )
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/45 px-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-label="AI 매칭 분석 안내"
    >
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
                aria-live="polite"
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

        {/* TIP 영역 */}
        <div className="flex min-h-[440px] flex-col overflow-hidden px-6 pb-6 pt-7 md:min-h-[420px] md:px-8 md:pb-8">

          {/* 카드 내용 */}
          <div className="min-h-[265px]">
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
                <Icon
                  className="h-6 w-6"
                  aria-hidden="true"
                />
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
          </div>

          {/* 이전 / 다음 + 페이지 점 */}
          <div className="mt-auto flex items-center justify-between pt-7">
            <button
              type="button"
              onClick={goPrev}
              className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-200 text-gray-500 transition-colors hover:bg-slate-50 hover:text-gray-800"
              aria-label="이전 팁"
            >
              <ChevronLeft
                className="h-4 w-4"
                aria-hidden="true"
              />
            </button>

            <div className="flex items-center gap-1.5">
              {MATCHING_TIPS.map((_, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => {
                    setDirection(
                      index < tipIndex ? 'prev' : 'next'
                    )

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
              <ChevronRight
                className="h-4 w-4"
                aria-hidden="true"
              />
            </button>
          </div>

          {/* 매칭 평가기준 안내 */}
          <p className="mt-6 border-t border-gray-100 pt-5 text-center text-xs text-gray-400">
            자세한 매칭 기준과 결과 해석 방법은{' '}
            <a
              href="/guide/evaluation"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-primary underline underline-offset-2 transition-colors hover:text-blue-700"
            >
              매칭 평가기준 탭
            </a>
            에서 확인할 수 있어요.
          </p>
        </div>
      </div>
    </div>
  )
}