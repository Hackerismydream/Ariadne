import type {
  AddTicketCommentRequest,
  AssignmentEvent,
  ApiWorkbench,
  AssignTicketRequest,
  RunAssignmentRequest,
} from "./types";
import { AriadneApiError } from "./errors";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    cache: "no-store",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new AriadneApiError(body || response.statusText, response.status, body);
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

export function getAssignmentEvents(assignmentId: string, since?: string) {
  const query = since ? `?since=${encodeURIComponent(since)}` : "";
  return requestJson<{ events: AssignmentEvent[] }>(
    `/api/assignments/${encodeURIComponent(assignmentId)}/events${query}`,
  );
}

export function addTicketComment(ticketIdOrKey: string, payload: AddTicketCommentRequest) {
  return requestJson(`/api/tickets/${encodeURIComponent(ticketIdOrKey)}/comments`, {
    method: "POST",
    headers: payload.idempotency_key ? { "Idempotency-Key": payload.idempotency_key } : undefined,
    body: JSON.stringify(payload),
  });
}
