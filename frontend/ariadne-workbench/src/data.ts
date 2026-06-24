import { getWorkbench } from "./shared/api/client";
import type { ApiBacklogOperation, ApiBacklogPreview, ApiSourceDocument, ApiWorkbench } from "./shared/api/types";
import type { AriadneTicket, RuntimeInfo, TicketExecutionEvidence, TicketStatus, WorkbenchData } from "./types";

export const emptyWorkbenchData: WorkbenchData = {
  goal: {
    id: "",
    title: "No persisted project loaded",
    northStar: "Start the Ariadne local API to load persisted project data.",
    status: "active",
    knowledgeInputs: [],
    feedbackSignals: [],
    currentState: "No persisted Workbench state is available in the browser.",
    targetState: "Connect to Ariadne's local API and load data from .ariadne.",
  },
  tickets: [],
  sources: [],
  sourceArtifacts: [],
  sourceEvidence: [],
  sourceUnderstandings: [],
  sourceEvents: [],
  projectInputs: [],
  knowledgeCards: [],
  backlogChanges: [],
  traceSteps: [],
  backlogMutationPreview: {
    status: "blocked",
    added: 0,
    updated: 0,
    deferred: 0,
    rejected: 0,
    noOp: 0,
    unsafe: 0,
    lastPreviewAt: "",
  },
  agents: [],
  runtimes: [],
  daemonStatus: {
    runtimeId: "",
    status: "offline",
    backgroundRunning: false,
    externalExecutionAuthorized: false,
    stale: null,
    currentAssignmentId: null,
    currentTicketKey: null,
    currentStage: null,
    heartbeatAt: null,
    lastEventId: null,
    lastError: null,
    openAssignmentCount: 0,
    claimableAssignmentCount: 0,
    runningAssignmentCount: 0,
    blockedAssignmentCount: 0,
    lastMessage: "Ariadne API is not connected.",
    scope: null,
    queuePreview: null,
  },
  assignments: [],
  projectResources: [],
  backendSmokeEvidence: [],
  releaseEvidence: undefined,
  skills: [],
  inbox: [],
  environment: {
    connectionMode: "disconnected",
    executionMode: "read_only",
    readOnly: true,
    ariadneRoot: "",
    ariadneStorePath: "",
    activeTargetProjectId: null,
    activeTargetProject: null,
    productionBackendsAvailable: [],
    selectedBackendRecommendation: null,
    blockers: [{ code: "api_disconnected", message: "Ariadne API is not connected.", severity: "error" }],
  },
  currentVersionDelivery: null,
  issueProjection: null,
  agentWorkflows: [],
  agentActivities: [],
};

export type WorkbenchDataSource = "api" | "disconnected";

export async function loadWorkbenchData(): Promise<{ data: WorkbenchData; source: WorkbenchDataSource; readOnly: boolean }> {
  try {
    const apiData = await getWorkbench();
    return { data: adaptApiWorkbench(apiData), source: "api", readOnly: false };
  } catch (error) {
    console.error("Ariadne Workbench API load failed", error);
    return { data: emptyWorkbenchData, source: "disconnected", readOnly: true };
  }
}

