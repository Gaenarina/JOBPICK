import { NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { bucket, db } from "@/lib/firebaseAdmin";

function parseMatchPreferences(value: FormDataEntryValue | null) {
  if (!value || typeof value !== "string") {
    return {
      desiredRoles: [],
      desiredLocations: [],
      employmentTypes: [],
      desiredKeywords: [],
    };
  }

  try {
    const parsed = JSON.parse(value);

    return {
      desiredRoles: Array.isArray(parsed.desiredRoles)
        ? parsed.desiredRoles
        : [],
      desiredLocations: Array.isArray(parsed.desiredLocations)
        ? parsed.desiredLocations
        : [],
      employmentTypes: Array.isArray(parsed.employmentTypes)
        ? parsed.employmentTypes
        : [],
      desiredKeywords: Array.isArray(parsed.desiredKeywords)
        ? parsed.desiredKeywords
        : [],
    };
  } catch (error) {
    console.error("matchPreferences 파싱 실패:", error);

    return {
      desiredRoles: [],
      desiredLocations: [],
      employmentTypes: [],
      desiredKeywords: [],
    };
  }
}

export async function POST(req: Request) {
  try {
    const formData = await req.formData();

    const file = formData.get("file") as File;
    const userId = formData.get("userId") as string;

    // 프론트에서 FormData에 JSON 문자열로 보내는 값
    const matchPreferences = parseMatchPreferences(
      formData.get("matchPreferences")
    );

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

      // 사용자 희망 직무/조건
      matchPreferences,

      createdAt: new Date(),
      updatedAt: new Date(),
    });

    return NextResponse.json({
      message: "업로드 완료",
      docId,
      status: "INIT",
      matchPreferences,
    });
  } catch (error) {
    console.error(error);
    return NextResponse.json({ error: "서버 오류" }, { status: 500 });
  }
}
