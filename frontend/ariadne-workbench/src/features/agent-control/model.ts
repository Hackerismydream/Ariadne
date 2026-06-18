import { useEffect, useRef, useState } from "react";

import { addTicketComment } from "../add-ticket-comment/api";
import { assignTicket } from "../assign-ticket/api";
import { runAssignment } from "../run-assignment/api";
import { getAssignmentEvents, openAssignmentEventsSocket } from "../../shared/api/client";
import type { AssignmentEvent } from "../../shared/api/types";
import { idempotencyKey } from "../../shared/lib/idempotency";
import type { WorkbenchDataSource } from "../../data";
import type {
  AriadneTicket,
  AssignmentSummary,
  ProjectResource,
  RuntimeInfo,
} from "../../types";

type ActionState = "idle" | "assigning" | "running";
type CommentState = "idle" | "posting";

type UseTicketAgentControlParams = {
  dataSource: WorkbenchDataSource;
  readOnly: boolean;
  latestAssignment?: AssignmentSummary;
  onRefresh: (preferredTicketRef?: string) => Promise<void>;
  productRuntime?: RuntimeInfo;
  targetProject?: ProjectResource;
  ticket: AriadneTicket;
};

function mergeEvents(current: AssignmentEvent[], incoming: AssignmentEvent[]) {
  const byCursor = new Map<string, AssignmentEvent>();
  for (const event of current) byCursor.set(event.cursor, event);
  for (const event of incoming) byCursor.set(event.cursor, event);
  return [...byCursor.values()].sort((a, b) => a.cursor.localeCompare(b.cursor));
}

export function useTicketAgentControl({
  dataSource,
  latestAssignment,
  onRefresh,
  productRuntime,
  readOnly,
  targetProject,
  ticket,
}: UseTicketAgentControlParams) {
  const [actionState, setActionState] = useState<ActionState>("idle");
  const [actionMessage, setActionMessage] = useState("");
  const [confirmationTokens, setConfirmationTokens] = useState<Record<string, string>>({});
  const [assignmentEvents, setAssignmentEvents] = useState<AssignmentEvent[]>([]);
  const [commentDraft, setCommentDraft] = useState("");
  const [commentState, setCommentState] = useState<CommentState>("idle");
  const socketRef = useRef<WebSocket | null>(null);
  const mutationReady = dataSource === "api" && !readOnly && Boolean(targetProject?.available) && Boolean(productRuntime);

  useEffect(() => {
    return () => socketRef.current?.close();
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
        setConfirmationTokens((current) => ({
          ...current,
          [assigned.assignment!.id!]: assigned.confirmation_token!,
        }));
      }
      setActionMessage("已创建 assignment 和一次性执行确认 token。");
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
      let assignmentId = latestAssignment?.id;
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
          setConfirmationTokens((current) => ({ ...current, [assignmentId!]: assigned.confirmation_token! }));
        }
      }
      if (!assignmentId) throw new Error("缺少 assignment id");
      if (!confirmationToken) throw new Error("缺少执行确认 token；请先重新分配任务再运行");
      await runAssignment(assignmentId, {
        confirmation_token: confirmationToken,
        timeout_seconds: 120,
        idempotency_key: idempotencyKey(`run-${ticket.key}`),
      });
      setActionMessage("已派发运行请求；请保持本地 daemon 运行，进度会从 WebSocket 推送。");
      watchAssignmentEvents(assignmentId);
      await onRefresh(ticket.key);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "运行失败");
    } finally {
      setActionState("idle");
    }
  }

  async function watchAssignmentEvents(assignmentId = latestAssignment?.id) {
    if (!assignmentId) {
      setActionMessage("没有 assignment 可观察。");
      return;
    }
    socketRef.current?.close();
    try {
      const response = await getAssignmentEvents(assignmentId);
      setAssignmentEvents(response.events);
      setActionMessage(`已读取 ${response.events.length} 条 assignment events，并开始实时观察。`);
      const cursor = response.events.at(-1)?.cursor;
      socketRef.current = openAssignmentEventsSocket(
        assignmentId,
        (batch) => {
          if (batch.events.length) {
            setAssignmentEvents((current) => mergeEvents(current, batch.events));
            setActionMessage(`实时事件：${batch.events.at(-1)?.stage ?? "progress"} / ${batch.events.at(-1)?.event_type ?? "updated"}`);
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
    mutationReady,
    postComment,
    runSelectedAssignment,
    setCommentDraft,
    watchAssignmentEvents,
  };
}
