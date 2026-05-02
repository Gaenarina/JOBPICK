import { NextResponse } from "next/server";
import { db } from "@/lib/firebaseAdmin";

export async function GET() {
  try {
    await db.collection("test").doc("connection").set({
      message: "Firebase 연결 성공",
      createdAt: new Date().toISOString(),
    });

    return NextResponse.json({
      success: true,
      message: "Firestore 저장 성공",
    });
  } catch (error) {
    console.error(error);

    return NextResponse.json(
      { success: false, message: "실패" },
      { status: 500 }
    );
  }
}