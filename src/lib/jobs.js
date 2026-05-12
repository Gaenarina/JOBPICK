/*
export const DASHBOARD_JOBS = [
  { id: 'd-1', title: '의료기기 물품 입출고 관리 및 사무 보조 채용', company: '(주)프롬메드', location: '경기 하남시', career: '신입·경력1년↑', category: '사무·총무', matchRate: 71, salary: '3,400만원' },
  { id: 'd-2', title: 'DB전문영업본부 경력 보험설계사', company: '(주)미래전략금융서비스', location: '서울 중구', career: '경력', category: '영업·고객상담', matchRate: 60, salary: '3,800만원' },
  { id: 'd-3', title: '백엔드 서버 개발자', company: '테크스타트업(주)', location: '서울 강남구', career: '신입·경력2년↑', category: '개발·데이터', matchRate: 85, salary: '4,200만원' },
  { id: 'd-4', title: '온라인 MD 주니어', company: '(주)커머스랩', location: '부산 해운대구', career: '신입', category: '마케팅·광고', matchRate: 66, salary: '3,300만원' },
]

export const INTERN_JOBS = [
  { id: 'i-1', title: '의료기기 물품 입출고 관리 및 사무 보조 채용', company: '(주)프롬메드', location: '경기 하남시', career: '신입·경력1년↑', category: '사무·총무', salary: '3,400만원', matchRate: 71 },
  { id: 'i-2', title: 'DB전문영업본부 경력 보험설계사', company: '(주)미래전략금융서비스', location: '서울 중구', career: '경력', category: '영업·고객상담', salary: '3,800만원', matchRate: 60 },
  { id: 'i-3', title: '프론트엔드 인턴', company: '(주)웨이브코어', location: '서울 마포구', career: '신입·인턴', category: '개발·데이터', salary: '3,200만원', matchRate: 78 },
]

export const ALL_JOBS = [...DASHBOARD_JOBS, ...INTERN_JOBS]

export function getJobById(id) {
  return ALL_JOBS.find((job) => String(job.id) === String(id))
}
*/

export const DASHBOARD_JOBS = []

export const INTERN_JOBS = []

export const ALL_JOBS = []

export function getJobById(id) {
  return ALL_JOBS.find((job) => String(job.id) === String(id))
}