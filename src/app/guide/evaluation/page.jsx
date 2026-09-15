import Link from 'next/link'
import {
  ArrowLeft,
  Target,
  ShieldCheck,
  FileSearch,
  AlertCircle,
  ChevronDown,
  CheckCircle2,
  CircleHelp,
  AlertTriangle,
  XCircle,
  Brain,
  BriefcaseBusiness,
  GraduationCap,
  Wrench,
  Award,
  ClipboardCheck,
} from 'lucide-react'

const resultTypes = [
  {
    name: 'AI 적합',
    icon: CheckCircle2,
    className: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    description:
      '직무 적합도가 높고, 이를 뒷받침할 판단 근거도 충분한 공고입니다.',
  },
  {
    name: '지원 가능',
    icon: ShieldCheck,
    className: 'bg-blue-50 text-blue-700 border-blue-200',
    description:
      '필수 지원조건을 상당 부분 충족하여 실제 지원을 고려할 수 있는 공고입니다.',
  },
  {
    name: '보통',
    icon: CircleHelp,
    className: 'bg-gray-50 text-gray-700 border-gray-200',
    description:
      '일부 조건은 일치하지만 적극적인 추천 기준에는 아직 미치지 않은 공고입니다.',
  },
  {
    name: '정보 부족',
    icon: AlertTriangle,
    className: 'bg-amber-50 text-amber-700 border-amber-200',
    description:
      '공고 또는 이력서 정보가 부족하여 정확한 판단이 어려운 경우입니다.',
  },
  {
    name: '부적합',
    icon: XCircle,
    className: 'bg-red-50 text-red-700 border-red-200',
    description:
      '필수조건을 충족하지 못했거나 현재 이력서와의 매칭 수준이 낮은 공고입니다.',
  },
]

const scoreCards = [
  {
    icon: Target,
    title: '적합도',
    description:
      '이력서의 경험과 역량이 채용공고의 직무와 얼마나 잘 맞는지를 종합적으로 보여줍니다.',
  },
  {
    icon: ShieldCheck,
    title: '자격 통과 가능성',
    description:
      '학력·경력·기술·자격증 등 공고의 필수 지원조건을 얼마나 충족하는지 보여줍니다.',
  },
  {
    icon: FileSearch,
    title: '판단 근거 충분도',
    description:
      '현재 채용공고에 AI가 매칭을 판단할 수 있는 정보가 얼마나 충분한지 보여줍니다.',
  },
]

const accessibilityItems = [
  {
    icon: BriefcaseBusiness,
    label: '경력',
    value: '30',
  },
  {
    icon: GraduationCap,
    label: '학력',
    value: '20',
  },
  {
    icon: Wrench,
    label: '필수 기술',
    value: '20',
  },
  {
    icon: Award,
    label: '필수 자격증',
    value: '15',
  },
  {
    icon: ClipboardCheck,
    label: '필수 자격요건',
    value: '15',
  },
]

const confidenceItems = [
  ['필수 기술 정보', '+25'],
  ['담당업무 정보', '+25'],
  ['필수 자격요건', '+20'],
  ['필수 자격증', '+5'],
  ['공고 내용의 충분성', '최대 +20'],
  ['학력·경력 정보', '+5'],
]

