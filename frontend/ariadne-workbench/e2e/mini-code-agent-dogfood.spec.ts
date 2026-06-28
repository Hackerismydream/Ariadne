import { expect, test, type Page, type TestInfo } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

const workbenchUrl = process.env.ARIADNE_WORKBENCH_URL ?? "http://127.0.0.1:8766";
const resultDir = process.env.ARIADNE_DOGFOOD_RESULT_DIR
  ?? path.resolve(process.cwd(), "../../.ariadne/dogfood/browser");
const serverLogPath = process.env.ARIADNE_DOGFOOD_SERVER_LOG ?? "";
const targetPath = process.env.ARIADNE_DOGFOOD_TARGET_PATH
  ?? "/Users/martinlos/code/ariadne-dogfood/mini-code-agent";
const mode = process.env.ARIADNE_DOGFOOD_MODE ?? "blocked-ok";
const runSuffix = process.env.ARIADNE_DOGFOOD_RUN_ID ?? new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
const targetVersion = `v0.1-real-${runSuffix}`;

const sources = [
  "https://minimal-agent.com/",
  "https://github.com/SWE-agent/mini-SWE-agent",
  "https://github.com/LiuMengxuan04/MiniCode",
];

type PreviewOperation = {
  ticket_key?: string | null;
  title?: string | null;
  reason?: string | null;
  metadata?: {
    affected_modules?: string[];
    acceptance_criteria?: string[];
    target_project_path?: string | null;
  } | null;
};

type IssueSnapshot = {
  issue?: Record<string, unknown> & {
    assignments?: AssignmentSnapshot[];
    execution_results?: ExecutionSnapshot[];
    evidence_sections?: EvidenceSectionSnapshot[];
    source_claim_trace?: SourceClaimSnapshot[];
    source_links?: string[];
    review_summary?: string | null;
    next_issue_links?: string[];
  };
};

type AssignmentSnapshot = {
  id?: string;
  status?: string;
  backend_name?: string | null;
  blocker?: string | null;
  blocked_reason?: string | null;
  failure_reason?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  created_at?: string | null;
  agent_id?: string;
  agent_name?: string;
};

type ExecutionSnapshot = {
  id?: string;
  backend_name?: string;
  blocked?: boolean;
  failure_reason?: string | null;
  exit_code?: number | null;
  test_exit_code?: number | null;
  changed_files?: string[];
  diff_artifact_path?: string | null;
  execution_log_artifact_path?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
};

type EvidenceSectionSnapshot = {
  category?: string;
  items?: EvidenceItemSnapshot[];
};

type EvidenceItemSnapshot = {
  category?: string;
  label?: string;
  path_or_url?: string | null;
};

type SourceClaimSnapshot = {
  evidence_id?: string;
  source_document_id?: string;
};

type StructuredClosureState = {
  status: "pending" | "real_closed" | "external_blocker" | "product_blocker";
  reason: string;
  issueSnapshot: IssueSnapshot;
  execution?: ExecutionSnapshot;
  assignment?: AssignmentSnapshot;
};

function slug(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 80) || "step";
}

function gitOutput(args: string[]) {
  try {
    return execFileSync("git", ["-C", targetPath, ...args], { encoding: "utf8" }).trim();
  } catch {
    return "";
  }
}

function selectDogfoodImplementationIssue(operations: PreviewOperation[]) {
  const candidates = operations.filter((operation) => operation.ticket_key);
  const scored = candidates
    .map((operation) => {
      const title = operation.title ?? "";
      const reason = operation.reason ?? "";
      const modules = operation.metadata?.affected_modules ?? [];
      const criteria = operation.metadata?.acceptance_criteria ?? [];
      const haystack = [title, reason, ...modules, ...criteria].join(" ").toLowerCase();
      let score = 0;
      if (modules.some((moduleName) => moduleName.startsWith("mini_code_agent/"))) score += 6;
      if (modules.some((moduleName) => moduleName.startsWith("tests/") || moduleName === "pyproject.toml")) score += 2;
      if (/agent loop|tool execution|trajectory|observation|review checker|safety|cli/.test(haystack)) score += 3;
      if (/external execution|ariadne_enable_external_execution|environment variable|blocked|blocker|ariadne\/|issue factory/.test(haystack)) {
        score -= 10;
      }
      if (modules.length === 0) score -= 3;
      return { operation, score };
    })
    .sort((left, right) => right.score - left.score);
  const selected = scored.find((item) => item.score > 0)?.operation;
  return selected?.ticket_key ?? candidates[0]?.ticket_key ?? "";
}

