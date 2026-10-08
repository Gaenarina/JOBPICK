"use client";

import { useEffect, useState } from "react";

type Candidate = {
  id: string;
  type: string;
  label: string;
  value: string;
  applyMode?: string;
  canApplyToResume?: boolean;
  source?: string;
};

type ImprovementResponse = {
  success: boolean;
  currentResult?: {
    score: number;
    recommendType: string;
  };
  candidates?: Candidate[];
  candidateCount?: number;
  message?: string;
};

type SimulationResponse = {
  success: boolean;
  original?: {
    score: number;
    recommendType: string;
  };
  simulated?: {
    score: number;
    recommendType: string;
  };
  scoreChange?: number;
  notice?: string;
  message?: string;
};

type Props = {
  resumeId: string;
  jobId: string;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function MatchingImprovementPanel({
  resumeId,
  jobId,
}: Props) {
  const [opened, setOpened] = useState(true);
  const [loading, setLoading] = useState(false);

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const [currentScore, setCurrentScore] = useState<number | null>(
    null
  );
  const [currentType, setCurrentType] = useState("");

  const [simulation, setSimulation] =
    useState<SimulationResponse | null>(null);

  const [error, setError] = useState("");

  const loadImprovements = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        `${API_BASE}/matching/improvements`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            resumeId,
            jobId,
          }),
        }
      );

      const data: ImprovementResponse =
        await response.json();

      if (!response.ok || !data.success) {
        throw new Error(
          data.message || "보완 항목 조회에 실패했습니다."
        );
      }

      setCandidates(data.candidates || []);
      setCurrentScore(
        data.currentResult?.score ?? null
      );
      setCurrentType(
        data.currentResult?.recommendType || ""
      );

      setOpened(true);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "오류가 발생했습니다."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadImprovements();
  }, [resumeId, jobId]);

  const toggleCandidate = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id)
        ? prev.filter((item) => item !== id)
        : [...prev, id]
    );

    setSimulation(null);
  };

  const runSimulation = async () => {
    const selectedCandidates = candidates.filter(
      (candidate) =>
        selectedIds.includes(candidate.id)
    );

    if (selectedCandidates.length === 0) {
      setError("보완 항목을 하나 이상 선택해주세요.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        `${API_BASE}/matching/simulate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            resumeId,
            jobId,
            selected: selectedCandidates.map(
              (candidate) => ({
                type: candidate.type,
                value: candidate.value,
              })
            ),
          }),
        }
      );

      const data: SimulationResponse =
        await response.json();

      if (!response.ok || !data.success) {
        throw new Error(
          data.message || "시뮬레이션에 실패했습니다."
        );
      }

      setSimulation(data);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "오류가 발생했습니다."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ marginTop: "16px" }}>
      {loading && (
        <p style={{ marginTop: "10px" }}>
          보완 항목을 확인 중입니다...
        </p>
      )}

      {error && (
        <p style={{ marginTop: "10px" }}>
          {error}
        </p>
      )}

      {opened && !loading && (
        <div style={{ marginTop: "16px" }}>
          <p>
            현재 적합도:{" "}
            <strong>
              {currentScore !== null
                ? `${currentScore}점`
                : "-"}
            </strong>
            {currentType && ` · ${currentType}`}
          </p>

          {candidates.length === 0 ? (
            <p>
              현재 확인된 필수 보완 항목이 없습니다.
            </p>
          ) : (
            <>
              <p>
                보완했다고 가정할 항목을 선택해보세요.
              </p>

              {candidates.map((candidate) => (
                <label
                  key={candidate.id}
                  style={{
                    display: "block",
                    marginBottom: "8px",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(
                      candidate.id
                    )}
                    onChange={() =>
                      toggleCandidate(candidate.id)
                    }
                  />{" "}
                  {candidate.label}
                </label>
              ))}

              <button
                type="button"
                onClick={runSimulation}
                disabled={
                  loading ||
                  selectedIds.length === 0
                }
              >
                예상 결과 확인하기
              </button>
            </>
          )}

          {simulation?.simulated && (
            <div style={{ marginTop: "18px" }}>
              <p>
                기존{" "}
                <strong>
                  {simulation.original?.score}점
                </strong>
                {" → "}
                예상{" "}
                <strong>
                  {simulation.simulated.score}점
                </strong>
              </p>

              <p>
                예상 변화:{" "}
                <strong>
                  {simulation.scoreChange !== undefined &&
                  simulation.scoreChange >= 0
                    ? "+"
                    : ""}
                  {simulation.scoreChange}점
                </strong>
              </p>

              <p>
                {simulation.original?.recommendType}
                {" → "}
                {simulation.simulated.recommendType}
              </p>

              <small>
                {simulation.notice}
              </small>
            </div>
          )}
        </div>
      )}
    </div>
  );
}