function adaptApiWorkbench(apiData: ApiWorkbench): WorkbenchData {
  const sortedPreviews = [...apiData.backlog_previews].sort((a, b) => a.created_at.localeCompare(b.created_at));
  const latestPreview = sortedPreviews.length ? sortedPreviews[sortedPreviews.length - 1] : undefined;
  const sources = apiData.sources.map(adaptSource);
  const knowledgeCards = apiData.sources.map(adaptKnowledgeCard);
  const backlogChanges = latestPreview ? adaptBacklogPreviewChanges(latestPreview) : [];
  return {
    goal: adaptGoal(apiData),
    tickets: apiData.tickets.map((ticket) => adaptTicket(ticket, apiData)),
    sources,
    knowledgeCards,
    backlogChanges,
    traceSteps: latestPreview ? adaptTraceSteps(latestPreview) : [],
    backlogMutationPreview: adaptBacklogMutationPreview(latestPreview),
    agents: apiData.agents.map((agent) => ({
      name: agent.name,
      description: agent.description || agent.role,
      backend: agent.backend_name ?? agent.agent_runtime,
      status: agent.enabled ? (agent.run_count ? "online" : "idle") : "offline",
      runs: agent.run_count,
      reasoning: `${agent.planner_name} / ${agent.agent_runtime}`,
    })),
    assignments: apiData.assignments.map((assignment) => ({
      id: assignment.id,
      ticketId: assignment.ticket_id,
      ticketKey: assignment.ticket_key,
      agentId: assignment.agent_id,
      agentName: assignment.agent_name,
      backendName: assignment.backend_name,
      status: assignment.status,
      readinessStatus: assignment.readiness_status,
      claimable: assignment.claimable,
      routeDecisionId: assignment.route_decision_id,
      handoffPacketId: assignment.handoff_packet_id,
      handoffHash: assignment.handoff_hash,
      buildContextId: assignment.build_context_id,
      blockedReason: assignment.blocked_reason,
      runtimeScope: assignment.runtime_scope,
      targetProjectId: assignment.target_project_id,
      createdAt: assignment.created_at,
      blocker: assignment.blocker,
      failureReason: assignment.failure_reason,
    })),
    daemonStatus: {
      runtimeId: apiData.daemon_status.runtime_id,
      status: apiData.daemon_status.status,
      backgroundRunning: apiData.daemon_status.background_running,
      externalExecutionAuthorized: apiData.daemon_status.external_execution_authorized,
      stale: apiData.daemon_status.stale,
      currentAssignmentId: apiData.daemon_status.current_assignment_id,
      currentTicketKey: apiData.daemon_status.current_ticket_key,
      currentStage: apiData.daemon_status.current_stage,
      heartbeatAt: apiData.daemon_status.heartbeat_at,
      lastEventId: apiData.daemon_status.last_event_id,
      lastError: apiData.daemon_status.last_error,
      openAssignmentCount: apiData.daemon_status.open_assignment_count,
      claimableAssignmentCount: apiData.daemon_status.claimable_assignment_count,
      runningAssignmentCount: apiData.daemon_status.running_assignment_count,
      blockedAssignmentCount: apiData.daemon_status.blocked_assignment_count,
      lastMessage: apiData.daemon_status.last_message,
      scope: apiData.daemon_status.scope ? {
        mode: apiData.daemon_status.scope.mode,
        targetProjectId: apiData.daemon_status.scope.target_project_id,
        ticketId: apiData.daemon_status.scope.ticket_id,
        assignmentId: apiData.daemon_status.scope.assignment_id,
        allowedBackends: apiData.daemon_status.scope.allowed_backends,
      } : null,
      queuePreview: apiData.daemon_status.queue_preview ? {
        current: apiData.daemon_status.queue_preview.current ? adaptAssignment(apiData.daemon_status.queue_preview.current) : null,
        sameTicketReady: apiData.daemon_status.queue_preview.same_ticket_ready.map(adaptAssignment),
        sameProjectReady: apiData.daemon_status.queue_preview.same_project_ready.map(adaptAssignment),
        outOfScopeReadyCount: apiData.daemon_status.queue_preview.out_of_scope_ready_count,
      } : null,
    },
    runtimes: apiData.runtime_capabilities.map(adaptRuntime),
    projectResources: apiData.target_projects.map((project) => ({
      id: project.id,
      label: project.label,
      resourceType: "local_directory",
      available: project.available,
      disabledReason: project.disabled_reason,
      localPath: project.local_path ?? (typeof project.metadata?.local_path === "string" ? project.metadata.local_path : undefined),
      pathExists: project.path_exists,
      isGitRepo: project.is_git_repo,
      gitBranch: project.git_branch,
      gitDirty: project.git_dirty,
      testCommand: project.test_command ?? (typeof project.metadata?.test_command === "string" ? project.metadata.test_command : undefined),
      issuePrefix: project.issue_prefix ?? (typeof project.metadata?.issue_prefix === "string" ? project.metadata.issue_prefix : undefined),
    })),
    sourceArtifacts: apiData.source_artifacts.map((artifact) => ({
      id: artifact.id,
      sourceDocumentId: artifact.source_document_id,
      artifactType: artifact.artifact_type,
      payloadHash: artifact.payload_hash,
      payloadPath: artifact.payload_path,
      evidenceIds: artifact.evidence_ids,
      createdAt: artifact.created_at,
    })),
    sourceEvidence: apiData.source_evidence.map((evidence) => ({
      id: evidence.id,
      sourceDocumentId: evidence.source_document_id,
      artifactId: evidence.artifact_id,
      locator: evidence.locator,
      quoteOrSummary: evidence.quote_or_summary,
      claim: evidence.claim,
      confidence: evidence.confidence,
      contentHash: evidence.content_hash,
      createdAt: evidence.created_at,
    })),
    sourceUnderstandings: (apiData.source_understandings ?? []).map((item) => ({
      sourceId: item.source_id,
      displayTitle: item.display_title,
      kindLabel: item.kind_label,
      roleLabel: item.role_label,
      analysisLabel: item.analysis_label,
      licenseRiskLabel: item.license_risk_label,
      whatAriadneUnderstood: item.what_ariadne_understood,
      evidenceItems: item.evidence_items.map((evidence) => ({
        locator: evidence.locator,
        summary: evidence.summary,
        claim: evidence.claim,
        confidenceLabel: evidence.confidence_label,
      })),
      generatedOutputs: item.generated_outputs,
      risks: item.risks,
      impactedTicketKeys: item.impacted_ticket_keys,
      nextActions: item.next_actions,
    })),
    sourceEvents: (apiData.source_events ?? []).map((event) => ({
      id: event.id,
      sourceId: event.source_id,
      eventType: event.event_type,
      label: event.label,
      createdAt: event.created_at,
    })),
    projectInputs: (apiData.project_inputs ?? []).map((item) => ({
      source: adaptSource(item.source),
      lifecycle: {
        sourceId: item.lifecycle.source_id,
        status: item.lifecycle.status,
        label: item.lifecycle.label,
        detail: item.lifecycle.detail,
        terminal: item.lifecycle.terminal,
        readyForIssueFactory: item.lifecycle.ready_for_issue_factory,
        blocker: item.lifecycle.blocker,
        updatedAt: item.lifecycle.updated_at,
        nextActions: item.lifecycle.next_actions.map((action) => ({
          id: action.id,
          label: action.label,
          enabled: action.enabled,
          reason: action.reason,
          targetRoute: action.target_route,
          apiAction: action.api_action,
        })),
      },
      understanding: item.understanding ? {
        sourceId: item.understanding.source_id,
        displayTitle: item.understanding.display_title,
        kindLabel: item.understanding.kind_label,
        roleLabel: item.understanding.role_label,
        analysisLabel: item.understanding.analysis_label,
        licenseRiskLabel: item.understanding.license_risk_label,
        whatAriadneUnderstood: item.understanding.what_ariadne_understood,
        evidenceItems: item.understanding.evidence_items.map((evidence) => ({
          locator: evidence.locator,
          summary: evidence.summary,
          claim: evidence.claim,
          confidenceLabel: evidence.confidence_label,
        })),
        generatedOutputs: item.understanding.generated_outputs,
        risks: item.understanding.risks,
        impactedTicketKeys: item.understanding.impacted_ticket_keys,
        nextActions: item.understanding.next_actions,
      } : null,
      artifacts: item.artifacts.map((artifact) => ({
        id: artifact.id,
        kind: artifact.kind,
        label: artifact.label,
        summary: artifact.summary,
        payloadPath: artifact.payload_path,
        payloadHash: artifact.payload_hash,
        evidenceCount: artifact.evidence_count,
        keyFields: artifact.key_fields,
      })),
      evidence: item.evidence.map((evidence) => ({
        locator: evidence.locator,
        summary: evidence.summary,
        claim: evidence.claim,
        confidenceLabel: evidence.confidence_label,
      })),
      impactedTicketKeys: item.impacted_ticket_keys,
    })),
    backendSmokeEvidence: [],
    releaseEvidence: undefined,
    skills: apiData.skills.map((skill) => ({
      name: skill.name,
      description: skill.description,
      usedBy: skill.applies_to_agent_roles,
      updatedAt: skill.updated_at,
    })),
    inbox: apiData.inbox.map((item) => ({
      id: item.id,
      ticketId: item.ticket_id ?? undefined,
      ticketKey: item.ticket_key ?? undefined,
      title: item.title,
      body: item.summary,
      time: item.created_at,
      kind: adaptInboxKind(item.source_type),
      status: adaptInboxStatus(item.status),
      severity: adaptInboxSeverity(item.severity),
      sourceType: item.source_type,
      sourceId: item.source_id,
      failureReason: item.failure_reason,
      recommendedAction: item.recommended_action,
      evidenceRef: item.evidence_ref,
      resolutionNote: item.resolution_note,
      repairTicketId: item.repair_ticket_id ?? undefined,
      repairTicketKey: item.repair_ticket_key ?? undefined,
      active: item.active,
      currentState: item.current_state,
      archiveReason: item.archive_reason,
      supersededByRef: item.superseded_by_ref,
      recoveryClass: item.recovery_class,
      primaryAction: item.primary_action,
      allowedActions: item.allowed_actions,
      linkedAssignmentId: item.linked_assignment_id,
      retryAssignmentId: item.retry_assignment_id,
    })),
    environment: apiData.environment ? {
      connectionMode: apiData.environment.connection_mode,
      executionMode: apiData.environment.execution_mode,
      readOnly: apiData.environment.read_only,
      ariadneRoot: apiData.environment.ariadne_root,
      ariadneStorePath: apiData.environment.ariadne_store_path,
      activeTargetProjectId: apiData.environment.active_target_project_id,
      activeTargetProject: apiData.environment.active_target_project ? {
        id: apiData.environment.active_target_project.id,
        label: apiData.environment.active_target_project.label,
        resourceType: "local_directory",
        available: apiData.environment.active_target_project.available,
        disabledReason: apiData.environment.active_target_project.disabled_reason,
        localPath: apiData.environment.active_target_project.local_path ?? undefined,
        pathExists: apiData.environment.active_target_project.path_exists,
        isGitRepo: apiData.environment.active_target_project.is_git_repo,
        gitBranch: apiData.environment.active_target_project.git_branch,
        gitDirty: apiData.environment.active_target_project.git_dirty,
        testCommand: apiData.environment.active_target_project.test_command ?? undefined,
        issuePrefix: apiData.environment.active_target_project.issue_prefix ?? undefined,
      } : null,
      productionBackendsAvailable: apiData.environment.production_backends_available,
      selectedBackendRecommendation: apiData.environment.selected_backend_recommendation,
      blockers: apiData.environment.blockers.map((blocker) => ({
        code: blocker.code,
        message: blocker.message,
        severity: blocker.severity,
      })),
    } : null,
    currentVersionDelivery: apiData.current_version_delivery ? adaptDelivery(apiData.current_version_delivery) : null,
    issueProjection: apiData.issue_projection ? {
      summary: apiData.issue_projection.summary,
      mainlineTickets: apiData.issue_projection.mainline_tickets.map((item) => ({
        ticketId: item.ticket_id,
        ticketKey: item.ticket_key,
        title: item.title,
        status: item.status,
        priority: item.priority,
        rootTicketKey: item.root_ticket_key,
        repairCount: item.repair_count,
        openRepairCount: item.open_repair_count,
        historyCount: item.history_count,
        childTicketKeys: item.child_ticket_keys,
        latestRepairSummary: item.latest_repair_summary,
      })),
      repairItems: apiData.issue_projection.repair_items,
      historyItems: apiData.issue_projection.history_items,
    } : null,
    agentWorkflows: (apiData.agent_workflows ?? []).map((step) => ({
      id: step.id,
      ticketId: step.ticket_id,
      ticketKey: step.ticket_key,
      sequence: step.sequence,
      agentName: step.agent_name,
      agentRole: step.agent_role,
      stepKind: step.step_kind,
      status: step.status,
      inputRefs: step.input_refs.map(adaptArtifactRef),
      outputRefs: step.output_refs.map(adaptArtifactRef),
      assignmentId: step.assignment_id,
      runId: step.run_id,
      handoffId: step.handoff_id,
      nextAgent: step.next_agent,
      nextAction: step.next_action,
      latestActivity: step.latest_activity ? adaptAgentActivity(step.latest_activity) : null,
      blockedReason: step.blocked_reason,
    })),
    agentActivities: (apiData.agent_activities ?? []).map(adaptAgentActivity),
  };
}

