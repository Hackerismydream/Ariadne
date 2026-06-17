import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(here, "..");
const repoRoot = resolve(frontendRoot, "..", "..");

async function readJson(path, fallback) {
  try {
    return JSON.parse(await readFile(path, "utf8"));
  } catch {
    return fallback;
  }
}

function runtimeFromCapability(capability) {
  return {
    machine: "local-mac",
    backend: capability.backend_name,
    status: capability.available ? "online" : "offline",
    version: capability.command_path ?? capability.command ?? "internal",
    cost7d: "$0.00",
    command: capability.command,
    commandPath: capability.command_path,
    externalExecutionEnabled: capability.external_execution_enabled,
    commandTemplateSet: capability.command_template_set,
    confirmExecutionRequired: capability.confirm_execution_required,
    supportsExternalExecution: capability.supports_external_execution,
    supportsDryRun: capability.supports_dry_run,
    checkedAt: capability.checked_at,
  };
}

function resourceFromProjectResource(resource) {
  return {
    id: resource.id,
    label: resource.label,
    resourceType: resource.resource_type,
    localPath: resource.resource_ref?.local_path,
  };
}

const runtimeSnapshot = await readJson(resolve(repoRoot, ".ariadne", "runtimes", "capability_snapshot.json"), {
  capabilities: [],
});
const projectResources = await readJson(resolve(repoRoot, ".ariadne", "project", "resources.json"), {
  resources: [],
});

const data = {
  runtimes: (runtimeSnapshot.capabilities ?? []).map(runtimeFromCapability),
  projectResources: (projectResources.resources ?? []).map(resourceFromProjectResource),
};

const outputPath = resolve(frontendRoot, "public", "web_data", "workbench.json");
await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
console.log(`Wrote ${outputPath}`);