export default function EvaluationGuidePage() {
  return (
    <main className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-4xl px-5 py-10 md:px-8 md:py-14">

        {/* 뒤로가기 */}
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-gray-500 transition-colors hover:text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          홈으로 돌아가기
        </Link>

        {/* 헤더 */}
        <header className="mt-6">
          <p className="text-sm font-semibold text-primary">
            JOBPICK GUIDE
          </p>

          <h1 className="mt-2 text-3xl font-bold text-gray-900 md:text-4xl">
            매칭 평가 기준
          </h1>

          <p className="mt-3 max-w-2xl leading-7 text-gray-600">
            JOBPICK은 이력서와 채용공고를 분석하여
            지원자에게 적합한 공고인지 종합적으로 판단합니다.
          </p>
        </header>

        {/* 1. 매칭 결과 */}
        <section className="mt-12">
          <h2 className="text-xl font-bold text-gray-900">
            매칭 결과는 이렇게 표시됩니다.
          </h2>

          <p className="mt-2 text-sm leading-6 text-gray-500">
            분석 결과에 따라 공고는 5가지 유형으로 구분됩니다.
          </p>

          <div className="mt-5 overflow-hidden rounded-2xl border border-gray-200 bg-white">
            {resultTypes.map((result, index) => {
              const Icon = result.icon

              return (
                <div
                  key={result.name}
                  className={`flex flex-col gap-3 p-5 sm:flex-row sm:items-center ${
                    index !== resultTypes.length - 1
                      ? 'border-b border-gray-100'
                      : ''
                  }`}
                >
                  <div className="flex w-32 shrink-0 items-center">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-semibold ${result.className}`}
                    >
                      <Icon className="h-4 w-4" />
                      {result.name}
                    </span>
                  </div>

                  <p className="text-sm leading-6 text-gray-600">
                    {result.description}
                  </p>
                </div>
              )
            })}
          </div>
        </section>

        {/* 2. 3가지 점수 */}
        <section className="mt-12">
          <h2 className="text-xl font-bold text-gray-900">
            이 결과는 3가지 점수를 함께 보고 결정해요.
          </h2>

          <p className="mt-2 text-sm leading-6 text-gray-500">
            하나의 점수만 보는 것이 아니라 직무 적합성, 지원조건,
            판단 가능한 정보의 충분성을 함께 분석합니다.
          </p>

          <div className="mt-5 grid gap-4 md:grid-cols-3">
            {scoreCards.map(({ icon: Icon, title, description }) => (
              <article
                key={title}
                className="rounded-2xl border border-gray-200 bg-white p-5"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-primary">
                  <Icon className="h-5 w-5" />
                </div>

                <h3 className="mt-4 font-bold text-gray-900">
                  {title}
                </h3>

                <p className="mt-2 text-sm leading-6 text-gray-600">
                  {description}
                </p>
              </article>
            ))}
          </div>
        </section>

        {/* 3. 필수조건 안내 */}
        <section className="mt-8">
          <div className="flex gap-4 rounded-2xl border border-red-200 bg-red-50 p-5">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />

            <div>
              <h3 className="font-bold text-red-700">
                적합도가 높아도 부적합일 수 있습니다.
              </h3>

              <p className="mt-2 text-sm leading-6 text-red-700">
                필수 기술, 학력, 경력, 자격증 또는 필수 자격요건을
                충족하지 못한 경우에는 다른 점수가 높더라도
                최종 결과가 부적합으로 표시될 수 있습니다.
              </p>
            </div>
          </div>
        </section>

        {/* 4. 상세 평가 기준 */}
        <section className="mt-8 mb-12">
          <details className="group overflow-hidden rounded-2xl border border-gray-200 bg-white">

            <summary className="flex cursor-pointer list-none items-center justify-between p-5">
              <div>
                <p className="font-bold text-gray-900">
                  상세 평가 기준 보기
                </p>

                <p className="mt-1 text-sm text-gray-500">
                  각 점수가 어떤 정보를 바탕으로 계산되는지 확인할 수 있어요.
                </p>
              </div>

              <ChevronDown className="h-5 w-5 shrink-0 text-gray-400 transition-transform group-open:rotate-180" />
            </summary>

            <div className="border-t border-gray-100 px-5 md:px-6">

              {/* 적합도 */}
              <DetailSection
                number="1"
                title="적합도는 무엇을 비교하나요?"
                description="공고에 존재하는 정보를 바탕으로 룰 기반 평가와 AI 의미 분석을 함께 사용합니다."
              >
                <div className="grid gap-4 md:grid-cols-3">

                  <SimpleInfoCard
                    icon={ClipboardCheck}
                    title="룰 기반 평가"
                    description="공고에 명시된 조건과 이력서 정보를 직접 비교합니다."
                    items={[
                      '기술',
                      '학력',
                      '경력',
                      '자격증',
                      '필수 자격요건',
                    ]}
                  />

                  <SimpleInfoCard
                    icon={Brain}
                    title="AI 의미 분석"
                    description="표현이 정확히 같지 않아도 경험과 직무의 의미적 유사성을 분석합니다."
                    items={[
                      '이력서 ↔ 공고 전체',
                      '경험 ↔ 담당업무',
                      '경험 ↔ 자격요건',
                    ]}
                  />

                  <SimpleInfoCard
                    icon={Target}
                    title="NCS 직무역량"
                    description="공고의 명확한 판단 근거가 부족할 때 직무역량을 보완적으로 비교합니다."
                    items={[
                      '필요한 경우에만 적용',
                      '모든 공고에 적용되지 않음',
                    ]}
                  />

                </div>

                <div className="mt-4 rounded-xl bg-gray-50 px-4 py-3 text-sm leading-6 text-gray-600">
                  공고에 없는 조건은 0점으로 처리하지 않고 평가에서 제외한 뒤,
                  실제 사용할 수 있는 항목끼리 점수 비중을 다시 조정합니다.
                </div>
              </DetailSection>

              {/* 자격 통과 가능성 */}
              <DetailSection
                number="2"
                title="자격 통과 가능성은 무엇을 보나요?"
                description="공고에서 실제 확인된 필수 지원조건만 비교합니다."
              >
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                  {accessibilityItems.map(
                    ({ icon: Icon, label, value }) => (
                      <div
                        key={label}
                        className="rounded-xl border border-gray-200 bg-gray-50 p-4 text-center"
                      >
                        <Icon className="mx-auto h-5 w-5 text-primary" />

                        <p className="mt-3 text-sm font-medium text-gray-700">
                          {label}
                        </p>

                        <p className="mt-1 text-xl font-bold text-gray-900">
                          {value}
                        </p>

                        <p className="text-xs text-gray-400">
                          중요도
                        </p>
                      </div>
                    )
                  )}
                </div>

                <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50 p-4">
                  <p className="text-sm leading-6 text-blue-700">
                    공고에 존재하지 않는 조건은 평가에서 제외합니다.
                    확인할 수 있는 필수조건이 하나도 없는 경우에는
                    모든 조건을 충족했다고 판단하지 않고
                    <strong> 중립값 50점</strong>을 제공합니다.
                  </p>
                </div>
              </DetailSection>

              {/* 판단 근거 충분도 */}
              <DetailSection
                number="3"
                title="판단 근거 충분도는 어떻게 정해지나요?"
                description="지원자가 얼마나 우수한지를 평가하는 점수가 아니라, 공고에 판단할 정보가 얼마나 충분한지를 나타냅니다."
                last
              >
                <div className="overflow-hidden rounded-xl border border-gray-200">
                  {confidenceItems.map(([label, value], index) => (
                    <div
                      key={label}
                      className={`flex items-center justify-between bg-white px-4 py-3 ${
                        index !== confidenceItems.length - 1
                          ? 'border-b border-gray-100'
                          : ''
                      }`}
                    >
                      <span className="text-sm text-gray-600">
                        {label}
                      </span>

                      <span className="text-sm font-bold text-gray-900">
                        {value}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="mt-4 rounded-xl bg-amber-50 p-4">
                  <p className="text-sm leading-6 text-amber-700">
                    예를 들어 담당업무나 자격요건이 거의 작성되지 않은 공고는
                    이력서가 부족해서가 아니라
                    <strong> 공고 자체의 판단 정보가 부족하기 때문에</strong>
                    판단 근거 충분도가 낮아질 수 있습니다.
                  </p>
                </div>
              </DetailSection>

            </div>
          </details>
        </section>

      </div>
    </main>
  )
}

function DetailSection({
  number,
  title,
  description,
  children,
  last = false,
}) {
  return (
    <section
      className={`py-7 ${
        last ? '' : 'border-b border-gray-100'
      }`}
    >
      <div className="mb-5 flex gap-3">

        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">
          {number}
        </div>

        <div>
          <h3 className="font-bold text-gray-900">
            {title}
          </h3>

          <p className="mt-1 text-sm leading-6 text-gray-500">
            {description}
          </p>
        </div>

      </div>

      {children}
    </section>
  )
}

function SimpleInfoCard({
  icon: Icon,
  title,
  description,
  items,
}) {
  return (
    <div className="rounded-xl border border-gray-200 p-4">

      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-primary">
        <Icon className="h-4 w-4" />
      </div>

      <h4 className="mt-3 font-bold text-gray-900">
        {title}
      </h4>

      <p className="mt-1 text-xs leading-5 text-gray-500">
        {description}
      </p>

      <ul className="mt-4 space-y-2">
        {items.map((item) => (
          <li
            key={item}
            className="flex items-start gap-2 text-xs text-gray-600"
          >
            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />

            {item}
          </li>
        ))}
      </ul>

    </div>
  )
}