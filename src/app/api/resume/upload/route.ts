import { NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { bucket, db } from "@/lib/firebaseAdmin";

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const file = formData.get("file") as File;
    const userId = formData.get("userId") as string;

    if (!file) {
      return NextResponse.json({ error: "파일 없음" }, { status: 400 });
    }

    const docId = randomUUID();
    const buffer = Buffer.from(await file.arrayBuffer());

    const storagePath = `resumes/${userId || "anonymous"}/${docId}/${file.name}`;
    const fileRef = bucket.file(storagePath);

    await fileRef.save(buffer, {
      metadata: {
        contentType: file.type,
      },
    });

    await db.collection("resumes").doc(docId).set({
      userId: userId || "",
      filename: file.name,
      storagePath,
      status: "INIT",
      createdAt: new Date(),
      updatedAt: new Date(),
    });

    return NextResponse.json({
      message: "업로드 완료",
      docId,
      status: "INIT",
    });
  } catch (error) {
    console.error(error);
    return NextResponse.json({ error: "서버 오류" }, { status: 500 });
  }
}