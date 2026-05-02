import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    message: "백엔드 연결 성공",
  });
}