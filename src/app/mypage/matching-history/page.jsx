"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { onAuthStateChanged } from "firebase/auth";
import { auth } from "@/lib/firebase";

const SORT_OPTIONS = [
  { value: "latest", label: "최신 매칭순" },
  { value: "score", label: "매칭률 높은순" },
];

export default function MatchingHistoryPage() {
  const [user, setUser] = useState(null);
  const [results, setResults] = useState([]);
  const [selectedResumeId, setSelectedResumeId] = useState("ALL");
  const [sortOption, setSortOption] = useState("latest");
  const [loading, setLoading] = useState(true);
  
  // 컴포넌트 내부로 안전하게 이동
  const [page, setPage] = useState(1);
  const itemsPerPage = 10;

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);

      if (!currentUser) {
        setLoading(false);
        return;
      }

      await fetchMatchingResults(currentUser.uid);
    });

    return () => unsubscribe();
  }, []);

  // 필터나 정렬이 변경되면 페이지를 1페이지로 리셋
  useEffect(() => {
    setPage(1);
  }, [selectedResumeId, sortOption]);

  const fetchMatchingResults = async (userId) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/matching-history?userId=${userId}`);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || "매칭 결과 조회 실패");
      }

      const data = await response.json();
      setResults(data.results || []);
    } catch (error) {
      console.error("[매칭 결과 조회 오류]", error);
      alert("매칭 결과를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const resumeOptions = useMemo(() => {
    const uniqueResumeMap = new Map();

    results.forEach((item) => {
      if (!uniqueResumeMap.has(item.resumeId)) {
        uniqueResumeMap.set(item.resumeId, {
          resumeId: item.resumeId,
          resumeFilename: item.resumeFilename,
        });
      }
    });

    return [
      { resumeId: "ALL", resumeFilename: "전체 이력서" },
      ...Array.from(uniqueResumeMap.values()),
    ];
  }, [results]);

  const filteredResults = useMemo(() => {
    const filtered = results.filter((item) => {
      if (selectedResumeId === "ALL") return true;
      return item.resumeId === selectedResumeId;
    });

    return [...filtered].sort((a, b) => {
      if (sortOption === "score") {
        return Number(b.score || 0) - Number(a.score || 0);
      }
      return new Date(b.updatedAt || 0).getTime() - new Date(a.updatedAt || 0).getTime();
    });
  }, [results, selectedResumeId, sortOption]);

  // 페이지네이션 계산
  const totalPages = Math.ceil(filteredResults.length / itemsPerPage);
  const startIndex = (page - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const pagedResults = filteredResults.slice(startIndex, endIndex);

  const formatScore = (score) => {
    const numberScore = Number(score || 0);
    return Number.isNaN(numberScore) ? 0 : Math.round(numberScore);
  };

  const formatDate = (dateValue) => {
    if (!dateValue) return "날짜 정보 없음";
    const date = new Date(dateValue);
    if (Number.isNaN(date.getTime())) return dateValue;

    return date.toLocaleDateString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  };

  // 1. 로딩 스켈레톤/메시지 공통 처리
  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 px-6 py-10">
        <div className="mx-auto max-w-6xl">
          <p className="text-gray-600">AI 매칭 결과를 불러오는 중입니다...</p>
        </div>
      </main>
    );
  }

  // 2. 미인증 사용자 처리
  if (!user) {
    return (
      <main className="min-h-screen bg-gray-50 px-6 py-10">
        <div className="mx-auto max-w-6xl rounded-2xl bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-bold text-gray-900">AI 매칭 결과</h1>
          <p className="mt-4 text-gray-600">
            로그인 후 내 이력서의 AI 매칭 결과를 확인할 수 있습니다.
          </p>
          <Link
            href="/login"
            className="mt-6 inline-block rounded-lg bg-blue-600 px-5 py-3 text-white hover:bg-blue-700 transition"
          >
            로그인하러 가기
          </Link>
        </div>
      </main>
    );
  }

  // 3. 정상 인증 완료 후 메인 뷰
  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-6xl">
        {/* 헤더 */}
        <div className="mb-8">
          <h1 className="mt-3 text-3xl font-bold text-gray-900">AI 매칭 결과</h1>
          <p className="mt-2 text-gray-600">
            내가 업로드한 전체 이력서의 AI 매칭 결과를 한 페이지에서 확인할 수 있습니다.
          </p>
        </div>

        {/* 컨트롤러 (필터 & 정렬) */}
        <section className="mb-6 rounded-2xl bg-white p-5 shadow-sm">
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-700">
                이력서별 필터링
              </label>
              <select
                value={selectedResumeId}
                onChange={(event) => setSelectedResumeId(event.target.value)}
                className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm text-gray-800 outline-none focus:border-blue-500"
              >
                {resumeOptions.map((resume) => (
                  <option key={resume.resumeId} value={resume.resumeId}>
                    {resume.resumeFilename}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-700">
                정렬 기준
              </label>
              <select
                value={sortOption}
                onChange={(event) => setSortOption(event.target.value)}
                className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm text-gray-800 outline-none focus:border-blue-500"
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-end">
              <div className="w-full rounded-lg bg-gray-50 px-4 py-3">
                <p className="text-sm text-gray-500">표시 중인 결과</p>
                <p className="text-xl font-bold text-gray-900">
                  {filteredResults.length}개
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* 결과 리스트 혹은 빈 화면 */}
        {filteredResults.length === 0 ? (
          <section className="rounded-2xl bg-white p-10 text-center shadow-sm">
            <h2 className="text-xl font-bold text-gray-900">
              아직 저장된 AI 매칭 결과가 없습니다.
            </h2>
            <p className="mt-3 text-gray-600">
              이력서를 업로드하고 AI 매칭을 실행하면 결과가 이곳에 표시됩니다.
            </p>
            <Link
              href="/dashboard"
              className="mt-6 inline-block rounded-lg bg-blue-600 px-5 py-3 text-white hover:bg-blue-700 transition"
            >
              AI 매칭하러 가기
            </Link>
          </section>
        ) : (
          <>
            <section className="grid gap-5 md:grid-cols-2">
              {pagedResults.map((result) => (
                <article
                  key={result.id}
                  className="rounded-2xl bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md"
                >
                  <div className="mb-4 flex items-start justify-between gap-4">
                    <div>
                      <h2 className="text-lg font-bold text-gray-900">{result.title}</h2>
                      <p className="mt-1 text-sm text-gray-600">{result.company}</p>
                    </div>
                    <div className="shrink-0 rounded-full bg-blue-50 px-3 py-1 text-sm font-bold text-blue-600">
                      {formatScore(result.score)}%
                    </div>
                  </div>

                  <div className="space-y-2 text-sm text-gray-700">
                    <p>
                      <span className="font-semibold text-gray-900">사용 이력서:</span>{" "}
                      {result.resumeFilename}
                    </p>
                    <p>
                      <span className="font-semibold text-gray-900">지역:</span>{" "}
                      {result.location}
                    </p>
                    <p>
                      <span className="font-semibold text-gray-900">연봉:</span>{" "}
                      {result.salary}
                    </p>
                    <p>
                      <span className="font-semibold text-gray-900">매칭 날짜:</span>{" "}
                      {formatDate(result.updatedAt)}
                    </p>
                  </div>

                  {result.reason && (
                    <p className="mt-4 line-clamp-3 text-sm leading-6 text-gray-600">
                      {result.reason}
                    </p>
                  )}

                  <div className="mt-5 flex gap-2">
                    {result.sourceUrl ? (
                      <a
                        href={result.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
                      >
                        공고 보기
                      </a>
                    ) : (
                      <button
                        type="button"
                        disabled
                        className="rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-500"
                      >
                        공고 링크 없음
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </section>

            {/* 페이지네이션 배치 완료 */}
            {totalPages > 1 && (
              <div className="flex justify-center gap-2 mt-8">
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`px-3 py-1 rounded-lg border ${
                      page === p
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}