function adaptAssignment(assignment: ApiWorkbench["assignments"][number]) {
  return {
    id: assignment.id,
    ticketId: assignment.ticket_id,
    ticketKey: assignment.ticket_key,
    agentId: assignment.agent_id,
    agentName: assignment.agent_name,
    backendName: assignment.backend_name,
    status: assignment.status,
    readinessStatus: assignment.readiness_status,
    claimable: assignment.claimable,
    routeDecisionId: assignment.route_decision_id,
    handoffPacketId: assignment.handoff_packet_id,
    handoffHash: assignment.handoff_hash,
    buildContextId: assignment.build_context_id,
    blockedReason: assignment.blocked_reason,
    runtimeScope: assignment.runtime_scope,
    targetProjectId: assignment.target_project_id,
    createdAt: assignment.created_at,
    blocker: assignment.blocker,
    failureReason: assignment.failure_reason,
  };
}

function adaptDelivery(delivery: NonNullable<ApiWorkbench["current_version_delivery"]>) {
  return {
    id: delivery.id,
    versionLabel: delivery.version_label,
    status: delivery.status,
    goalId: delivery.goal_id,
    targetProjectId: delivery.target_project_id,
    targetProjectLabel: delivery.target_project_label,
    currentState: delivery.current_state,
    targetState: delivery.target_state,
    summary: delivery.summary,
    generatedAt: delivery.generated_at,
    progressCounts: delivery.progress_counts,
    gates: delivery.gates.map((gate) => ({
      id: gate.id,
      label: gate.label,
      status: gate.status,
      detail: gate.detail,
      refId: gate.ref_id,
    })),
    deliveryItems: delivery.delivery_items.map((item) => ({
      ticketId: item.ticket_id,
      ticketKey: item.ticket_key,
      title: item.title,
      status: item.status,
      priority: item.priority,
      targetProjectId: item.target_project_id,
      assignmentId: item.assignment_id,
      assignmentStatus: item.assignment_status,
      backendName: item.backend_name,
      executionResultId: item.execution_result_id,
      testExitCode: item.test_exit_code,
      reviewVerdict: item.review_verdict,
      evidenceStatus: item.evidence_status,
      terminalVerdict: item.terminal_verdict,
      changedFiles: item.changed_files,
      preflightDirtyFiles: item.preflight_dirty_files,
    })),
    latestRealRun: delivery.latest_real_run ? {
      ticketKey: delivery.latest_real_run.ticket_key,
      assignmentId: delivery.latest_real_run.assignment_id,
      backendName: delivery.latest_real_run.backend_name,
      executionResultId: delivery.latest_real_run.execution_result_id,
      exitCode: delivery.latest_real_run.exit_code,
      testExitCode: delivery.latest_real_run.test_exit_code,
      reviewVerdict: delivery.latest_real_run.review_verdict,
      dryRun: delivery.latest_real_run.dry_run,
      blocked: delivery.latest_real_run.blocked,
      terminalVerdict: delivery.latest_real_run.terminal_verdict,
      changedFiles: delivery.latest_real_run.changed_files,
      preflightDirtyFiles: delivery.latest_real_run.preflight_dirty_files,
      handoffFile: delivery.latest_real_run.handoff_file,
      diffArtifactPath: delivery.latest_real_run.diff_artifact_path,
      executionLogArtifactPath: delivery.latest_real_run.execution_log_artifact_path,
      memoryPath: delivery.latest_real_run.memory_path,
      nextTicketsPath: delivery.latest_real_run.next_tickets_path,
    } : null,
    blockers: delivery.blockers,
    nextActions: delivery.next_actions,
    evidenceRefs: delivery.evidence_refs,
  };
}

