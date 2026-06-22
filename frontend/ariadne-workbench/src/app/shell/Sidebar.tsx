import { BookOpenText, FolderKanban, Inbox, ListTodo, Monitor, Plus, Search, Settings, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { PageKey } from "../routes";
import { pageHash } from "../routes";
import type { WorkbenchData } from "../../types";

const navGroups: Array<{
  label: string;
  items: Array<{ id: string; key: PageKey; label: string; icon: LucideIcon; hash?: string }>;
}> = [
  {
    label: "Workbench",
    items: [
      { id: "issues", key: "ready", label: "Issues", icon: FolderKanban, hash: "#issues" },
      { id: "sources", key: "sources", label: "Sources", icon: BookOpenText, hash: "#sources" },
      { id: "plan-changes", key: "tasks", label: "Plan Changes", icon: ListTodo, hash: "#plan-changes" },
      { id: "team", key: "diagnostics", label: "Team", icon: Users, hash: "#team" },
      { id: "runs", key: "diagnostics", label: "Runs", icon: Monitor, hash: "#runs" },
      { id: "inbox", key: "diagnostics", label: "Inbox", icon: Inbox, hash: "#inbox" },
      { id: "diagnostics", key: "diagnostics", label: "Diagnostics", icon: Settings, hash: "#diagnostics" },
    ],
  },
];

export function WorkbenchSidebar({
  data,
  page,
  onNavigate,
}: {
  data: WorkbenchData;
  page: PageKey;
  onNavigate: (page: PageKey, hash?: string) => void;
}) {
  const currentHash = globalThis.location?.hash || pageHash(page);
  return (
    <aside className="sidebar">
      <button className="workspace-switch" type="button">
        <span className="workspace-avatar">A</span>
        <span>Ariadne</span>
      </button>
      <button className="sidebar-command" type="button">
        <Search size={16} />
        <span>搜索...</span>
        <kbd>⌘ K</kbd>
      </button>
      <button className="create-button" type="button">
        <Plus size={16} />
        <span>新建 issue</span>
        <kbd>C</kbd>
      </button>
      {navGroups.map((group) => (
        <nav className="nav-group" key={group.label}>
          <p>{group.label}</p>
          {group.items.map((item) => {
            const Icon = item.icon;
            const enabled = ["project", "sources", "tasks", "ready", "diagnostics"].includes(item.key);
            const active = item.key === page && (!item.hash || currentHash === item.hash || item.hash === pageHash(page));
            return (
              <button
                className={`nav-item ${active ? "active" : ""}`}
                data-page={item.key}
                disabled={!enabled}
                key={item.id}
                type="button"
                onClick={() => enabled && onNavigate(item.key, item.hash)}
              >
                <Icon size={16} />
                <span>{item.label}</span>
                {item.id === "inbox" ? <em>{data.inbox.length}</em> : null}
              </button>
            );
          })}
        </nav>
      ))}
      <button className="help-button" type="button">?</button>
    </aside>
  );
}
