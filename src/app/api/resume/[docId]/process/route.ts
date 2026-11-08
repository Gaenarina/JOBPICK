import { NextResponse } from "next/server";
import { getAiServerBaseUrl } from "@/lib/aiServer";

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

    const aiServerUrl = getAiServerBaseUrl();
    if (!aiServerUrl) {
      return NextResponse.json(
        { error: "AI_SERVER_URL이 설정되지 않았거나 유효하지 않습니다." },
        { status: 503 }
      );
    }

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
        matchPreferences: body.matchPreferences || {},
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