async function pageState(page: Page) {
  const text = await page.locator("body").innerText({ timeout: 1_500 }).catch((error) => `UNREADABLE_BODY: ${String(error)}`);
  const projectInputEnabled = await page.getByTestId("project-version-target-path").isEnabled({ timeout: 1_000 }).catch(() => false);
  let connection = "unknown";
  if (text.includes("已接入本地 FastAPI 控制平面")) connection = "api";
  if (projectInputEnabled && !text.includes("只读")) connection = "api";
  if (text.includes("使用本地静态快照") || text.includes("显式离线 fixture 模式")) connection = "snapshot_or_fixture";
  if (text.includes("未连接本地 API") || text.includes("只读")) connection = connection === "api" ? "api_with_readonly_text" : "disconnected_or_readonly";
  return { connection, visibleText: text.slice(0, 12_000) };
}

async function recordBlocker(stepName: string, page: Page, testInfo: TestInfo, error: unknown) {
  await mkdir(resultDir, { recursive: true });
  const screenshotPath = testInfo.outputPath(`blocker-${slug(stepName)}.png`);
  await page.screenshot({ fullPage: true, path: screenshotPath }).catch(() => undefined);
  const state = await pageState(page);
  const blocker = {
    schema_version: "ariadne.browser_dogfood_blocker.v1",
    mode,
    step: stepName,
    url: page.url(),
    error: error instanceof Error ? error.message : String(error),
    screenshot_path: screenshotPath,
    server_log_path: serverLogPath,
    workbench_connection: state.connection,
    visible_page_state: state.visibleText,
    recorded_at: new Date().toISOString(),
  };
  await writeFile(path.join(resultDir, "current-blocker.json"), `${JSON.stringify(blocker, null, 2)}\n`);
  await writeFile(testInfo.outputPath("blocker.json"), `${JSON.stringify(blocker, null, 2)}\n`);
}

async function stepOrBlock(testInfo: TestInfo, page: Page, stepName: string, action: () => Promise<void>) {
  try {
    await action();
  } catch (error) {
    await recordBlocker(stepName, page, testInfo, error);
    throw new Error(`DOGFOOD_BLOCKER: ${stepName}: ${error instanceof Error ? error.message : String(error)}`);
  }
}

async function clickFirst(page: Page, name: string | RegExp) {
  await page.getByRole("button", { name }).first().click();
}

async function fetchIssueSnapshot(page: Page, issueKey: string): Promise<IssueSnapshot> {
  const response = await page.request.get(`${workbenchUrl}/api/issues/${encodeURIComponent(issueKey)}`);
  if (!response.ok()) {
    throw new Error(`issue snapshot failed: ${response.status()}`);
  }
  return await response.json() as IssueSnapshot;
}

function latestByTimestamp<T extends { ended_at?: string | null; started_at?: string | null; created_at?: string | null }>(items: T[]) {
  return [...items].sort((left, right) => timestampValue(left) - timestampValue(right)).at(-1);
}

