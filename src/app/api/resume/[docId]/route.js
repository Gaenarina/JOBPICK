import { NextResponse } from "next/server";
import { db } from "@/lib/firebaseAdmin";

export async function GET(req, { params }) {
  try {
    const { docId } = params;

    const doc = await db.collection("resumes").doc(docId).get();

    if (!doc.exists) {
      return NextResponse.json({ error: "문서 없음" }, { status: 404 });
    }

    return NextResponse.json({
      docId,
      ...doc.data(),
    });
  } catch (error) {
    console.error(error);
    return NextResponse.json({ error: "서버 오류" }, { status: 500 });
  }
}


