import { useEffect, useRef, useState } from "react";

import { addTicketComment } from "../add-ticket-comment/api";
import { assignTicket } from "../assign-ticket/api";
import { runAssignment } from "../run-assignment/api";
import {
  getAssignmentEvents,
  openAssignmentEventsSocket,
  runAssignmentNow,
  startDaemon,
  stopDaemon,
} from "../../shared/api/client";
import type { AssignmentEvent } from "../../shared/api/types";
import { idempotencyKey } from "../../shared/lib/idempotency";
import type { WorkbenchDataSource } from "../../data";
import type {
  AriadneTicket,
  AssignmentSummary,
  ProjectResource,
  DaemonStatus,
  RuntimeInfo,
} from "../../types";

type ActionState = "idle" | "assigning" | "running";
type DaemonActionState = "idle" | "starting" | "stopping";
type CommentState = "idle" | "posting";

type UseTicketAgentControlParams = {
  dataSource: WorkbenchDataSource;
  readOnly: boolean;
  latestAssignment?: AssignmentSummary;
  onRefresh: (preferredTicketRef?: string) => Promise<void>;
  productRuntime?: RuntimeInfo;
  daemonStatus?: DaemonStatus;
  targetProject?: ProjectResource;
  ticket: AriadneTicket;
};

function mergeEvents(current: AssignmentEvent[], incoming: AssignmentEvent[]) {
  const byCursor = new Map<string, AssignmentEvent>();
  for (const event of current) byCursor.set(event.cursor, event);
  for (const event of incoming) byCursor.set(event.cursor, event);
  return [...byCursor.values()].sort((a, b) => a.cursor.localeCompare(b.cursor));
}

export function assignmentEventsNeedWorkbenchRefresh(events: AssignmentEvent[]) {
  return events.some((event) =>
    event.source === "artifact"
    || event.event_type === "result"
    || event.event_type === "blocked"
    || event.event_type === "failed"
    || event.event_type === "done",
  );
}

