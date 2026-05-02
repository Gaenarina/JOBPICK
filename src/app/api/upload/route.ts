import { NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { admin, bucket, db } from "@/lib/firebaseAdmin";

export async function POST(req: Request) {
  try {
    const formData = await req.formData();

    const file = formData.get("file") as File | null;
    const userId = (formData.get("userId") as string) || "anonymous";

    if (!file) {
      return NextResponse.json(
        { success: false, message: "파일이 없습니다." },
        { status: 400 }
      );
    }

    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    const docId = randomUUID();
    const fileName = file.name || "upload.bin";
    const contentType = file.type || "application/octet-stream";

    const storagePath = `original/${userId}/${docId}/${fileName}`;
    const storageFile = bucket.file(storagePath);

    await storageFile.save(buffer, {
      metadata: {
        contentType,
      },
    });

    await db.collection("documents").doc(docId).set({
      docId,
      userId,
      filename: fileName,
      contentType,
      storagePath,
      status: "INIT",
      createdAt: admin.firestore.FieldValue.serverTimestamp(),
      updatedAt: admin.firestore.FieldValue.serverTimestamp(),
    });

    return NextResponse.json({
      success: true,
      message: "업로드 성공",
      docId,
      storagePath,
    });
  } catch (error) {
    console.error("Upload error:", error);

    return NextResponse.json(
      { success: false, message: "업로드 실패" },
      { status: 500 }
    );
  }
}