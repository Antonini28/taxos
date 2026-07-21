/**
 * Typed API client (docs/frontend/05 §3).
 *
 * Errors arrive as RFC 9457 problem+json and are normalised into one ApiError shape, so
 * every screen renders failures the same way — including the trace id that links a user's
 * screenshot to the exact server-side request.
 *
 * Identity is header-based for now, matching the backend's development auth. The OIDC/BFF
 * flow replaces this function without touching a single component.
 */

const BASE = "/backend";

export class ApiError extends Error {
  constructor(
    public status: number,
    public title: string,
    public detail: string | null,
    public traceId: string | null,
    public fieldErrors: { field: string; message: string }[] = [],
  ) {
    super(detail ?? title);
  }
}

const DEV_IDENTITY = {
  tenant: "00000000-0000-0000-0000-0000000000d1",
  user: "daniel@dev",
};

export function currentUser(): string {
  if (typeof window === "undefined") return DEV_IDENTITY.user;
  return localStorage.getItem("taxos-user") ?? DEV_IDENTITY.user;
}

export function setCurrentUser(user: string): void {
  localStorage.setItem("taxos-user", user);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "X-Taxos-Tenant": DEV_IDENTITY.tenant,
      "X-Taxos-User": currentUser(),
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let problem: Record<string, unknown> = {};
    try {
      problem = await response.json();
    } catch {
      /* non-JSON error body — fall through to the status-based message */
    }
    throw new ApiError(
      response.status,
      (problem.title as string) ?? `Request failed (${response.status})`,
      (problem.detail as string) ?? null,
      (problem.trace_id as string) ?? null,
      (problem.errors as { field: string; message: string }[]) ?? [],
    );
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  upload: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", body: form }),
};

// --- Response shapes (mirroring taxos_contracts) ------------------------------

export interface Batch {
  id: string;
  entity_id: string;
  period_key: string;
  source_type: string;
  filename: string;
  status: string;
  row_count: number;
  accepted_count: number;
  quarantined_count: number;
  created_at: string;
}

export interface ValidationReport {
  batch_id: string;
  status: string;
  row_count: number;
  accepted_count: number;
  quarantined_count: number;
  control_total: string;
  rule_breakdown: Record<string, number>;
}

export interface QuarantinedRow {
  row_number: number;
  failures: { rule: string; message: string; field: string | null }[];
  source_payload: Record<string, string>;
}

export interface Box {
  box_id: string;
  label: string;
  value: string;
  derived: boolean;
}

export interface Computation {
  id: string;
  entity_id: string;
  period_key: string;
  tax_type: string;
  pack_ref: string;
  engine_version: string;
  inputs_hash: string;
  result_hash: string;
  unmapped_codes: string[];
  boxes: Box[];
  computed_at: string;
}

export interface LineageEntry {
  row_id: string;
  document_ref: string;
  counterparty: string;
  kind: string;
  amount: string;
  vat_code: string;
  citation_ref: string;
}

export interface Lineage {
  computation_id: string;
  box_id: string;
  box_value: string;
  contribution_total: string;
  entries: LineageEntry[];
}

export interface WorkItem {
  id: string;
  entity_id: string;
  period_key: string;
  item_type: string;
  title: string;
  state: string;
  prepared_by: string;
  computation_id: string | null;
  content_hash: string | null;
  created_at: string;
}

export interface ApprovalEligibility {
  can_approve: boolean;
  reason: string | null;
  content_hash: string | null;
}

export interface Approval {
  id: string;
  approver: string;
  content_hash: string;
  comment: string | null;
  granted_at: string;
  voided: boolean;
  void_reason: string | null;
}

export interface Transition {
  from_state: string;
  to_state: string;
  actor: string;
  comment: string | null;
  occurred_at: string;
}
