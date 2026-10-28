import { NextRequest, NextResponse } from "next/server";

export async function POST(
  req: NextRequest,
  { params }: { params: { action: string } }
) {
  const { action } = params;

  if (!["improvements", "simulate"].includes(action)) {
    return NextResponse.json(
      { error: "잘못된 요청입니다." },
      { status: 404 }
    );
  }

  const serverUrl = process.env.AI_SERVER_URL;

  if (!serverUrl) {
    return NextResponse.json(
      { error: "AI_SERVER_URL이 설정되지 않았습니다." },
      { status: 500 }
    );
  }

  try {
    const response = await fetch(
      `${serverUrl.replace(/\/$/, "")}/matching/${action}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: await req.text(),
        cache: "no-store",
      }
    );

    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch (error) {
    console.error("매칭 보완 API 오류:", error);

    return NextResponse.json(
      { error: "AI 서버 연결 실패" },
      { status: 502 }
    );
  }
}