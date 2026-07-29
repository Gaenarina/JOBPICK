import { NextResponse } from "next/server";

export async function POST(
  _req: Request,
  { params }: { params: { docId: string } }
) {
  try {
    const { docId } = params;

    if (!docId) {
      return NextResponse.json({ error: "docId is required." }, { status: 400 });
    }

    const aiServerUrl =
      process.env.AI_SERVER_URL || "http://localhost:8000";
    const aiRes = await fetch(
      `${aiServerUrl}/matching-results/${encodeURIComponent(docId)}/ai-summary`,
      { method: "POST", cache: "no-store" }
    );
    const aiData = await aiRes.json().catch(() => ({}));

    if (!aiRes.ok) {
      return NextResponse.json(
        { error: aiData.error || "Gemini summary generation failed." },
        { status: aiRes.status }
      );
    }

    return NextResponse.json(aiData);
  } catch (error) {
    console.error("Gemini summary request failed:", error);
    return NextResponse.json({ error: "Server error." }, { status: 500 });
  }
}