function adaptArtifactRef(ref: NonNullable<ApiWorkbench["agent_workflows"]>[number]["output_refs"][number]) {
  return {
    id: ref.id,
    artifactType: ref.artifact_type,
    path: ref.path,
    summary: ref.summary,
    createdAt: ref.created_at,
    metadata: ref.metadata,
  };
}

function adaptAgentActivity(activity: NonNullable<ApiWorkbench["agent_activities"]>[number]) {
  return {
    id: activity.id,
    ticketId: activity.ticket_id,
    ticketKey: activity.ticket_key,
    assignmentId: activity.assignment_id,
    runId: activity.run_id,
    agentName: activity.agent_name,
    stage: activity.stage,
    eventType: activity.event_type,
    summary: activity.summary,
    timestamp: activity.timestamp,
    refId: activity.ref_id,
  };
}

function adaptTicket(ticket: ApiWorkbench["tickets"][number], apiData: ApiWorkbench): AriadneTicket {
  const assignment = apiData.assignments.find((item) => item.id === ticket.latest_assignment_id)
    ?? apiData.assignments.find((item) => item.ticket_id === ticket.id);
  const progress = apiData.assignments
    .filter((item) => item.ticket_id === ticket.id)
    .map((item) => ({
      time: item.created_at ?? "",
      actor: item.agent_name,
      kind: item.status,
      body: item.blocker ? `${item.status}: ${item.blocker}` : `Assignment ${item.status} via ${item.backend_name ?? "runtime"}`,
    }));
  const evidence = ticket.evidence ? adaptTicketEvidence(ticket.evidence) : undefined;
  return {
    id: ticket.id,
    key: ticket.key,
    title: ticket.title,
    latestAssignmentId: ticket.latest_assignment_id,
    targetProjectId: ticket.target_project_id,
    summary: ticket.summary ?? `由 Ariadne 管理的 ${ticket.source_type} 来源任务。`,
    status: adaptTicketStatus(ticket.status),
    priority: ticket.priority === "high" || ticket.priority === "low" ? ticket.priority : "medium",
    owner: assignment?.agent_name ?? ticket.assigned_agent_id ?? "构建负责人",
    source: ticket.source_ref ?? ticket.source_type,
    decision: "code_task",
    reviewVerdict: ticket.latest_review_verdict === "pass"
      ? "pass"
      : ticket.latest_review_verdict === "needs_fix"
        ? "needs_fix"
        : ticket.status === "blocked"
          ? "blocked"
          : "pending",
    progress,
    changedFiles: evidence?.changedFiles?.length ? evidence.changedFiles : ticket.affected_modules ?? [],
    memoryPath: evidence?.memoryPath ?? undefined,
    nextTicketsPath: evidence?.nextTicketsPath ?? undefined,
    executionEvidence: evidence,
    acceptance: ticket.acceptance_criteria?.length
      ? ticket.acceptance_criteria
      : ["任务可以分配给生产运行时。", "运行进度在 Ariadne 中可见。"],
  };
}

