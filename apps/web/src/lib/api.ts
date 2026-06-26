import { cookies } from "next/headers";

import type { components } from "@hadp/api-client";

type Schemas = components["schemas"];
export type Patient = Schemas["PatientOut"];
export type TimelinePoint = Schemas["TimelinePointOut"];
export type Me = Schemas["MeResponse"];
export type TenantMembership = Schemas["TenantMembershipOut"];
export type LoginResponse = Schemas["LoginResponse"];
export type ReleaseOut = Schemas["ReleaseOut"];

// The report view endpoints return an open dict (no response_model); typed locally.
export interface ReportEvidenceItem {
  observation_id: string;
  original_name?: string;
  value?: string | null;
  unit?: string | null;
  observed_at?: string;
  review_status?: string;
  missing?: boolean; // backend surfaces unresolved evidence as { observation_id, missing: true }
}
export interface ReportStatement {
  id: string;
  text: string;
  evidence: ReportEvidenceItem[];
}
export interface ReportView {
  report_id: string;
  patient_id: string;
  status: string;
  version_no: number;
  narrative_provider: string;
  narrative_version: string;
  statements: ReportStatement[];
}
export interface PatientView {
  report_id: string;
  status: string;
  released_at: string | null;
  synthetic: boolean;
  statements: { id: string; text: string }[];
}

// Interpretation matrix (ADR-0003): six domain verdicts (CIS + Actionability as TWO separate
// fields) + three verdict-free tri-state cells each. Typed locally (response_model is structured).
export interface EvidenceObs {
  original_name: string;
  value: string | null;
  unit: string | null;
  reference: string | null;
  observed_at: string;
  review_status: string;
  metric_code: string | null;
}
export interface TriStateCellView {
  tri_state_axis: string;
  state: string;
  endpoint_adequacy: string;
  evidence_count: number;
  evidence: EvidenceObs[];
  rationale: string | null;
}
export interface DomainVerdictView {
  domain_axis: string;
  cis_status: string;
  actionability_class: string;
  followup_adequacy: string;
  review_status: string;
  rationale: string | null;
  cells: TriStateCellView[];
}
export interface DomainMatrixView {
  run_id: string | null;
  run_number: number | null;
  domains: DomainVerdictView[];
}

const API_BASE = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
const COOKIE = "hadp_session";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    detail: string,
  ) {
    super(detail);
  }
}

async function request<T>(
  path: string,
  init?: RequestInit & { auth?: boolean },
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body) headers.set("content-type", "application/json");
  if (init?.auth !== false) {
    const token = (await cookies()).get(COOKIE)?.value;
    if (token) headers.set("cookie", `${COOKIE}=${token}`);
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    let code = "error";
    let detail = res.statusText;
    try {
      const body = (await res.json()) as {
        error?: { code?: string; detail?: string };
      };
      code = body.error?.code ?? code;
      detail = body.error?.detail ?? detail;
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(res.status, code, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function devLogin(email: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/dev-login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email }),
    cache: "no-store",
  });
  if (!res.ok) throw new ApiError(res.status, "login_failed", "login failed");
  // Persist the session cookie issued by the API on this app's domain.
  const setCookies = res.headers.getSetCookie?.() ?? [];
  for (const c of setCookies) {
    const match = c.match(new RegExp(`${COOKIE}=([^;]+)`));
    if (match?.[1]) {
      (await cookies()).set(COOKIE, match[1], {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
      });
    }
  }
  return (await res.json()) as LoginResponse;
}

export async function logout(): Promise<void> {
  try {
    await request("/api/v1/auth/logout", { method: "POST" });
  } finally {
    (await cookies()).delete(COOKIE);
  }
}

export const me = () => request<Me>("/api/v1/auth/me");
export const myTenants = () =>
  request<TenantMembership[]>("/api/v1/tenancy/my-tenants");
export const selectTenant = (tenant_id: string) =>
  request("/api/v1/tenancy/select-tenant", {
    method: "POST",
    body: JSON.stringify({ tenant_id }),
  });

export const listPatients = () => request<Patient[]>("/api/v1/patients");
export const createPatient = (display_name: string) =>
  request<Patient>("/api/v1/patients", {
    method: "POST",
    body: JSON.stringify({ display_name }),
  });

export const getPatient = (patientId: string) =>
  request<Patient>(`/api/v1/patients/${patientId}`);

export const timeline = (patientId: string) =>
  request<TimelinePoint[]>(`/api/v1/patients/${patientId}/observations`);

export const interpretation = (patientId: string) =>
  request<DomainMatrixView>(`/api/v1/patients/${patientId}/interpretation`);

export const generateReport = (patientId: string) =>
  request<ReportView>(`/api/v1/patients/${patientId}/reports`, {
    method: "POST",
  });
export const getReport = (reportId: string) =>
  request<ReportView>(`/api/v1/reports/${reportId}`);
export const approveReport = (reportId: string) =>
  request<ReportView>(`/api/v1/reports/${reportId}/approve`, {
    method: "POST",
  });
export const releaseReport = (reportId: string) =>
  request<ReleaseOut>(`/api/v1/reports/${reportId}/release`, {
    method: "POST",
  });

export const patientView = (tenant: string, token: string) =>
  request<PatientView>(
    `/api/v1/patient-view?tenant=${encodeURIComponent(tenant)}&token=${encodeURIComponent(token)}`,
    { auth: false },
  );