export function useTicketAgentControl({
  dataSource,
  latestAssignment,
  onRefresh,
  productRuntime,
  daemonStatus,
  readOnly,
  targetProject,
  ticket,
}: UseTicketAgentControlParams) {
  const [actionState, setActionState] = useState<ActionState>("idle");
  const [actionMessage, setActionMessage] = useState("");
  const [daemonActionState, setDaemonActionState] = useState<DaemonActionState>("idle");
  const [confirmationTokens, setConfirmationTokens] = useState<Record<string, string>>({});
  const [lastCreatedAssignmentId, setLastCreatedAssignmentId] = useState<string | undefined>();
  const [assignmentEvents, setAssignmentEvents] = useState<AssignmentEvent[]>([]);
  const [commentDraft, setCommentDraft] = useState("");
  const [commentState, setCommentState] = useState<CommentState>("idle");
  const socketRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mutationReady = dataSource === "api" && !readOnly && Boolean(targetProject?.available) && Boolean(productRuntime);

  useEffect(() => {
    return () => {
      socketRef.current?.close();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  async function assignSelectedTicket() {
    if (!targetProject || !productRuntime) return;
    setActionState("assigning");
    setActionMessage("");
    try {
      const assigned = await assignTicket(ticket.key, {
        assignee_id: productRuntime.backend,
        assignee_kind: "agent",
        backend_name: productRuntime.backend as "codex" | "claude-code",
        runtime_profile: "production",
        target_project_id: targetProject.id,
        idempotency_key: idempotencyKey(`assign-${ticket.key}`),
      }) as { assignment?: { id?: string }; confirmation_token?: string };
      if (assigned.assignment?.id && assigned.confirmation_token) {
        setLastCreatedAssignmentId(assigned.assignment.id);
        setConfirmationTokens((current) => ({
          ...current,
          [assigned.assignment!.id!]: assigned.confirmation_token!,
        }));
      }
      setActionMessage("已创建 assignment；本地运行时会自动 claim 并执行。");
      await onRefresh(ticket.key);
      if (assigned.assignment?.id) watchAssignmentEvents(assigned.assignment.id);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "分配失败");
    } finally {
      setActionState("idle");
    }
  }

  async function runSelectedAssignment() {
    if (!targetProject || !productRuntime) return;
    setActionState("running");
    setActionMessage("");
    try {
      let assignmentId = lastCreatedAssignmentId ?? latestAssignment?.id;
      let confirmationToken = assignmentId ? confirmationTokens[assignmentId] : undefined;
      if (!assignmentId) {
        const assigned = await assignTicket(ticket.key, {
          assignee_id: productRuntime.backend,
          assignee_kind: "agent",
          backend_name: productRuntime.backend as "codex" | "claude-code",
          runtime_profile: "production",
          target_project_id: targetProject.id,
          idempotency_key: idempotencyKey(`assign-${ticket.key}`),
        }) as { assignment?: { id?: string }; confirmation_token?: string };
        assignmentId = assigned.assignment?.id;
        if (assignmentId && assigned.confirmation_token) {
          confirmationToken = assigned.confirmation_token;
          setLastCreatedAssignmentId(assignmentId);
          setConfirmationTokens((current) => ({ ...current, [assignmentId!]: assigned.confirmation_token! }));
        }
      }
      if (assignmentId && !confirmationToken) {
        const assigned = await assignTicket(ticket.key, {
          assignee_id: productRuntime.backend,
          assignee_kind: "agent",
          backend_name: productRuntime.backend as "codex" | "claude-code",
          runtime_profile: "production",
          target_project_id: targetProject.id,
          idempotency_key: idempotencyKey(`assign-run-${ticket.key}`),
        }) as { assignment?: { id?: string }; confirmation_token?: string };
        assignmentId = assigned.assignment?.id ?? assignmentId;
        if (assignmentId && assigned.confirmation_token) {
          confirmationToken = assigned.confirmation_token;
          setLastCreatedAssignmentId(assignmentId);
          setConfirmationTokens((current) => ({ ...current, [assignmentId!]: assigned.confirmation_token! }));
        }
      }
      if (!assignmentId) throw new Error("缺少 assignment id");
      if (!confirmationToken) throw new Error("缺少执行确认 token；请先重新分配任务再运行");
      const runKey = idempotencyKey(`run-${ticket.key}`);
      await runAssignment(assignmentId, {
        confirmation_token: confirmationToken,
        timeout_seconds: 600,
        idempotency_key: runKey,
      });
      if (daemonStatus?.backgroundRunning) {
        setActionMessage("当前 assignment 已派发；后台 daemon 会 claim 并执行，结果和阻塞原因会回流到任务证据面板。");
      } else {
        await runAssignmentNow(assignmentId, {
          confirmation_token: confirmationToken,
          timeout_seconds: 600,
          idempotency_key: runKey,
        });
        setActionMessage("本地 daemon 已 claim 该 assignment；结果和阻塞原因会回流到任务证据面板。");
      }
      watchAssignmentEvents(assignmentId);
      await onRefresh(ticket.key);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "运行失败");
    } finally {
      setActionState("idle");
    }
  }

  async function startLocalDaemon() {
    if (dataSource !== "api" || readOnly) return;
    setDaemonActionState("starting");
    setActionMessage("");
    try {
      await startDaemon({
        runtime_id: "workbench-local",
        interval_seconds: 2,
        timeout_seconds: 600,
        external_execution_authorized: true,
        allowed_assignment_id: lastCreatedAssignmentId ?? latestAssignment?.id ?? null,
        target_project_id: targetProject?.id ?? ticket.targetProjectId ?? null,
        allowed_backends: productRuntime?.backend ? [productRuntime.backend] : [],
        scope_mode: "current_assignment",
      });
      setActionMessage("本地运行时已启动，并已授权 Codex/Claude 执行分配给它的任务。");
      await onRefresh(ticket.key);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "启动本地运行时失败");
    } finally {
      setDaemonActionState("idle");
    }
  }

  async function stopLocalDaemon() {
    if (dataSource !== "api" || readOnly) return;
    setDaemonActionState("stopping");
    setActionMessage("");
    try {
      await stopDaemon();
      setActionMessage("本地运行时已停止。");
      await onRefresh(ticket.key);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "停止本地运行时失败");
    } finally {
      setDaemonActionState("idle");
    }
  }

  async function watchAssignmentEvents(assignmentId = latestAssignment?.id) {
    if (!assignmentId) {
      setActionMessage("没有 assignment 可观察。");
      return;
    }
    socketRef.current?.close();
    if (pollRef.current) clearInterval(pollRef.current);
    try {
      const response = await getAssignmentEvents(assignmentId);
      setAssignmentEvents(response.events);
      setActionMessage(`已读取 ${response.events.length} 条 assignment events，并开始实时观察。`);
      if (assignmentEventsNeedWorkbenchRefresh(response.events)) {
        await onRefresh(ticket.key);
      }
      const cursor = response.events.at(-1)?.cursor;
      pollRef.current = setInterval(() => {
        void getAssignmentEvents(assignmentId).then((snapshot) => {
          if (snapshot.events.length) {
            setAssignmentEvents((current) => mergeEvents(current, snapshot.events));
          }
          if (
            assignmentEventsNeedWorkbenchRefresh(snapshot.events)
            || ["done", "blocked", "failed", "cancelled"].includes(snapshot.assignment.status)
          ) {
            void onRefresh(ticket.key);
          }
          if (["done", "blocked", "failed", "cancelled"].includes(snapshot.assignment.status) && pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
        }).catch(() => {
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
        });
      }, 2_000);
      socketRef.current = openAssignmentEventsSocket(
        assignmentId,
        (batch) => {
          if (batch.events.length) {
            setAssignmentEvents((current) => mergeEvents(current, batch.events));
            setActionMessage(`实时事件：${batch.events.at(-1)?.stage ?? "progress"} / ${batch.events.at(-1)?.event_type ?? "updated"}`);
            if (assignmentEventsNeedWorkbenchRefresh(batch.events)) {
              void onRefresh(ticket.key);
            }
            if (["done", "blocked", "failed", "cancelled"].includes(batch.assignment.status) && pollRef.current) {
              clearInterval(pollRef.current);
              pollRef.current = null;
            }
          }
        },
        () => setActionMessage("WebSocket 连接失败；保留最近一次 HTTP 事件快照。"),
        cursor,
      );
      await onRefresh(ticket.key);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "查看事件失败");
    }
  }

  async function postComment() {
    const body = commentDraft.trim();
    if (!body) return;
    setCommentState("posting");
    try {
      await addTicketComment(ticket.key, {
        body,
        assignment_id: latestAssignment?.id,
        idempotency_key: idempotencyKey(`comment-${ticket.key}`),
      });
      setCommentDraft("");
      setActionMessage("评论已写入 ticket timeline。");
      await onRefresh(ticket.key);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "评论失败");
    } finally {
      setCommentState("idle");
    }
  }

  return {
    actionMessage,
    actionState,
    assignmentEvents,
    assignSelectedTicket,
    commentDraft,
    commentState,
    daemonActionState,
    mutationReady,
    postComment,
    runSelectedAssignment,
    setCommentDraft,
    startLocalDaemon,
    stopLocalDaemon,
    watchAssignmentEvents,
  };
}