function adaptTicketEvidence(evidence: NonNullable<ApiWorkbench["tickets"][number]["evidence"]>): TicketExecutionEvidence {
  return {
    assignmentId: evidence.assignment_id,
    assignmentStatus: evidence.assignment_status,
    assignmentBlocker: evidence.assignment_blocker,
    assignmentFailureReason: evidence.assignment_failure_reason,
    executionResultId: evidence.execution_result_id,
    backendName: evidence.backend_name,
    dryRun: evidence.dry_run,
    blocked: evidence.blocked,
    blockReason: evidence.block_reason,
    failureReason: evidence.failure_reason,
    command: evidence.command,
    exitCode: evidence.exit_code,
    stdoutExcerpt: evidence.stdout_excerpt,
    stderrExcerpt: evidence.stderr_excerpt,
    changedFiles: evidence.changed_files,
    diffArtifactPath: evidence.diff_artifact_path,
    executionLogArtifactPath: evidence.execution_log_artifact_path,
    handoffFile: evidence.handoff_file,
    testCommand: evidence.test_command,
    testExitCode: evidence.test_exit_code,
    testStdoutExcerpt: evidence.test_stdout_excerpt,
    testStderrExcerpt: evidence.test_stderr_excerpt,
    reviewReportId: evidence.review_report_id,
    reviewVerdict: evidence.review_verdict,
    memoryPath: evidence.memory_path,
    feishuPlanPath: evidence.feishu_plan_path,
    nextTicketsPath: evidence.next_tickets_path,
    warnings: evidence.warnings,
    currentState: evidence.current_state,
    currentAssignmentId: evidence.current_assignment_id,
    currentRunId: evidence.current_run_id,
    currentExecutionResultId: evidence.current_execution_result_id,
    currentReviewReportId: evidence.current_review_report_id,
    historicalBlockerCount: evidence.historical_blocker_count,
    activeBlockerCount: evidence.active_blocker_count,
    supersededInboxItemIds: evidence.superseded_inbox_item_ids,
  };
}

