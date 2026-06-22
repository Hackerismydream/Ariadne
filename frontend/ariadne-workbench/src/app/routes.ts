export type PageKey = "delivery" | "project" | "sources" | "tasks" | "ready" | "diagnostics";

export type HashRoute = {
  page?: PageKey;
  ticketRef?: string;
  redirectHash?: string;
};

export function parseHashRoute(hash = globalThis.location?.hash ?? ""): HashRoute {
  const value = hash.replace(/^#/, "").trim();
  if (!value) return {};
  const issueMatch = value.match(/^issues\/([^/?#]+)$/i) ?? value.match(/^(?:issue|ticket)=([^&]+)/i);
  if (issueMatch) return { page: "ready", ticketRef: decodeURIComponent(issueMatch[1]) };
  const legacyMap: Record<string, PageKey> = {
    goal: "project",
    knowledge: "sources",
    issues: "ready",
    "plan-changes": "tasks",
    team: "diagnostics",
    runs: "diagnostics",
    agents: "diagnostics",
    runtimes: "diagnostics",
    runtime: "diagnostics",
    skills: "diagnostics",
    inbox: "diagnostics",
  };
  if (value === "delivery" || value === "version") {
    return { page: "ready", redirectHash: "#issues" };
  }
  if (legacyMap[value]) return { page: legacyMap[value] };
  if (["project", "sources", "tasks", "ready", "diagnostics"].includes(value)) {
    return { page: value as PageKey };
  }
  return {};
}

export function pageHash(page: PageKey) {
  const hashes: Record<PageKey, string> = {
    project: "#project",
    sources: "#sources",
    tasks: "#plan-changes",
    ready: "#issues",
    delivery: "#issues",
    diagnostics: "#diagnostics",
  };
  return hashes[page];
}

export function applyRouteRedirect(route: HashRoute) {
  if (route.redirectHash && globalThis.location?.hash !== route.redirectHash) {
    globalThis.history?.replaceState(null, "", route.redirectHash);
  }
}

export function ensureDefaultHashRoute() {
  if (!globalThis.location?.hash) {
    globalThis.history?.replaceState(null, "", "#issues");
  }
}