function timestampValue(item: { ended_at?: string | null; started_at?: string | null; created_at?: string | null }) {
  const value = item.ended_at ?? item.started_at ?? item.created_at ?? "";
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function latestExecution(issueSnapshot: IssueSnapshot) {
  return latestByTimestamp(issueSnapshot.issue?.execution_results ?? []);
}

function latestAssignment(issueSnapshot: IssueSnapshot) {
  return latestByTimestamp(issueSnapshot.issue?.assignments ?? []);
}

function evidenceItemPath(issueSnapshot: IssueSnapshot, label: RegExp, category?: string) {
  const sections = issueSnapshot.issue?.evidence_sections ?? [];
  for (const section of sections) {
    for (const item of section.items ?? []) {
      if (category && item.category !== category) continue;
      if (label.test(String(item.label ?? "")) && item.path_or_url) {
        return item.path_or_url;
      }
    }
  }
  return "";
}

function sourceEvidenceRefs(issueSnapshot: IssueSnapshot) {
  const claimRefs = (issueSnapshot.issue?.source_claim_trace ?? [])
    .map((claim) => claim.evidence_id)
    .filter((value): value is string => Boolean(value));
  const linkRefs = (issueSnapshot.issue?.source_links ?? []).filter((value) => value.startsWith("source_evidence_"));
  return [...new Set([...claimRefs, ...linkRefs])];
}

function sourceDocumentIds(issueSnapshot: IssueSnapshot) {
  const claimRefs = (issueSnapshot.issue?.source_claim_trace ?? [])
    .map((claim) => claim.source_document_id)
    .filter((value): value is string => Boolean(value));
  const linkRefs = (issueSnapshot.issue?.source_links ?? []).filter((value) => value.startsWith("source_") && !value.startsWith("source_artifact_") && !value.startsWith("source_evidence_"));
  return [...new Set([...claimRefs, ...linkRefs])];
}

function sourceArtifactIds(issueSnapshot: IssueSnapshot) {
  return [...new Set((issueSnapshot.issue?.source_links ?? []).filter((value) => value.startsWith("source_artifact_")))];
}

async function waitForStructuredClosure(page: Page, issueKey: string): Promise<StructuredClosureState> {
  const deadline = Date.now() + 1_200_000;
  let lastState: StructuredClosureState | undefined;
  let waitMs = 2_000;
  while (Date.now() < deadline) {
    const issueSnapshot = await fetchIssueSnapshot(page, issueKey);
    lastState = classifyStructuredClosure(issueSnapshot);
    if (lastState.status !== "pending") {
      return lastState;
    }
    await page.waitForTimeout(waitMs);
    waitMs = Math.min(waitMs * 1.5, 20_000);
  }
  return lastState ?? {
    status: "product_blocker",
    reason: "issue snapshot never became available",
    issueSnapshot: {},
  };
}

function classifyStructuredClosure(issueSnapshot: IssueSnapshot): StructuredClosureState {
  const execution = latestExecution(issueSnapshot);
  const assignment = latestAssignment(issueSnapshot);
  if (!execution) {
    if (assignment?.status && ["blocked", "failed", "cancelled"].includes(assignment.status)) {
      const reason = assignment.failure_reason ?? assignment.blocked_reason ?? assignment.blocker ?? "assignment terminal before execution";
      return {
        status: isExternalExecutionReason(reason) ? "external_blocker" : "product_blocker",
        reason,
        issueSnapshot,
        assignment,
      };
    }
    return { status: "pending", reason: "waiting for execution result", issueSnapshot, assignment };
  }

  if (execution.blocked) {
    const reason = execution.failure_reason ?? assignment?.failure_reason ?? assignment?.blocked_reason ?? assignment?.blocker ?? "execution blocked";
    return {
      status: isExternalExecutionReason(reason) ? "external_blocker" : "product_blocker",
      reason,
      issueSnapshot,
      execution,
      assignment,
    };
  }
  if (!/^(codex|claude-code|claude)$/i.test(execution.backend_name ?? "")) {
    return { status: "product_blocker", reason: `non-real backend ${execution.backend_name ?? "<missing>"}`, issueSnapshot, execution, assignment };
  }
  if (execution.exit_code !== 0) {
    return { status: "product_blocker", reason: `execution exit_code=${execution.exit_code}`, issueSnapshot, execution, assignment };
  }
  if (!(execution.test_exit_code === 0 || execution.test_exit_code === null)) {
    return { status: "product_blocker", reason: `test_exit_code=${execution.test_exit_code}`, issueSnapshot, execution, assignment };
  }
  if ((execution.changed_files ?? []).length === 0) {
    return { status: "product_blocker", reason: "execution recorded no changed files", issueSnapshot, execution, assignment };
  }
  if (!execution.diff_artifact_path) {
    return { status: "product_blocker", reason: "execution recorded no diff artifact", issueSnapshot, execution, assignment };
  }
  if (!/pass/i.test(issueSnapshot.issue?.review_summary ?? "")) {
    return { status: "pending", reason: "waiting for review pass evidence", issueSnapshot, execution, assignment };
  }
  if (!evidenceItemPath(issueSnapshot, /memory[\s_-]*record/i, "memory")) {
    return { status: "pending", reason: "waiting for memory record evidence", issueSnapshot, execution, assignment };
  }
  if (!evidenceItemPath(issueSnapshot, /next[\s_-]*tickets/i, "next_ticket")) {
    return { status: "pending", reason: "waiting for next tickets evidence", issueSnapshot, execution, assignment };
  }
  if (sourceEvidenceRefs(issueSnapshot).length === 0) {
    return { status: "product_blocker", reason: "selected issue has no source evidence refs", issueSnapshot, execution, assignment };
  }
  if (!assignment?.status) {
    return { status: "pending", reason: "waiting for assignment terminal status", issueSnapshot, execution, assignment };
  }
  if (assignment.status === "queued") {
    return { status: "product_blocker", reason: "assignment requeued after successful execution evidence", issueSnapshot, execution, assignment };
  }
  if (assignment.status !== "done") {
    return { status: "pending", reason: `waiting for assignment done; current status=${assignment.status}`, issueSnapshot, execution, assignment };
  }
  return { status: "real_closed", reason: "structured execution evidence is complete", issueSnapshot, execution, assignment };
}

function isExternalExecutionReason(reason: string) {
  return /external_execution_blocked|command_unavailable|authentication_failed|quota_exceeded|provider_config_invalid|runtime_offline|resource_locked|dirty_base_checkout|invalid_resource|not logged in|login required|quota|rate limit|service tier|permission|git state|ARIADNE_ENABLE_EXTERNAL_EXECUTION|Codex CLI|Claude CLI/i.test(reason);
}

test.describe("Mini Code Agent browser dogfood", () => {
  test("drives the real Workbench product path until closure or first blocker", async ({ page }, testInfo) => {
    test.setTimeout(1_500_000);
    let selectedIssueKey = "";
    let previewId = "";
    let appliedIssueKeys: string[] = [];
    const targetRepoBeforeCommit = gitOutput(["rev-parse", "HEAD"]);
    const targetRepoBeforeStatus = gitOutput(["status", "--short"]);

    await stepOrBlock(testInfo, page, "open real Workbench in API mode", async () => {
      await page.goto(`${workbenchUrl}/?v=browser-dogfood-first#project`, { waitUntil: "domcontentloaded" });
      await expect(page.getByRole("heading", { level: 1, name: "Project Version", exact: true })).toBeVisible({ timeout: 15_000 });
      await expect.poll(async () => (await pageState(page)).connection, {
        message: "Workbench should leave fixture/disconnected mode and become writable API mode",
        timeout: 20_000,
      }).toBe("api");
    });

    await stepOrBlock(testInfo, page, "create and select target project version", async () => {
      const projectForm = page.getByTestId("project-version-form");
      await expect(projectForm).toBeVisible({ timeout: 10_000 });
      await projectForm.getByTestId("project-version-target-mode").selectOption("new");
      await projectForm.getByTestId("project-version-target-path").fill(targetPath);
      await projectForm.getByTestId("project-version-target-label").fill("Mini Code Agent");
      await projectForm.getByTestId("project-version-test-command").fill("python3.11 -m pytest");
      await projectForm.getByTestId("project-version-issue-prefix").fill("MCA");
      await projectForm.getByTestId("project-version-target-version").fill(targetVersion);
      await projectForm.getByTestId("project-version-goal").fill(
        "用户给一个本地项目目标和外部知识，Ariadne 组织 agent team 生成目标项目 issue，并调度 Codex/Claude 把 mini-code-agent 推进到可运行 v0.1。",
      );
      await projectForm.getByTestId("project-version-target-state").fill(
        "mini_code_agent CLI 可以运行 --help，并能执行一次 inspect/summarize 风格的本地任务，Workbench 回流 diff、tests、review、memory 和 next issue。",
      );
      const projectVersionResponse = page.waitForResponse((response) =>
        response.request().method() === "POST"
        && new URL(response.url()).pathname === "/api/project-versions",
        { timeout: 120_000 },
      );
      await expect(projectForm.getByTestId("project-version-create")).toBeEnabled({ timeout: 10_000 });
      await projectForm.getByTestId("project-version-create").click();
      const response = await projectVersionResponse;
      expect(response.ok(), `project version creation failed: ${response.status()}`).toBeTruthy();
      const payload = await response.json() as { project_version?: { id?: string; version_label?: string } };
      expect(payload.project_version?.version_label).toBe(targetVersion);
      await expect(page.locator("body")).toContainText(payload.project_version?.id ?? targetVersion, { timeout: 20_000 });
      await expect(page.locator("body")).toContainText(targetVersion, { timeout: 20_000 });
    });

    await stepOrBlock(testInfo, page, "add three external sources and analyze them", async () => {
      await page.goto(`${workbenchUrl}/?v=browser-dogfood-first#sources`, { waitUntil: "domcontentloaded" });
      await expect(page.getByRole("heading", { level: 1, name: "Sources" })).toBeVisible({ timeout: 15_000 });
      for (const source of sources) {
        const sourcePanel = page.locator(".primary-source-input");
        const urlInput = page.getByLabel("Paste a URL, GitHub repo, or local path");
        const addAndAnalyze = page.getByRole("button", { name: "Add and Analyze" });
        await urlInput.fill("");
        await urlInput.click();
        await page.keyboard.insertText(source);
        await expect(urlInput).toHaveValue(source);
        await expect(addAndAnalyze).toBeEnabled({ timeout: 5_000 });
        const sourceResponse = page.waitForResponse((response) =>
          response.request().method() === "POST"
          && new URL(response.url()).pathname === "/api/sources",
          { timeout: 120_000 },
        );
        await addAndAnalyze.click();
        const response = await sourceResponse;
        expect(response.ok(), `source request failed: ${response.status()} ${source}`).toBeTruthy();
        await expect(sourcePanel.locator(".action-message")).toContainText(/Analyzed source|Existing source opened/, { timeout: 45_000 });
      }
    });

    await stepOrBlock(testInfo, page, "generate target-project issue preview", async () => {
      await page.goto(`${workbenchUrl}/?v=browser-dogfood-first#plan-changes`, { waitUntil: "domcontentloaded" });
      await expect(page.getByRole("heading", { level: 1, name: "Plan Changes" })).toBeVisible({ timeout: 15_000 });
      const planChangesPage = page.locator(".plan-changes-page");
      const previewResponse = page.waitForResponse((response) =>
        response.request().method() === "POST"
        && new URL(response.url()).pathname === "/api/issue-factory/preview",
        { timeout: 180_000 },
      );
      await clickFirst(page, "Generate Issue Delta");
      const response = await previewResponse;
      expect(response.ok(), `issue delta preview failed: ${response.status()}`).toBeTruthy();
      const previewPayload = await response.json() as {
        preview?: { id?: string; operations?: PreviewOperation[] };
      };
      previewId = previewPayload.preview?.id ?? "";
      appliedIssueKeys = (previewPayload.preview?.operations ?? [])
        .map((operation) => operation.ticket_key)
        .filter((key): key is string => Boolean(key));
      selectedIssueKey = selectDogfoodImplementationIssue(previewPayload.preview?.operations ?? []);
      expect(
        selectedIssueKey,
        "Issue Delta preview API should include at least one target-project implementation ticket_key",
      ).not.toBe("");
      await expect(planChangesPage.locator(".action-message")).toContainText(
        /Generated \d+ issue delta items\.|Issue delta generation failed/,
        { timeout: 180_000 },
      );
      await expect(planChangesPage).toContainText(/MCA-\d{3}|No added items|Blocked: unsafe changes/, { timeout: 60_000 });
      const body = await planChangesPage.innerText();
      expect(body).toMatch(/MCA-\d{3}|Mini Code Agent|mini-code-agent/i);
      expect(body).toContain(selectedIssueKey);
    });

    await stepOrBlock(testInfo, page, "apply issue delta", async () => {
      const applyResponse = page.waitForResponse((response) =>
        response.request().method() === "POST"
        && /\/api\/issue-factory\/[^/]+\/apply$/.test(new URL(response.url()).pathname),
        { timeout: 120_000 },
      );
      await clickFirst(page, "Apply Changes");
      const response = await applyResponse;
      expect(response.ok(), `issue delta apply failed: ${response.status()}`).toBeTruthy();
      const issuesPage = page.locator(".phase3-issues-page");
      await expect(issuesPage).toContainText(selectedIssueKey, { timeout: 45_000 });
      await expect(issuesPage).toContainText(/Issues|current version mainline/, { timeout: 45_000 });
      const body = await issuesPage.innerText();
      expect(body).not.toMatch(/stale_preview|Apply failed|Internal Server Error|Traceback|500/);
    });

    await stepOrBlock(testInfo, page, "open selected target issue", async () => {
      await page.goto(`${workbenchUrl}/?v=browser-dogfood-first#issues/${selectedIssueKey}`, { waitUntil: "domcontentloaded" });
      await expect(page.locator("body")).toContainText(selectedIssueKey, { timeout: 20_000 });
      const body = await page.locator("body").innerText();
      expect(body).toMatch(/Mini Code Agent|mini-code-agent|MCA-\d{3}/i);
    });

    await stepOrBlock(testInfo, page, "assign current issue to Codex or Claude", async () => {
      const issueDetail = page.getByTestId("issue-detail");
      await clickFirst(page, /^Assign$/);
      await expect(issueDetail).toContainText(/Assigned .* to|Ready to claim/, { timeout: 30_000 });
    });

    await stepOrBlock(testInfo, page, "authorize and start scoped daemon for current assignment", async () => {
      await page.goto(`${workbenchUrl}/?v=browser-dogfood-first#runs`, { waitUntil: "domcontentloaded" });
      await expect(page.getByRole("heading", { level: 1, name: "Runs" })).toBeVisible({ timeout: 15_000 });
      const runsPage = page.locator(".runs-page");
      const actionMessage = runsPage.locator(".action-message").first();
      await expect(runsPage).toContainText(selectedIssueKey, { timeout: 30_000 });
      await expect(page.getByRole("button", { name: /Start Daemon/ })).toBeEnabled({ timeout: 30_000 });
      await clickFirst(page, /Start Daemon/);
      await expect(runsPage).toContainText(/Start Daemon requested|Running|Claimed|Blocked|Done/, { timeout: 60_000 });
      const message = await actionMessage.innerText().catch(() => "");
      expect(message).not.toMatch(/Start Daemon failed|Internal Server Error|Traceback/);
    });

    await stepOrBlock(testInfo, page, "inspect execution evidence and version progress", async () => {
      await page.goto(`${workbenchUrl}/?v=browser-dogfood-first#issues/${selectedIssueKey}`, { waitUntil: "domcontentloaded" });
      const issueDetail = page.getByTestId("issue-detail");
      await expect(issueDetail).toBeVisible({ timeout: 20_000 });
      await expect(issueDetail).toContainText(selectedIssueKey, { timeout: 30_000 });
      await expect(issueDetail.getByRole("heading", { name: "Execution Results" })).toBeVisible({ timeout: 20_000 });
      if (mode !== "real") {
        throw new Error("BLOCKED_REHEARSAL_NOT_CLOSURE: browser path reached evidence inspection, but real mode was not requested.");
      }
      const closureState = await waitForStructuredClosure(page, selectedIssueKey);
      if (closureState.status === "external_blocker") {
        throw new Error(`BLOCKED_NOT_CLOSED: external Codex/Claude execution blocker reached from browser path: ${closureState.reason}`);
      }
      if (closureState.status !== "real_closed") {
        throw new Error(`REAL_EXECUTION_NOT_PROVEN: ${closureState.reason}`);
      }
      await page.reload({ waitUntil: "domcontentloaded" });
      await expect(issueDetail).toContainText(/Execution Results|Diff artifact|tests|Review|Evidence Center/, { timeout: 30_000 });
      const body = await issueDetail.innerText();
      expect(body).not.toContain("No execution results yet");
      await mkdir(resultDir, { recursive: true });
      const closureScreenshotPath = path.join(resultDir, "closure-issue-detail.png");
      await page.screenshot({ fullPage: false, path: closureScreenshotPath });
      const workbenchSnapshotPath = path.join(resultDir, "workbench-snapshot.json");
      const issueSnapshotPath = path.join(resultDir, `issue-${selectedIssueKey}.json`);
      const workbenchResponse = await page.request.get(`${workbenchUrl}/api/workbench`);
      expect(workbenchResponse.ok(), `workbench snapshot failed: ${workbenchResponse.status()}`).toBeTruthy();
      const workbenchSnapshot = await workbenchResponse.json();
      const issueResponse = await page.request.get(`${workbenchUrl}/api/issues/${encodeURIComponent(selectedIssueKey)}`);
      expect(issueResponse.ok(), `issue snapshot failed: ${issueResponse.status()}`).toBeTruthy();
      const issueSnapshot = await issueResponse.json() as IssueSnapshot;
      await writeFile(workbenchSnapshotPath, `${JSON.stringify(workbenchSnapshot, null, 2)}\n`);
      await writeFile(issueSnapshotPath, `${JSON.stringify(issueSnapshot, null, 2)}\n`);
      const issue = (issueSnapshot.issue ?? {}) as Record<string, any>;
      const assignment = (latestAssignment(issueSnapshot) ?? {}) as AssignmentSnapshot;
      const execution = (latestExecution(issueSnapshot) ?? {}) as ExecutionSnapshot;
      const evidenceItems = (issue.evidence_sections ?? []).flatMap((section: { items?: unknown[] }) => section.items ?? []) as Array<Record<string, unknown>>;
      const artifactPath = (label: RegExp, category?: string) => {
        const item = evidenceItems.find((entry) => (
          (!category || entry.category === category)
          && label.test(String(entry.label ?? ""))
          && entry.path_or_url
        ));
        return item?.path_or_url ? String(item.path_or_url) : "";
      };
      const executionLog = execution.execution_log_artifact_path
        ? await readJsonIfExists(String(execution.execution_log_artifact_path))
        : {};
      const workbenchDelivery = workbenchSnapshot.currentVersionDelivery ?? {};
      const evidenceRefs = sourceEvidenceRefs(issueSnapshot);
      const sourceDocuments = sourceDocumentIds(issueSnapshot);
      const sourceArtifacts = sourceArtifactIds(issueSnapshot);
      const targetRepoAfterCommit = gitOutput(["rev-parse", "HEAD"]);
      const targetRepoAfterStatus = gitOutput(["status", "--short"]);
      await writeFile(
        path.join(resultDir, "closure-result.json"),
        `${JSON.stringify(
          {
            schema_version: "ariadne.project_version_closure.v1",
            status: "REAL_CLOSED",
            mode,
            created_at: new Date().toISOString(),
            target_path: targetPath,
            workbench_url: page.url(),
            project: {
              project_id: issue.target_project_id ?? workbenchDelivery.target_project_id ?? "",
              title: issue.target_project_label ?? workbenchDelivery.target_project_label ?? "",
              goal: workbenchDelivery.target_state ?? "",
              target_version: issue.target_version ?? workbenchDelivery.version_label ?? targetVersion,
              project_version_id: issue.project_version_id ?? workbenchDelivery.project_version_id ?? "",
            },
            target_repo: {
              path: targetPath,
              before_commit: targetRepoBeforeCommit,
              after_commit: targetRepoAfterCommit,
              git_status_before: targetRepoBeforeStatus,
              git_status_after: targetRepoAfterStatus,
            },
            sources: sourceDocuments.map((sourceId: string) => ({
              source_id: sourceId,
              type: "source_document",
              uri_or_path: (issue.source_links ?? []).find((link: string) => link.includes("://")) ?? "",
              artifact_ids: sourceArtifacts,
              evidence_refs: evidenceRefs,
            })),
            issue_delta: {
              preview_id: previewId,
              compiler_mode: issue.compiler_provenance?.compiler_mode ?? "",
              applied_at: "",
              item_count: appliedIssueKeys.length,
              applied_issue_keys: appliedIssueKeys,
            },
            selected_issue: {
              ticket_id: issue.id ?? "",
              ticket_key: issue.key ?? selectedIssueKey,
              title: issue.title ?? "",
              acceptance_criteria: issue.acceptance_criteria ?? [],
              affected_modules: issue.affected_modules ?? [],
              source_evidence_refs: evidenceRefs,
            },
            assignment: {
              assignment_id: assignment.id ?? "",
              agent_id: assignment.agent_id ?? "",
              agent_name: assignment.agent_name ?? "",
              backend_name: assignment.backend_name ?? "",
              runtime_profile: `${assignment.agent_id ?? ""}:runtime`,
              status: assignment.status ?? "",
            },
            handoff: {
              artifact_id: issue.handoff?.id ?? "",
              path: issue.handoff?.handoff_file ?? "",
              contains_goal: body.includes("Goal") || body.includes("GOAL"),
              contains_evidence: (issue.source_evidence_refs ?? []).length > 0,
              contains_allowed_paths: body.includes("Allowed Paths") || body.includes("allowed"),
              contains_test_command: body.includes("python3.11 -m pytest"),
            },
            execution: {
              execution_result_id: execution.id ?? "",
              backend_name: execution.backend_name ?? "",
              command_summary: String(executionLog.command ?? ""),
              exit_code: execution.exit_code ?? null,
              stdout_artifact_path: execution.execution_log_artifact_path ?? "",
              stderr_artifact_path: execution.execution_log_artifact_path ?? "",
              provider_failure_kind: executionLog.provider_failure_kind ?? null,
              changed_files: execution.changed_files ?? [],
              git_diff_artifact_path: execution.diff_artifact_path ?? "",
              test_command: executionLog.test_command ?? "",
              test_exit_code: execution.test_exit_code ?? null,
              test_stdout_artifact_path: artifactPath(/test_output/i, "execution"),
              test_stderr_artifact_path: artifactPath(/test_output/i, "execution"),
            },
            review: {
              review_report_id: artifactPath(/review_report/i, "review").split("/").pop()?.replace(".json", "") ?? "",
              verdict: issue.review_verdict ?? "",
              summary: issue.review_summary ?? "",
              artifact_path: artifactPath(/review_report/i, "review"),
            },
            inbox: {
              open_item_ids: [],
              resolved_item_ids: [],
            },
            memory: {
              record_ids: [],
              artifact_paths: [artifactPath(/memory[\s_-]*record/i, "memory")].filter(Boolean),
            },
            next_issues: {
              artifact_path: artifactPath(/next[\s_-]*tickets/i, "next_ticket"),
              suggested_issue_count: issue.next_issue_links?.length ?? 0,
            },
            workbench_evidence: {
              screenshots: [closureScreenshotPath],
              api_snapshots: [workbenchSnapshotPath, issueSnapshotPath],
              console_log_path: "",
            },
            merge_gate: {
              eligible: true,
              checks: [
                "browser Workbench path",
                "real Codex/Claude backend",
                "target repo changed files",
                "tests recorded",
                "review pass",
                "memory and next issues recorded",
              ],
            },
            execution_evidence_text: body,
            recorded_at: new Date().toISOString(),
          },
          null,
          2,
        )}\n`,
      );
    });
  });
});

function classifyInspectorEvidence(text: string) {
  if (/还没有 execution \/ diff \/ tests \/ review 回流/.test(text)) return "pending";
  if (/No execution results yet/.test(text)) return "pending";
  if (/状态\s*(ready_to_claim|运行中|running)|实时事件：execution \/ started|阶段\s*execution/i.test(text)) return "pending";
  if (/\b(Ready to claim|Claimed|Running)\b/.test(text) && !/\b(exit|tests)\s*(-?\d+)/i.test(text)) return "pending";
  if (
    /command is unavailable|命令不可用|not logged in|login required|quota|rate limit|External execution blocked|ARIADNE_ENABLE_EXTERNAL_EXECUTION|Codex CLI|Claude CLI/i.test(text)
  ) {
    return "external_blocker";
  }
  const realExecutionSignals = [
    /\b(codex|claude-code)\b/i,
    /exit\s*(-?\d+)/i,
    /tests\s*(-?\d+)/i,
    /Diff artifact:\s*(?!No diff artifact recorded)/i,
    /mini_code_agent\/|pyproject\.toml|tests\//i,
    /Review report: pass|Review\s+pass|Review[\s\S]*pass/i,
    /Memory record|Memory Artifacts/i,
    /Next tickets artifact|Next Tickets/i,
  ];
  const hasRealProof = realExecutionSignals.every((pattern) => pattern.test(text));
  if (hasRealProof && !hasUnsafeClosureMarker(text)) {
    return "real_closed";
  }
  if (/Blocked[\s\S]*(IncompleteRead|agent_error|failed|blocked)|Assignment Progress[\s\S]*(Blocked|Failed)|Execution failed|Reviewer verdict|needs_fix|Review blocked/i.test(text)) return "product_blocker";
  if (/No changed files recorded|No diff artifact recorded/.test(text)) return "product_blocker";
  return "pending";
}

function hasUnsafeClosureMarker(text: string) {
  return /fake-codex|dry-run|演练模式\s*支持|门禁关闭|已阻塞/i.test(text)
    || /dry_run\s*[:=]\s*true/i.test(text)
    || /"dry_run"\s*:\s*true/i.test(text)
    || /"blocked"\s*:\s*true/i.test(text);
}

async function readJsonIfExists(filePath: string) {
  try {
    return JSON.parse(await readFile(filePath, "utf8"));
  } catch {
    return {};
  }
}