function adaptTicketStatus(status: string): TicketStatus {
  if (status === "ready_for_execution" || status === "waiting_approval") return "ready";
  if (status === "coding") return "running";
  if (status === "done") return "done";
  if (status === "reviewing") return "reviewing";
  if (status === "blocked" || status === "failed" || status === "cancelled") return "blocked";
  if (status === "planning" || status === "analyzing") return "planning";
  return "inbox";
}

function adaptRuntime(runtime: ApiWorkbench["runtime_capabilities"][number]): RuntimeInfo {
  return {
    machine: "local-mac",
    backend: runtime.backend_name,
    status: runtime.available ? "online" : "offline",
    version: runtime.display_name || (runtime.command_template_set ? "已配置命令模板" : "默认命令模板"),
    cost7d: "local",
    externalExecutionEnabled: runtime.external_execution_enabled,
    commandTemplateSet: runtime.command_template_set,
    confirmExecutionRequired: runtime.confirm_execution_required,
    supportsExternalExecution: true,
    canAssign: runtime.can_assign,
    canRun: runtime.can_run,
    fallbackOnly: runtime.fallback_only,
    disabledReasons: runtime.disabled_reasons,
  };
}

function adaptGoal(apiData: ApiWorkbench): WorkbenchData["goal"] {
  const sortedGoals = [...apiData.goals].sort((a, b) => a.created_at.localeCompare(b.created_at));
  const goal = sortedGoals.length ? sortedGoals[sortedGoals.length - 1] : undefined;
  if (!goal) {
    return {
      id: "GOAL-NOT-CREATED",
      title: "还没有创建产品目标",
      northStar: "从网页创建目标、添加外部知识，再生成 issue。",
      targetProjectId: null,
      status: "active",
      knowledgeInputs: [],
      feedbackSignals: [],
      currentState: "Workbench 已连接本地 API，但还没有目标。",
      targetState: "创建目标后由 Issue Factory 生成可执行任务。",
    };
  }
  return {
    id: goal.id,
    title: goal.title,
    northStar: goal.north_star,
    targetProjectId: goal.target_project_id,
    status: goal.status,
    knowledgeInputs: goal.knowledge_inputs,
    feedbackSignals: goal.feedback_signals,
    currentState: goal.current_state || "已在 Workbench 创建目标。",
    targetState: goal.target_state || "生成 issue 并通过 Agent Runtime 推进版本。",
  };
}

