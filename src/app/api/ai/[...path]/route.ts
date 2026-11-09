import { NextRequest, NextResponse } from "next/server";
import { getAiServerBaseUrl } from "@/lib/aiServer";

export const dynamic = "force-dynamic";

type RouteContext = { params: { path: string[] } };
type AllowedMethod = "GET" | "POST";

function resolveAiPath(segments: string[], method: AllowedMethod): string | null {
  if (
    method === "POST" &&
    segments.length === 1 &&
    ["process-resume", "process-one-match"].includes(segments[0])
  ) {
    return `/${segments[0]}`;
  }

  if (
    method === "GET" &&
    segments.length === 2 &&
    segments[0] === "matching-results" &&
    segments[1]
  ) {
    return `/matching-results/${encodeURIComponent(segments[1])}`;
  }

  return null;
}

async function proxyAiRequest(
  request: NextRequest,
  segments: string[],
  method: AllowedMethod
): Promise<NextResponse> {
  const path = resolveAiPath(segments, method);
  if (!path) {
    return NextResponse.json({ error: "지원하지 않는 AI API 요청입니다." }, { status: 404 });
  }

  const baseUrl = getAiServerBaseUrl();
  if (!baseUrl) {
    return NextResponse.json(
      { error: "AI_SERVER_URL이 설정되지 않았거나 유효하지 않습니다." },
      { status: 503 }
    );
  }

  try {
    const upstream = await fetch(`${baseUrl}${path}`, {
      method,
      headers: method === "POST" ? { "Content-Type": "application/json" } : undefined,
      body: method === "POST" ? await request.text() : undefined,
      cache: "no-store",
    });
    const rawResponse = await upstream.text();
    let data: unknown;
    try {
      data = JSON.parse(rawResponse);
    } catch {
      console.error(`AI server returned non-JSON response (${upstream.status}).`);
      return NextResponse.json(
        { error: "AI 서버에서 올바른 응답을 받지 못했습니다." },
        { status: 502 }
      );
    }

    return NextResponse.json(data, {
      status: upstream.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    console.error("AI server proxy request failed:", error);
    return NextResponse.json({ error: "AI 서버에 연결할 수 없습니다." }, { status: 502 });
  }
}

export async function GET(request: NextRequest, { params }: RouteContext) {
  return proxyAiRequest(request, params.path, "GET");
}

export async function POST(request: NextRequest, { params }: RouteContext) {
  return proxyAiRequest(request, params.path, "POST");
}
