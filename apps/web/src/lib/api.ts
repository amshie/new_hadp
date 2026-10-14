import { cookies, headers as requestHeaders } from "next/headers";

import type { components } from "@hadp/api-client";

type Schemas = components["schemas"];
export type Patient = Schemas["PatientOut"];
export type CreatePatientInput = Schemas["CreatePatientRequest"];
export type DuplicateCheck = Schemas["DuplicateCheckOut"];
export type DuplicateCandidate = Schemas["DuplicateCandidateOut"];
export type TimelinePoint = Schemas["TimelinePointOut"];
export type CoreKpi = Schemas["CoreKpiOut"];
export type Me = Schemas["MeResponse"];
export type TenantMembership = Schemas["TenantMembershipOut"];
export type LoginResponse = Schemas["LoginResponse"];
export type ReleaseOut = Schemas["ReleaseOut"];
export type WorklistRow = Schemas["WorklistRowOut"];
export type Coverage = Schemas["CoverageOut"];
export type Throughput = Schemas["ThroughputOut"];
export type Source = Schemas["SourceOut"];
export type ReviewQueueItem = Schemas["ReviewItemOut"];
export type ResolveReviewOut = Schemas["ResolveReviewOut"];
export type InvitationOut = Schemas["InvitationOut"];
export type RedeemOut = Schemas["RedeemOut"];
export type StaffInvitationOut = Schemas["StaffInvitationOut"];
export type StaffInvitationListItem = Schemas["StaffInvitationListItem"];
export type StaffRole = Schemas["StaffInviteCreateIn"]["role"];
export type MemberOut = Schemas["MemberOut"];

// The report view endpoints return an open dict (no response_model); typed locally.
export interface ReportEvidenceItem {
  observation_id: string;
  original_name?: string;
  // The source representation (verbatim); `value`/`unit` are the normalized one, when it exists.
  original_value?: string;
  original_unit?: string | null;
  value?: string | null;
  unit?: string | null;
  observed_at?: string;
  review_status?: string;
  missing?: boolean; // backend surfaces unresolved evidence as { observation_id, missing: true }
  superseded?: boolean; // a published laboratory correction has replaced the cited value
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
  edited?: boolean; // true once the current version carries a human edit
  // A cited value no longer stands: not approvable or releasable; a new draft is the way on.
  cites_replaced_evidence?: boolean;
  // Closed vocabulary: why this version was rejected, and — on a version that reworks a
  // rejected one — why that earlier version was rejected.
  rejection_reason?: string | null;
  reworks_rejection_reason?: string | null;
  statements: ReportStatement[];
}
export interface PatientView {
  report_id: string;
  status: string;
  released_at: string | null;
  synthetic: boolean;
  statements: { id: string; text: string }[];
  // The practice that released the report; its address only if it gave one.
  clinic?: { name: string; address: string | null } | null;
}

// Interpretation matrix (ADR-0003): six domain verdicts (CIS + Actionability as TWO separate
// fields) + three verdict-free tri-state cells each. Typed locally (response_model is structured).
export interface EvidenceObs {
  observation_id: string;
  original_name: string;
  value: string | null;
  unit: string | null;
  reference: string | null;
  observed_at: string;
  review_status: string;
  metric_code: string | null;
  kpi_code?: string | null; // the catalog identity of the cited value (source code = fallback)
  superseded?: boolean; // a published laboratory correction has replaced the cited value
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
  // When the run was recorded (null without a run): values received later were not before
  // its author.
  recorded_at?: string | null;
  domains: DomainVerdictView[];
}

const API_BASE = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
const COOKIE = "hadp_session";
const CSRF_COOKIE = "hadp_csrf";
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    detail: string,
  ) {
    super(detail);
  }
}

// Some limits of the API count per client address: sign-in, the patient view and the two
// invitation redemptions. The API's peer is this server for every browser, so on those calls
// the X-Forwarded-For this server received is passed on as it is. This server asserts nothing
// about it — the list is whatever the client and the proxies in front wrote; the API decides
// which entry it believes, and whether it believes this server at all (TRUSTED_PROXIES and
// TRUSTED_PROXY_HOPS, apps/api/src/hadp_api/security/client_address.py). Only on those calls:
// no other call of the API needs to know where a request came from.
async function forwardedFor(): Promise<Record<string, string>> {
  const chain = (await requestHeaders()).get("x-forwarded-for");
  return chain ? { "x-forwarded-for": chain } : {};
}

