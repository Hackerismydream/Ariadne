import type {
  AddTicketCommentRequest,
  ApiWorkbench,
  AssignTicketRequest,
  RunAssignmentRequest,
} from "./types";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as T;
}

export function getWorkbench() {
  return requestJson<ApiWorkbench>("/api/workbench");
}

export function getRuntimeStatus() {
  return requestJson<{ capabilities: ApiWorkbench["runtime_capabilities"] }>("/api/runtime/status");
}

export function assignTicket(ticketIdOrKey: string, payload: AssignTicketRequest) {
  return requestJson(`/api/tickets/${encodeURIComponent(ticketIdOrKey)}/assign`, {
    method: "POST",
    headers: payload.idempotency_key ? { "Idempotency-Key": payload.idempotency_key } : undefined,
    body: JSON.stringify(payload),
  });
}

export function runAssignment(assignmentId: string, payload: RunAssignmentRequest) {
  return requestJson(`/api/assignments/${encodeURIComponent(assignmentId)}/run`, {
    method: "POST",
    headers: payload.idempotency_key ? { "Idempotency-Key": payload.idempotency_key } : undefined,
    body: JSON.stringify(payload),
  });
}

export function addTicketComment(ticketIdOrKey: string, payload: AddTicketCommentRequest) {
  return requestJson(`/api/tickets/${encodeURIComponent(ticketIdOrKey)}/comments`, {
    method: "POST",
    headers: payload.idempotency_key ? { "Idempotency-Key": payload.idempotency_key } : undefined,
    body: JSON.stringify(payload),
  });
}