function adaptSource(source: ApiSourceDocument): WorkbenchData["sources"][number] {
  return {
    id: source.id,
    sourceType: adaptSourceType(source.source_type),
    sourceRole: source.source_role,
    title: source.title,
    status: adaptSourceStatus(source.status, source.analysis_status),
    analysisStatus: source.analysis_status,
    ingestedAt: source.created_at,
    pathOrUrl: source.path_or_url,
    linkedTicketCount: source.linked_ticket_count,
    artifactIds: source.artifact_ids,
    licenseRisk: source.license_risk,
  };
}

function adaptSourceStatus(status: string, analysisStatus: string): WorkbenchData["sources"][number]["status"] {
  if (status === "linked" || status === "applied" || status === "archived" || status === "failed") return status;
  if (analysisStatus === "analyzed") return "analyzed";
  if (analysisStatus === "blocked") return "blocked";
  if (analysisStatus === "pending") return "pending";
  return "new";
}

function adaptKnowledgeCard(source: ApiSourceDocument): WorkbenchData["knowledgeCards"][number] {
  return {
    id: `kc-${source.id}`,
    sourceId: source.id,
    title: source.title,
    sourceSummary: source.summary,
    evidence: source.evidence_snippets.length ? source.evidence_snippets : [source.summary],
    projectRelevance: "由 Workbench 来源输入生成，等待 Issue Factory 关联到任务。",
    buildDecision: "code_task",
    affectedModules: [],
    risks: [],
    confidence: 0.7,
    primary: true,
  };
}

function adaptBacklogPreviewChanges(preview: ApiBacklogPreview): WorkbenchData["backlogChanges"] {
  return preview.operations.map((operation) => adaptBacklogOperation(preview, operation));
}

