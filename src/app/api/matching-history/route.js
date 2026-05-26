import { NextResponse } from "next/server";
import { db } from "@/lib/firebaseAdmin";

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const userId = searchParams.get("userId");

    if (!userId) {
      return NextResponse.json(
        { error: "userId가 필요합니다." },
        { status: 400 }
      );
    }

    const snapshot = await db
      .collection("matching_results")
      .where("userId", "==", userId)
      .get();

    const matchingDocs = snapshot.docs.map((doc) => ({
      id: doc.id,
      ...doc.data(),
    }));

    // matching_results 안에 있는 resumeId 목록 추출
    const resumeIds = [
      ...new Set(
        matchingDocs
          .map((item) => item.resumeId || item.id)
          .filter(Boolean)
      ),
    ];

    // resumeId 기준으로 resumes 컬렉션에서 이력서 정보 조회
    const resumeInfoMap = {};

    await Promise.all(
      resumeIds.map(async (resumeId) => {
        try {
          const resumeDoc = await db
            .collection("resumes")
            .doc(String(resumeId))
            .get();

          if (resumeDoc.exists) {
            const resumeData = resumeDoc.data();

            resumeInfoMap[resumeId] = {
              resumeId,
              resumeTitle:
                resumeData.filename ||
                resumeData.originalFilename ||
                resumeData.title ||
                resumeData.resumeTitle ||
                resumeData.name ||
                "제목 없는 이력서",
            };
          } else {
            resumeInfoMap[resumeId] = {
              resumeId,
              resumeTitle: "삭제되었거나 찾을 수 없는 이력서",
            };
          }
        } catch (error) {
          console.error("[이력서 정보 조회 실패]", resumeId, error);

          resumeInfoMap[resumeId] = {
            resumeId,
            resumeTitle: "이력서 정보 조회 실패",
          };
        }
      })
    );

    const results = [];

    matchingDocs.forEach((data) => {
      const resumeId = data.resumeId || data.id;

      const resumeTitle =
        resumeInfoMap[resumeId]?.resumeTitle || "제목 없는 이력서";

      const updatedAt = data.updatedAt || "";

      const matches = Array.isArray(data.matches) ? data.matches : [];

      matches.forEach((match, index) => {
        const title =
          match.title ||
          match.jobTitle ||
          match.job_title ||
          match.position ||
          match.recruitTitle ||
          "공고명 없음";

        const company =
          match.company ||
          match.companyName ||
          match.company_name ||
          match.corpName ||
          "회사명 없음";

        const location =
          match.location ||
          match.region ||
          match.address ||
          match.workPlace ||
          "지역 정보 없음";

        const salary =
          match.salary ||
          match.pay ||
          match.wage ||
          match.salaryInfo ||
          "연봉 정보 없음";

        const score = Number(
          match.score ||
            match.matchScore ||
            match.match_score ||
            match.matchRate ||
            match.match_rate ||
            0
        );

        const reason =
          match.reason ||
          match.summary ||
          match.matchReason ||
          match.description ||
          "";

        const sourceUrl =
          match.sourceUrl ||
          match.url ||
          match.link ||
          match.jobUrl ||
          "";

        results.push({
          id: `${data.id}-${index}`,
          resumeId,
          resumeTitle,
          resumeFilename: resumeTitle,
          updatedAt,

          jobId: match.jobId || match.id || match.job_id || "",
          title,
          company,
          location,
          salary,
          score,
          reason,
          sourceUrl,
        });
      });
    });

    return NextResponse.json({
      results,
    });
  } catch (error) {
    console.error("[매칭 결과 조회 실패]", error);

    return NextResponse.json(
      {
        error: "매칭 결과 조회 중 오류가 발생했습니다.",
        detail: error.message,
      },
      { status: 500 }
    );
  }
}