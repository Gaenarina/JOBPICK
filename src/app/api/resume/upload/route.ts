import { NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { admin, bucket, db } from "../../../../lib/firebaseAdmin";

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const file = formData.get("file") as File;

    if (!file) {
      return NextResponse.json({ error: "파일 없음" }, { status: 400 });
    }

    // -----------------------------
    // 1. docId 생성
    // -----------------------------
    const docId = randomUUID();

    const buffer = Buffer.from(await file.arrayBuffer());

    // -----------------------------
    // 2. Storage 저장
    // -----------------------------
    const storagePath = `resumes/anonymous/${docId}/${file.name}`;

    const fileRef = bucket.file(storagePath);

    await fileRef.save(buffer, {
      metadata: {
        contentType: file.type,
      },
    });

    // -----------------------------
    // 3. Firestore 문서 생성
    // -----------------------------
    await db.collection("resumes").doc(docId).set({
      filename: file.name,
      storagePath,
      status: "INIT",
      createdAt: new Date(),
      updatedAt: new Date(),
    });

    // -----------------------------
    // 4. Python 서버 호출 (🔥 핵심)
    // -----------------------------
    fetch("http://localhost:8000/process-resume", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ docId }),
    }).catch(() => {});

    return NextResponse.json({
      message: "업로드 및 처리 시작 완료",
      docId,
      status: "INIT",
    });

  } catch (error) {
    console.error(error);
    return NextResponse.json({ error: "서버 오류" }, { status: 500 });
  }
}