type ApiInit = RequestInit & {
  auth?: boolean;
  // Pass the client's address on (see forwardedFor).
  forClient?: boolean;
};

// One authenticated call to the API: forwards the session + CSRF cookies, maps an error
// response to ApiError, and hands back the raw response (a JSON body or a file).
async function send(path: string, init?: ApiInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  if (init?.forClient) {
    for (const [name, value] of Object.entries(await forwardedFor()))
      headers.set(name, value);
  }
  // A multipart body carries its own content type (with the boundary); everything else is JSON.
  if (init?.body && !(init.body instanceof FormData))
    headers.set("content-type", "application/json");
  if (init?.auth !== false) {
    const jar = await cookies();
    const token = jar.get(COOKIE)?.value;
    const csrf = jar.get(CSRF_COOKIE)?.value;
    // Forward BOTH cookies: the API's double-submit check compares the x-csrf-token
    // header against the csrf COOKIE, so the cookie itself must travel too.
    const cookieParts = [
      ...(token ? [`${COOKIE}=${token}`] : []),
      ...(csrf ? [`${CSRF_COOKIE}=${csrf}`] : []),
    ];
    if (cookieParts.length) headers.set("cookie", cookieParts.join("; "));
    if (csrf && UNSAFE_METHODS.has((init?.method ?? "GET").toUpperCase())) {
      headers.set("x-csrf-token", csrf);
    }
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
  return res;
}

async function request<T>(path: string, init?: ApiInit): Promise<T> {
  const res = await send(path, init);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// Which sign-in this deployment offers. The API is the authority: the development sign-in
// exists only outside production (it answers 404 there), and no production identity provider
// is connected yet. The login page shows what exists — never a form that cannot work.
//
// Allow-list, fail-closed: the form (and the "synthetic data" line beside it) is shown only
// when the API names an environment that has the development sign-in. An answer that is
// missing, slow, malformed or names anything else shows no form.
export type SignInMode = "development" | "none" | "unreachable";

const DEV_SIGN_IN_ENVS = new Set(["development", "test"]);

export async function signInMode(): Promise<SignInMode> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return "unreachable";
    const health = (await res.json()) as Partial<Schemas["HealthOut"]>;
    if (health.app_env === "production") return "none";
    return DEV_SIGN_IN_ENVS.has(health.app_env ?? "")
      ? "development"
      : "unreachable";
  } catch {
    return "unreachable";
  }
}

