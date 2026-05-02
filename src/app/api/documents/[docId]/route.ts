import { NextResponse } from "next/server";
import { admin, db } from "@/lib/firebaseAdmin";

export async function GET(
  req: Request,
  { params }: { params: { docId: string } }
) {
  try {
    const { docId } = params;

    const docRef = db.collection("documents").doc(docId);
    const docSnap = await docRef.get();

    if (!docSnap.exists) {
      return NextResponse.json(
        { success: false, message: "문서를 찾을 수 없습니다." },
        { status: 404 }
      );
    }

    return NextResponse.json({
      success: true,
      data: docSnap.data(),
    });
  } catch (error) {
    console.error(error);

    return NextResponse.json(
      { success: false, message: "문서 조회 실패" },
      { status: 500 }
    );
  }
}

export async function POST(
  req: Request,
  { params }: { params: { docId: string } }
) {
  try {
    const { docId } = params;
    const body = await req.json();

    const { status, result } = body;

    const updateData: any = {
      updatedAt: admin.firestore.FieldValue.serverTimestamp(),
    };

    if (status) updateData.status = status;
    if (result) updateData.result = result;

    await db.collection("documents").doc(docId).update(updateData);

    return NextResponse.json({
      success: true,
      message: "문서 업데이트 성공",
    });
  } catch (error) {
    console.error(error);

    return NextResponse.json(
      { success: false, message: "문서 업데이트 실패" },
      { status: 500 }
    );
  }
}