function adaptBacklogOperation(preview: ApiBacklogPreview, operation: ApiBacklogOperation): WorkbenchData["backlogChanges"][number] {
  const kindByIntent: Record<string, WorkbenchData["backlogChanges"][number]["kind"]> = {
    add: "added",
    update: "updated",
    defer: "deferred",
    discard: "rejected",
    supersede: "superseded",
    no_op: "no_op",
  };
  return {
    id: operation.id,
    knowledgeCardId: `kc-${preview.evidence_refs[1] ?? preview.evidence_refs[0] ?? preview.trigger_ref}`,
    kind: operation.change_intent
      ? kindByIntent[operation.change_intent] ?? "no_op"
      : operation.operation_type === "update_ticket"
      ? "updated"
      : operation.operation_type === "defer_ticket"
        ? "deferred"
        : operation.operation_type === "supersede_ticket"
          ? "superseded"
          : operation.operation_type === "no_op"
            ? "no_op"
            : "added",
    ticketKey: operation.ticket_key ?? "NEW",
    title: operation.title ?? "未命名任务",
    reason: operation.reason,
    priority: operation.priority === "high" ? "P1" : operation.priority === "low" ? "P3" : "P2",
    suggestedOwnerAgent: operation.owner_agent ?? "Build Lead",
    buildDecision: operation.build_decision === "architecture_change" ? "architecture_change" : "code_task",
    previewId: preview.id,
    previewStatus: preview.applied_update_id ? "applied" : preview.conflict_count ? "blocked" : "preview_only",
    triggerType: preview.trigger_type,
    operationType: operation.operation_type,
    appliedUpdateId: preview.applied_update_id,
    conflictCount: preview.conflict_count,
    evidenceRefs: operation.evidence_refs,
    affectedModules: operation.affected_modules,
    acceptanceCriteria: operation.acceptance_criteria,
    sourceArtifactIds: operation.source_artifact_ids,
    buildContextId: operation.build_context_id,
    targetProjectId: operation.target_project_id,
    goalReason: operation.goal_reason,
    changeIntent: operation.change_intent,
    targetVersionLabel: operation.target_version_label,
    existingTicketKey: operation.existing_ticket_key,
    beforeSnapshot: operation.before_snapshot,
    afterSummary: operation.after_summary,
    confidence: operation.confidence,
    decisionReason: operation.decision_reason,
    included: operation.included,
  };
}

function adaptTraceSteps(preview: ApiBacklogPreview): WorkbenchData["traceSteps"] {
  return preview.operations.flatMap((operation) => {
    const knowledgeCardId = `kc-${preview.evidence_refs[1] ?? preview.evidence_refs[0] ?? preview.trigger_ref}`;
    return [
      {
        id: `${operation.id}-source`,
        knowledgeCardId,
        backlogChangeId: operation.id,
        label: "Source" as const,
        summary: `来源证据：${preview.evidence_refs.join(", ") || preview.trigger_ref}`,
        artifactPath: ".ariadne/sources/",
        timestamp: preview.created_at,
      },
      {
        id: `${operation.id}-ticket`,
        knowledgeCardId,
        backlogChangeId: operation.id,
        label: "Ticket Delta" as const,
        summary: operation.reason,
        artifactPath: `.ariadne/backlog/previews/${preview.id}.json`,
        timestamp: preview.created_at,
      },
    ];
  });
}

function adaptBacklogMutationPreview(preview?: ApiBacklogPreview): WorkbenchData["backlogMutationPreview"] {
  if (!preview) {
    return {
      status: "preview_only",
      added: 0,
      updated: 0,
      deferred: 0,
      rejected: 0,
      noOp: 0,
      unsafe: 0,
      lastPreviewAt: "未生成",
    };
  }
  return {
    status: preview.applied_update_id ? "applied" : preview.conflict_count ? "blocked" : "preview_only",
    added: preview.operations.filter((operation) => operation.operation_type === "add_ticket").length,
    updated: preview.operations.filter((operation) => operation.operation_type === "update_ticket").length,
    deferred: preview.operations.filter((operation) => operation.operation_type === "defer_ticket").length,
    rejected: preview.operations.filter((operation) => operation.operation_type === "supersede_ticket").length,
    noOp: preview.operations.filter((operation) => operation.operation_type === "no_op").length,
    unsafe: preview.conflict_count,
    lastPreviewAt: preview.created_at,
    previewId: preview.id,
    triggerType: preview.trigger_type,
    appliedUpdateId: preview.applied_update_id,
  };
}

function adaptSourceType(sourceType: string): WorkbenchData["sources"][number]["sourceType"] {
  if (sourceType === "github_repo") return "github_repo";
  if (sourceType === "note") return "manual_note";
  if (sourceType === "review") return "review_feedback";
  if (sourceType === "paper" || sourceType === "blog") return sourceType;
  return "manual_note";
}

function adaptInboxKind(sourceType: string): WorkbenchData["inbox"][number]["kind"] {
  if (sourceType === "assignment" || sourceType === "execution") return "blocker";
  if (sourceType === "memory") return "memory";
  if (sourceType === "review") return "review";
  return "goal";
}

function adaptInboxStatus(status: string): WorkbenchData["inbox"][number]["status"] {
  if (status === "acknowledged" || status === "resolved" || status === "snoozed") return status;
  return "open";
}

function adaptInboxSeverity(severity: string): WorkbenchData["inbox"][number]["severity"] {
  if (severity === "low" || severity === "high" || severity === "critical") return severity;
  return "medium";
}
