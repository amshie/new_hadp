import { NextResponse, type NextRequest } from "next/server";

import { ApiError, intakeValueRegion } from "@/lib/api";
import { isUuid } from "@/lib/uuid";

// The page region a proposed value was read from, as the confirmation screen shows it beside
// the value. The API authorizes (intake.read, tenant scope) and records the read; this handler
// only passes the image through to the signed-in browser — an image cannot come back from a
// server action, hence a route. GET, same-site cookie: an <img> of this site carries it.
export const dynamic = "force-dynamic";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ batchId: string; valueId: string }> },
): Promise<NextResponse> {
  const { batchId, valueId } = await params;
  if (!isUuid(batchId) || !isUuid(valueId))
    return NextResponse.json({ code: "not_found" }, { status: 404 });
  try {
    const upstream = await intakeValueRegion(valueId);
    return new NextResponse(upstream.body, {
      status: 200,
      headers: {
        "content-type": "image/png",
        "cache-control": "private, no-store",
      },
    });
  } catch (e) {
    if (e instanceof ApiError) {
      const code = e.message.split(":", 1)[0]?.trim() ?? "";
      return NextResponse.json(
        { code: /^[a-z_]+$/.test(code) ? code : e.code },
        { status: e.status, headers: { "cache-control": "no-store" } },
      );
    }
    return NextResponse.json({ code: "error" }, { status: 502 });
  }
}
