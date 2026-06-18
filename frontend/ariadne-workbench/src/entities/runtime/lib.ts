import type { RuntimeInfo } from "../../types";

export function selectableProductionRuntimes(runtimes: RuntimeInfo[]) {
  return runtimes.filter((runtime) => {
    if (runtime.backend === "shell") return false;
    if (runtime.fallbackOnly) return false;
    return runtime.canAssign || runtime.canRun || runtime.backend === "codex" || runtime.backend === "claude-code";
  });
}
