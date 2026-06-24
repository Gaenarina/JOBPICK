import { NextResponse } from "next/server";

export async function POST(
  req: Request,
  { params }: { params: { docId: string } }
) {
  try {
    const { docId } = params;

    if (!docId) {
      return NextResponse.json(
        { error: "docId가 없습니다." },
        { status: 400 }
      );
    }

    const body = await req.json().catch(() => ({}));

    const userId = body.userId || "";
    const forceRefresh = body.forceRefresh === true;

    const aiServerUrl =
      process.env.AI_SERVER_URL || "http://localhost:8000";

    const aiRes = await fetch(`${aiServerUrl}/process-resume`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        docId,
        resumeId: docId,
        userId,
        forceRefresh,
      }),
    });

    const aiData = await aiRes.json().catch(() => ({}));

    if (!aiRes.ok) {
      return NextResponse.json(
        {
          error: aiData.error || "AI 서버 처리 실패",
          detail: aiData,
        },
        { status: aiRes.status }
      );
    }

    return NextResponse.json({
      message: "최신 정보로 매칭 완료",
      docId,
      status: "DONE",
      result: aiData,
    });
  } catch (error) {
    console.error("AI 분석/매칭 요청 실패:", error);
    return NextResponse.json(
      { error: "서버 오류" },
      { status: 500 }
    );
  }
}