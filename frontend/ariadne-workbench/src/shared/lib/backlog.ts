import type { WorkbenchData } from "../../types";

export function groupBacklogChanges(changes: WorkbenchData["backlogChanges"]) {
  return {
    added: changes.filter((change) => change.kind === "added"),
    updated: changes.filter((change) => change.kind === "updated"),
    deferred: changes.filter((change) => change.kind === "deferred"),
    rejected: changes.filter((change) => change.kind === "rejected"),
  };
}
