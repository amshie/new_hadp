import { NextResponse, type NextRequest } from "next/server";

import { ApiError, exportPatientData } from "@/lib/api";
import { isUuid } from "@/lib/uuid";

// Download of a patient's data export (GDPR Art. 15/20). The API authorizes (owner only),
// builds the package, audits it and stores nothing; this handler only passes the file through
// to the signed-in browser. A file cannot come back from a server action, hence a route.
//
// A route handler has none of a server action's built-in origin check, so it makes its own:
// a browser POST always carries Origin, and it must be this site. (The session cookie is
// SameSite=Lax as well, so a cross-site POST would arrive without a session anyway.)
export const dynamic = "force-dynamic";

function sameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  if (origin === null) return true; // not a browser form/fetch; the cookie rule still applies
  // Behind a reverse proxy the public host arrives as X-Forwarded-Host.
  const host =
    request.headers.get("x-forwarded-host")?.split(",")[0]?.trim() ||
    request.headers.get("host");
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await params;
  if (!isUuid(id))
    return NextResponse.json({ code: "not_found" }, { status: 404 });
  if (!sameOrigin(request))
    return NextResponse.json({ code: "cross_origin" }, { status: 403 });
  try {
    const upstream = await exportPatientData(id);
    return new NextResponse(upstream.body, {
      status: 200,
      headers: {
        "content-type": "application/zip",
        "content-disposition":
          upstream.headers.get("content-disposition") ??
          'attachment; filename="datenauskunft.zip"',
        "cache-control": "no-store",
      },
    });
  } catch (e) {
    if (e instanceof ApiError) {
      // The API detail starts with a code and never carries patient data; only the code
      // goes on to the browser.
      const code = e.message.split(":", 1)[0]?.trim() ?? "";
      return NextResponse.json(
        { code: /^[a-z_]+$/.test(code) ? code : e.code },
        { status: e.status, headers: { "cache-control": "no-store" } },
      );
    }
    return NextResponse.json({ code: "error" }, { status: 502 });
  }
}
