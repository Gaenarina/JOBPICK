import { NextResponse } from 'next/server'
import { db } from '@/lib/firebaseAdmin'

function normalizeStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return []
  }

  return [
    ...new Set(
      value
        .filter((item): item is string => typeof item === 'string')
        .map((item) => item.trim())
        .filter(Boolean)
    ),
  ]
}

function normalizeMatchPreferences(value: unknown) {
  const preferences =
    value && typeof value === 'object'
      ? (value as Record<string, unknown>)
      : {}

  return {
    desiredRoles: normalizeStringArray(
      preferences.desiredRoles
    ),
    desiredLocations: normalizeStringArray(
      preferences.desiredLocations
    ),
    employmentTypes: normalizeStringArray(
      preferences.employmentTypes
    ),
    desiredKeywords: normalizeStringArray(
      preferences.desiredKeywords
    ),
  }
}

/**
 * 등록된 이력서의 현재 매칭 조건 조회
 */
export async function GET(
  request: Request,
  { params }: { params: { docId: string } }
) {
  try {
    const { docId } = params

    if (!docId) {
      return NextResponse.json(
        {
          error: 'docId가 필요합니다.',
        },
        {
          status: 400,
        }
      )
    }

    const resumeDoc = await db
      .collection('resumes')
      .doc(docId)
      .get()

    if (!resumeDoc.exists) {
      return NextResponse.json(
        {
          error: '이력서를 찾을 수 없습니다.',
        },
        {
          status: 404,
        }
      )
    }

    const resumeData = resumeDoc.data() || {}

    const matchPreferences =
      normalizeMatchPreferences(
        resumeData.matchPreferences
      )

    return NextResponse.json({
      docId,
      matchPreferences,
    })
  } catch (error) {
    console.error(
      '[이력서 매칭 조건 조회 실패]',
      error
    )

    return NextResponse.json(
      {
        error:
          '이력서 매칭 조건 조회 중 오류가 발생했습니다.',
      },
      {
        status: 500,
      }
    )
  }
}

/**
 * 등록된 이력서의 매칭 조건 수정
 */
export async function PATCH(
  request: Request,
  { params }: { params: { docId: string } }
) {
  try {
    const { docId } = params

    if (!docId) {
      return NextResponse.json(
        {
          error: 'docId가 필요합니다.',
        },
        {
          status: 400,
        }
      )
    }

    const body = await request
      .json()
      .catch(() => ({}))

    const matchPreferences =
      normalizeMatchPreferences(
        body.matchPreferences
      )

    const resumeRef = db
      .collection('resumes')
      .doc(docId)

    const resumeDoc = await resumeRef.get()

    if (!resumeDoc.exists) {
      return NextResponse.json(
        {
          error: '이력서를 찾을 수 없습니다.',
        },
        {
          status: 404,
        }
      )
    }

    await resumeRef.update({
      matchPreferences,
      updatedAt: new Date(),
    })

    return NextResponse.json({
      message:
        '이력서 매칭 조건이 수정되었습니다.',
      docId,
      matchPreferences,
    })
  } catch (error) {
    console.error(
      '[이력서 매칭 조건 수정 실패]',
      error
    )

    return NextResponse.json(
      {
        error:
          '이력서 매칭 조건 수정 중 오류가 발생했습니다.',
      },
      {
        status: 500,
      }
    )
  }
}
