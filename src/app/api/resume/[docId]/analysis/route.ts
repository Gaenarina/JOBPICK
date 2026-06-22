import { NextResponse } from "next/server";
import { db } from "@/lib/firebaseAdmin";

export async function GET(
  req: Request,
  { params }: { params: { docId: string } }
) {
  try {
    const { docId } = params;

    if (!docId) {
      return NextResponse.json(
        { error: "docId가 없습니다." },
        { status: 400 }
      );
    }

    const docRef = db.collection("resumes").doc(docId);
    const docSnap = await docRef.get();

    if (!docSnap.exists) {
      return NextResponse.json(
        { error: "이력서를 찾을 수 없습니다." },
        { status: 404 }
      );
    }

    const data = docSnap.data();

    const originalAnalysis = data?.originalAnalysis || data?.resume || null;
    const editedAnalysis = data?.editedAnalysis || null;
    const effectiveAnalysis =
      data?.effectiveAnalysis || editedAnalysis || originalAnalysis;

    return NextResponse.json({
      resumeId: docId,
      docId,
      filename: data?.filename || "",
      originalAnalysis,
      editedAnalysis,
      effectiveAnalysis,
      isAnalysisEdited: data?.isAnalysisEdited || false,
      analysisStatus: data?.analysisStatus || "UNKNOWN",
      analysisVersion: data?.analysisVersion || 1,
      analysisUpdatedAt: data?.analysisUpdatedAt || null,
    });
  } catch (error) {
    console.error("이력서 분석 결과 조회 실패:", error);
    return NextResponse.json(
      { error: "서버 오류" },
      { status: 500 }
    );
  }
}

export async function PATCH(
  req: Request,
  { params }: { params: { docId: string } }
) {
  try {
    const { docId } = params;

    if (!docId) {
      return NextResponse.json(
        { error: "docId가 없습니다." },
        { status: 400 }
      );
    }

    const body = await req.json();
    const editedAnalysis = body.editedAnalysis;

    if (!editedAnalysis || typeof editedAnalysis !== "object") {
      return NextResponse.json(
        { error: "수정된 분석 결과가 없습니다." },
        { status: 400 }
      );
    }

    const docRef = db.collection("resumes").doc(docId);
    const docSnap = await docRef.get();

    if (!docSnap.exists) {
      return NextResponse.json(
        { error: "이력서를 찾을 수 없습니다." },
        { status: 404 }
      );
    }

    const data = docSnap.data();
    const currentVersion = data?.analysisVersion || 1;
    const nextVersion = currentVersion + 1;
    const now = new Date().toISOString();

    await docRef.update({
      editedAnalysis,
      effectiveAnalysis: editedAnalysis,
      isAnalysisEdited: true,
      analysisVersion: nextVersion,
      analysisUpdatedAt: now,
      updatedAt: now,
    });

    return NextResponse.json({
      message: "이력서 분석 결과 수정 완료",
      resumeId: docId,
      docId,
      editedAnalysis,
      effectiveAnalysis: editedAnalysis,
      isAnalysisEdited: true,
      analysisVersion: nextVersion,
    });
  } catch (error) {
    console.error("이력서 분석 결과 수정 실패:", error);
    return NextResponse.json(
      { error: "서버 오류" },
      { status: 500 }
    );
  }
}