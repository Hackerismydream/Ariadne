import { expect, test, type Page, type TestInfo } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const workbenchUrl = process.env.ARIADNE_WORKBENCH_URL ?? "http://127.0.0.1:8766";
const resultDir = process.env.ARIADNE_DOGFOOD_RESULT_DIR
  ?? path.resolve(process.cwd(), "../../.ariadne/dogfood/browser");
const serverLogPath = process.env.ARIADNE_DOGFOOD_SERVER_LOG ?? "";
const targetPath = process.env.ARIADNE_DOGFOOD_TARGET_PATH
  ?? "/Users/martinlos/code/ariadne-dogfood/mini-code-agent";
const mode = process.env.ARIADNE_DOGFOOD_MODE ?? "blocked-ok";

const sources = [
  "https://minimal-agent.com/",
  "https://github.com/SWE-agent/mini-SWE-agent",
  "https://github.com/LiuMengxuan04/MiniCode",
];

function slug(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 80) || "step";
}

async function pageState(page: Page) {
  const text = await page.locator("body").innerText({ timeout: 1_500 }).catch((error) => `UNREADABLE_BODY: ${String(error)}`);
  const projectInputEnabled = await page.getByLabel("项目文件夹").isEnabled({ timeout: 1_000 }).catch(() => false);
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

test.describe("Mini Code Agent browser dogfood", () => {
  test("drives the real Workbench product path until closure or first blocker", async ({ page }, testInfo) => {
    test.setTimeout(180_000);

    await stepOrBlock(testInfo, page, "open real Workbench in API mode", async () => {
      await page.goto(`${workbenchUrl}/?v=browser-dogfood-first#project`, { waitUntil: "domcontentloaded" });
      await expect(page.getByRole("heading", { name: "当前目标" })).toBeVisible({ timeout: 15_000 });
      await expect.poll(async () => (await pageState(page)).connection, {
        message: "Workbench should leave fixture/disconnected mode and become writable API mode",
        timeout: 20_000,
      }).toBe("api");
    });

    await stepOrBlock(testInfo, page, "create or select target project folder", async () => {
      await page.getByLabel("项目文件夹").fill(targetPath);
      await page.getByLabel("项目名称").fill("Mini Code Agent");
      await clickFirst(page, "注册项目");
      await expect(page.locator("body")).toContainText(/目标项目已注册|target path does not exist|Target project path does not exist/, { timeout: 20_000 });
      const body = await page.locator("body").innerText();
      expect(body).toContain("目标项目已注册");
    });

    await stepOrBlock(testInfo, page, "set project goal and target version", async () => {
      await page.getByLabel("目标标题").fill("Build Mini Code Agent v0.1");
      await page.getByLabel("北极星目标").fill(
        "用户给一个本地项目目标和外部知识，Ariadne 组织 agent team 生成目标项目 issue，并调度 Codex/Claude 把 mini-code-agent 推进到可运行 v0.1。",
      );
      await page.getByLabel("目标态").fill(
        "mini_code_agent CLI 可以运行 --help，并能执行一次 inspect/summarize 风格的本地任务，Workbench 回流 diff、tests、review、memory 和 next issue。",
      );
      await clickFirst(page, "创建目标");
      await expect(page.locator("body")).toContainText("目标已创建", { timeout: 20_000 });
    });

    await stepOrBlock(testInfo, page, "add three external sources and analyze them", async () => {
      await page.goto(`${workbenchUrl}/?v=browser-dogfood-first#sources`, { waitUntil: "domcontentloaded" });
      await expect(page.getByRole("heading", { level: 1, name: "项目输入" })).toBeVisible({ timeout: 15_000 });
      for (const source of sources) {
        const urlInput = page.getByLabel("路径或 URL");
        const addAndAnalyze = page.getByRole("button", { name: "添加并分析" });
        await urlInput.fill("");
        await urlInput.click();
        await page.keyboard.insertText(source);
        await expect(urlInput).toHaveValue(source);
        await expect(addAndAnalyze).toBeEnabled({ timeout: 5_000 });
        await addAndAnalyze.click();
        await expect(page.locator("body")).toContainText(/分析完成|已打开现有记录|已阻塞|分析失败/, { timeout: 45_000 });
        const body = await page.locator("body").innerText();
        expect(body).not.toMatch(/分析失败|Internal Server Error|Traceback|500/);
      }
    });

    await stepOrBlock(testInfo, page, "generate target-project issue preview", async () => {
      await clickFirst(page, "查看任务建议");
      await expect(page.locator("body")).toContainText(/MCA-\d{3}|还没有分析完成的输入|任务建议生成失败/, { timeout: 45_000 });
      const body = await page.locator("body").innerText();
      expect(body).not.toMatch(/还没有分析完成的输入|任务建议生成失败|Internal Server Error|Traceback|500/);
      expect(body).toMatch(/MCA-\d{3}|Mini Code Agent|mini-code-agent/i);
    });

    await stepOrBlock(testInfo, page, "apply issue delta", async () => {
      await clickFirst(page, "应用任务变更");
      await expect(page.locator("body")).toContainText(/任务建议已应用|stale_preview|应用任务变更失败|Internal Server Error/, { timeout: 45_000 });
      const body = await page.locator("body").innerText();
      expect(body).not.toMatch(/stale_preview|应用任务变更失败|Internal Server Error|Traceback|500/);
    });

    await stepOrBlock(testInfo, page, "open MCA-001 target issue", async () => {
      await page.goto(`${workbenchUrl}/?v=browser-dogfood-first#issues/MCA-001`, { waitUntil: "domcontentloaded" });
      await expect(page.locator("body")).toContainText("MCA-001", { timeout: 20_000 });
      const body = await page.locator("body").innerText();
      expect(body).toMatch(/Mini Code Agent|mini-code-agent|MCA-001/i);
    });

    await stepOrBlock(testInfo, page, "assign current issue to Codex or Claude", async () => {
      await clickFirst(page, /^分配$/);
      await expect(page.locator("body")).toContainText(/已创建 assignment|分配失败|未连接产品 API|缺少可用目标/, { timeout: 30_000 });
      const body = await page.locator("body").innerText();
      expect(body).not.toMatch(/分配失败|未连接产品 API|缺少可用目标|Internal Server Error|Traceback|500/);
    });

    await stepOrBlock(testInfo, page, "authorize local runtime for current assignment", async () => {
      await clickFirst(page, /授权 Codex\/Claude 并启动运行时/);
      await expect(page.locator("body")).toContainText(/本地运行时已启动|启动本地运行时失败/, { timeout: 30_000 });
      const body = await page.locator("body").innerText();
      expect(body).not.toMatch(/启动本地运行时失败|Internal Server Error|Traceback|500/);
    });

    await stepOrBlock(testInfo, page, "run current assignment from Workbench", async () => {
      await clickFirst(page, /分配后由运行时自动 claim|运行/);
      await expect(page.locator("body")).toContainText(/结果和阻塞原因会回流|缺少执行确认 token|运行失败|已读取 \d+ 条 assignment events/, { timeout: 60_000 });
      const body = await page.locator("body").innerText();
      expect(body).not.toMatch(/缺少执行确认 token|运行失败|Internal Server Error|Traceback|500/);
    });

    await stepOrBlock(testInfo, page, "inspect execution evidence and version progress", async () => {
      await expect(page.getByText("执行证据")).toBeVisible({ timeout: 20_000 });
      const body = await page.locator("body").innerText();
      expect(body).toMatch(/执行结果|Diff|测试退出码|评审|Memory|Next Tickets/);
      expect(body).not.toContain("还没有 execution / diff / tests / review 回流");
      const realExecutionSignals = [
        /后端\s*(codex|claude-code)/i,
        /执行结果\s*(?!未记录)/,
        /退出码\s*(-?\d+)/,
        /测试退出码\s*(-?\d+)/,
      ];
      const missingRealProof = realExecutionSignals.some((pattern) => !pattern.test(body));
      const unsafeProof = /fake-codex|dry_run|dry-run|演练模式\s*支持|门禁关闭|已阻塞|blocked/i.test(body);
      if (mode !== "real") {
        throw new Error("BLOCKED_REHEARSAL_NOT_CLOSURE: browser path reached evidence inspection, but real mode was not requested.");
      }
      if (missingRealProof || unsafeProof) {
        throw new Error("REAL_EXECUTION_NOT_PROVEN: Workbench did not show unblocked Codex/Claude CLI execution with exit code, tests, diff, review, memory, and next tickets.");
      }
    });
  });
});