export async function devLogin(email: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/dev-login`, {
    method: "POST",
    headers: { "content-type": "application/json", ...(await forwardedFor()) },
    body: JSON.stringify({ email }),
    cache: "no-store",
  });
  if (!res.ok) throw new ApiError(res.status, "login_failed", "login failed");
  // Persist the session + CSRF cookies issued by the API on this app's domain.
  const setCookies = res.headers.getSetCookie?.() ?? [];
  for (const c of setCookies) {
    const session = c.match(new RegExp(`^${COOKIE}=([^;]+)`));
    if (session?.[1]) {
      (await cookies()).set(COOKIE, session[1], {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
      });
    }
    const csrf = c.match(new RegExp(`^${CSRF_COOKIE}=([^;]+)`));
    if (csrf?.[1]) {
      // Deliberately NOT httpOnly (double-submit token, readable by the client).
      (await cookies()).set(CSRF_COOKIE, csrf[1], {
        httpOnly: false,
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
    // Both, also when the revoke failed: neither value stays on the device after sign-out.
    const jar = await cookies();
    jar.delete(COOKIE);
    jar.delete(CSRF_COOKIE);
  }
}

export const me = () => request<Me>("/api/v1/auth/me");
export const myTenants = () =>
  request<TenantMembership[]>("/api/v1/tenancy/my-tenants");
// One's own sessions, and ending every other one.
export type MySessions = Schemas["SessionsOut"];
export type MySession = Schemas["SessionOut"];
export const mySessions = () => request<MySessions>("/api/v1/auth/sessions");
export const endOtherSessions = () =>
  request<Schemas["EndedOut"]>("/api/v1/auth/sessions/end-others", {
    method: "POST",
  });
export const selectTenant = (tenant_id: string) =>
  request("/api/v1/tenancy/select-tenant", {
    method: "POST",
    body: JSON.stringify({ tenant_id }),
  });

export const listPatients = () => request<Patient[]>("/api/v1/patients");
export const createPatient = (input: CreatePatientInput) =>
  request<Patient>("/api/v1/patients", {
    method: "POST",
    body: JSON.stringify(input),
  });

// POST, not GET: identity details travel in the body so they never land in a query
// string, browser history, or an access log (same rule as the patient-view token).
export const checkDuplicates = (input: Schemas["DuplicateCheckRequest"]) =>
  request<DuplicateCheck>("/api/v1/patients/duplicate-check", {
    method: "POST",
    body: JSON.stringify(input),
  });

export const getPatient = (patientId: string) =>
  request<Patient>(`/api/v1/patients/${patientId}`);

export const worklist = (params?: { status?: string; q?: string }) => {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.q) qs.set("q", params.q);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request<WorklistRow[]>(`/api/v1/worklist${suffix}`);
};

export const coverage = () => request<Coverage>("/api/v1/worklist/coverage");

export const throughput = (days = 30) =>
  request<Throughput>(`/api/v1/worklist/throughput?days=${days}`);

// The ways values came in: one line per laboratory file reader, then everything else.
export const sources = () => request<Source[]>("/api/v1/worklist/sources");

export const timeline = (patientId: string) =>
  request<TimelinePoint[]>(`/api/v1/patients/${patientId}/observations`);

// The catalog's core markers (global reference data: names, domains, classes).
export const coreCatalog = () => request<CoreKpi[]>("/api/v1/kpi-catalog/core");

export const interpretation = (patientId: string) =>
  request<DomainMatrixView>(`/api/v1/patients/${patientId}/interpretation`);

export type RunAuthorIn = Schemas["RunAuthorIn"];
export const authorInterpretation = (patientId: string, body: RunAuthorIn) =>
  request<DomainMatrixView>(
    `/api/v1/patients/${patientId}/interpretation-runs`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );

// Patient data export (GDPR Art. 15/20): the API builds one ZIP per request and stores
// nothing; `exportPatientData` hands the file response through (see the route handler
// patients/[id]/datenauskunft). The list is read from the audit trail.
export type DataExport = Schemas["DataExportOut"];
export const listDataExports = (patientId: string) =>
  request<DataExport[]>(`/api/v1/patients/${patientId}/data-exports`);
export const exportPatientData = (patientId: string) =>
  send(`/api/v1/patients/${patientId}/data-export`, { method: "POST" });

// Consent (append-only events on a closed purpose vocabulary): current state per purpose, and
// the two write operations — each appends a NEW event; nothing is ever edited.
export type ConsentState = Schemas["ConsentStateOut"];
export type ConsentPurposeValue = Schemas["ConsentIn"]["purpose"];
export const listConsents = (patientId: string) =>
  request<ConsentState[]>(`/api/v1/patients/${patientId}/consents`);
export const grantConsent = (
  patientId: string,
  purpose: ConsentPurposeValue,
  channel: string,
) =>
  request<Schemas["ConsentEventOut"]>(
    `/api/v1/patients/${patientId}/consents`,
    { method: "POST", body: JSON.stringify({ purpose, channel }) },
  );
export const withdrawConsent = (
  patientId: string,
  purpose: ConsentPurposeValue,
  channel: string,
) =>
  request<Schemas["ConsentEventOut"]>(
    `/api/v1/patients/${patientId}/consents/withdraw`,
    { method: "POST", body: JSON.stringify({ purpose, channel }) },
  );

// Laboratory files (ingestion tier 1): the original is stored first, then read by a structured
// reader. Metadata and counts only — the web never receives file content back.
export type SourceDocument = Schemas["SourceDocumentOut"];
export type DocumentImportResult = Schemas["DocumentImportOut"];
export const listDocuments = (patientId: string) =>
  request<SourceDocument[]>(`/api/v1/patients/${patientId}/documents`);
export const uploadDocument = (patientId: string, file: Blob, name: string) => {
  const body = new FormData();
  body.append("file", file, name);
  return request<Schemas["DocumentOut"]>(
    `/api/v1/patients/${patientId}/documents`,
    { method: "POST", body },
  );
};
export const importDocument = (patientId: string, documentId: string) =>
  request<DocumentImportResult>(
    `/api/v1/patients/${patientId}/documents/${documentId}/import`,
    { method: "POST" },
  );

export const createInvitation = (patientId: string) =>
  request<InvitationOut>(`/api/v1/patients/${patientId}/invitations`, {
    method: "POST",
  });
export const redeemInvitation = (tenant: string, token: string) =>
  request<RedeemOut>("/api/v1/invitations/redeem", {
    method: "POST",
    body: JSON.stringify({ tenant, token }),
    auth: false,
    forClient: true,
  });

export const reviewQueue = () =>
  request<ReviewQueueItem[]>("/api/v1/review-items");
export const resolveReviewItem = (
  reviewItemId: string,
  decision: "publish" | "reject",
) =>
  request<ResolveReviewOut>(`/api/v1/review-items/${reviewItemId}/resolve`, {
    method: "POST",
    body: JSON.stringify({ decision }),
  });

export const generateReport = (patientId: string) =>
  request<ReportView>(`/api/v1/patients/${patientId}/reports`, {
    method: "POST",
  });
export const getReport = (reportId: string) =>
  request<ReportView>(`/api/v1/reports/${reportId}`);
export type ReportStatementInput = Schemas["StatementIn"];
export const editReport = (
  reportId: string,
  statements: ReportStatementInput[],
) =>
  request<ReportView>(`/api/v1/reports/${reportId}/edit`, {
    method: "POST",
    body: JSON.stringify({ statements }),
  });
export const redraftReport = (reportId: string) =>
  request<ReportView>(`/api/v1/reports/${reportId}/redraft`, {
    method: "POST",
  });
export const approveReport = (reportId: string) =>
  request<ReportView>(`/api/v1/reports/${reportId}/approve`, {
    method: "POST",
  });
export const rejectReport = (
  reportId: string,
  reason: Schemas["RejectReportRequest"]["reason"],
) =>
  request<ReportView>(`/api/v1/reports/${reportId}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
export const releaseReport = (reportId: string) =>
  request<ReleaseOut>(`/api/v1/reports/${reportId}/release`, {
    method: "POST",
  });

// Token travels in the POST body, never the URL: it must not land in a query string,
// browser history, referrer, or an intermediary access log.
export const patientView = (tenant: string, token: string) =>
  request<PatientView>("/api/v1/patient-view", {
    method: "POST",
    body: JSON.stringify({ tenant, token }),
    auth: false,
    forClient: true,
  });

// Staff administration (owner-only server-side): invite a colleague, list pending invites,
// revoke. Redeem is the colleague-side self-onboarding (no staff session).
export const createStaffInvitation = (role: StaffRole, label?: string) =>
  request<StaffInvitationOut>("/api/v1/staff-invitations", {
    method: "POST",
    body: JSON.stringify(label ? { role, label } : { role }),
  });
export const listStaffInvitations = () =>
  request<StaffInvitationListItem[]>("/api/v1/staff-invitations");
export const revokeStaffInvitation = (invitationId: string) =>
  request<{ status: string }>(
    `/api/v1/staff-invitations/${invitationId}/revoke`,
    { method: "POST" },
  );
// The clinic's own audit trail (owner-only server-side): newest first, paged by a cursor.
export type AuditEvent = Schemas["AuditEventOut"];
export type AuditPage = Schemas["AuditPageOut"];
export type AuditCategory = Schemas["AuditCategory"];
export interface AuditFilters {
  category?: AuditCategory;
  target_id?: string;
  actor_user_id?: string;
  since?: string;
  until?: string;
  exclude_reads?: boolean;
  cursor?: string;
  limit?: number;
}
export const listAuditEvents = (filters: AuditFilters) => {
  const qs = new URLSearchParams();
  if (filters.limit) qs.set("limit", String(filters.limit));
  if (filters.category) qs.set("category", filters.category);
  if (filters.target_id) qs.set("target_id", filters.target_id);
  if (filters.actor_user_id) qs.set("actor_user_id", filters.actor_user_id);
  if (filters.since) qs.set("since", filters.since);
  if (filters.until) qs.set("until", filters.until);
  if (filters.exclude_reads) qs.set("exclude_reads", "true");
  if (filters.cursor) qs.set("cursor", filters.cursor);
  return request<AuditPage>(`/api/v1/audit-events?${qs.toString()}`);
};
// One's own latest actions (any staff role), newest first, without reads.
export const ownActivity = (limit = 5) =>
  request<AuditEvent[]>(`/api/v1/audit-events/mine?limit=${limit}`);

// Member administration (owner-only server-side): list the team, change a role, remove.
export const listMembers = () => request<MemberOut[]>("/api/v1/members");
// The clinic's profile (every staff role reads it; the owner changes it).
export type ClinicProfile = Schemas["ClinicProfileOut"];
export const clinicProfile = () =>
  request<ClinicProfile>("/api/v1/clinic-profile");
export const updateClinicProfile = (input: Schemas["ClinicProfileIn"]) =>
  request<ClinicProfile>("/api/v1/clinic-profile", {
    method: "PUT",
    body: JSON.stringify(input),
  });
// Which consent text versions the clinic's records refer to (counts only).
export type ConsentTexts = Schemas["ConsentTextsOut"];
export const consentTexts = () =>
  request<ConsentTexts>("/api/v1/consent-texts");
// The authorization matrix: what each role may do (owner-only server-side).
export type RolePermissions = Schemas["RolePermissionsOut"];
export const rolePermissions = () =>
  request<RolePermissions[]>("/api/v1/roles");
export const changeMemberRole = (membershipId: string, role: StaffRole) =>
  request<MemberOut>(`/api/v1/members/${membershipId}`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
export const removeMember = (membershipId: string) =>
  request<{ status: string }>(`/api/v1/members/${membershipId}`, {
    method: "DELETE",
  });

// Patient erasure requests (GDPR Art. 17) — the two-person gate lifecycle. Server-side
// authorization is the control: create/cancel are owner-only, decide is medical-director-only,
// list is owner + medical director. Execution is a separate (not-yet-wired) capability.
export type DeletionRequestView = Schemas["DeletionRequestOut"];
export type DeletionReason =
  Schemas["DeletionRequestCreateIn"]["reason_category"];

export const createDeletionRequest = (
  patientId: string,
  reason_category: DeletionReason,
) =>
  request<DeletionRequestView>(
    `/api/v1/patients/${patientId}/deletion-requests`,
    { method: "POST", body: JSON.stringify({ reason_category }) },
  );
export const listDeletionRequests = () =>
  request<DeletionRequestView[]>("/api/v1/deletion-requests");
export const approveDeletionRequest = (requestId: string) =>
  request<DeletionRequestView>(
    `/api/v1/deletion-requests/${requestId}/approve`,
    { method: "POST" },
  );
export const rejectDeletionRequest = (requestId: string) =>
  request<DeletionRequestView>(
    `/api/v1/deletion-requests/${requestId}/reject`,
    { method: "POST" },
  );
export const cancelDeletionRequest = (requestId: string) =>
  request<DeletionRequestView>(
    `/api/v1/deletion-requests/${requestId}/cancel`,
    { method: "POST" },
  );
export const executeDeletionRequest = (requestId: string) =>
  request<DeletionRequestView>(
    `/api/v1/deletion-requests/${requestId}/execute`,
    { method: "POST" },
  );

export const redeemStaffInvitation = (input: {
  tenant: string;
  token: string;
  display_name: string;
  email: string;
}) =>
  request<{ status: string; role: StaffRole }>(
    "/api/v1/staff-invitations/redeem",
    {
      method: "POST",
      body: JSON.stringify(input),
      auth: false,
      forClient: true,
    },
  );

// The preparation-time metric (owner only): what the clinic states about its own preparation
// time, and what the platform measures from the report lifecycle. No patient data.
export type PreparationTime = Schemas["PreparationTimeOut"];
export type PreparationStatement = Schemas["PreparationStatementOut"];
export type PreparationMeasured = Schemas["PreparationMeasuredOut"];
export type PreparationStatementInput =
  Schemas["RecordPreparationStatementRequest"];

export const getPreparationTime = () =>
  request<PreparationTime>("/api/v1/metrics/preparation-time");

export const recordPreparationStatement = (input: PreparationStatementInput) =>
  request<PreparationStatement>("/api/v1/metrics/preparation-time/statements", {
    method: "POST",
    body: JSON.stringify(input),
  });
