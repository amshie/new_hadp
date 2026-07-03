import { NextResponse, type NextRequest } from "next/server";

import { encodePv, PV_COOKIE } from "@/lib/patientView";
import { isUuid } from "@/lib/uuid";

// Cookie-exchange entry for the patient access link. The minted link points here with the
// tenant + token in the query string; this handler moves that credential into an httpOnly
// cookie and 303-redirects to the clean, tokenless /patient-view. The bearer token therefore
// never persists in the patient's address bar or browser history. Referrer-Policy: no-referrer
// keeps the token-bearing entry URL from leaking onward.
export const dynamic = "force-dynamic";

export function GET(request: NextRequest): NextResponse {
  const params = request.nextUrl.searchParams;
  const tenant = params.get("tenant");
  const token = params.get("token");

  // Relative Location: the browser resolves it against the host the patient arrived on,
  // so the host-only hadp_pv cookie set below is always sent on the redirected request.
  // (An absolute URL from request.url can carry a different host — e.g. localhost vs
  // 127.0.0.1 — which would drop the cookie.)
  const res = new NextResponse(null, {
    status: 303,
    headers: { Location: "/patient-view", "Referrer-Policy": "no-referrer" },
  });

  if (tenant && token && isUuid(tenant)) {
    res.cookies.set(PV_COOKIE, encodePv(tenant, token), {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/patient-view",
      maxAge: 60 * 30,
    });
  }
  return res;
}
