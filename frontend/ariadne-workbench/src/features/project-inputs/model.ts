export type SourceFormType = "blog" | "paper" | "github_repo" | "note";

export type InferredSourceInput = {
  title: string;
  sourceType: SourceFormType;
  sourceRole: "reference_project" | "requirement_source" | "background_knowledge";
  summary: string;
};

export function inferSourceInput(rawValue: string): InferredSourceInput {
  const value = rawValue.trim();
  if (!value) {
    return { title: "", sourceType: "blog", sourceRole: "background_knowledge", summary: "" };
  }
  try {
    const url = new URL(value);
    const host = url.hostname.replace(/^www\./, "");
    const parts = url.pathname.split("/").filter(Boolean);
    if (host === "github.com" && parts.length >= 2) {
      const owner = parts[0];
      const repo = parts[1].replace(/\.git$/, "");
      return {
        title: `${owner}/${repo}`,
        sourceType: "github_repo",
        sourceRole: "reference_project",
        summary: `${owner}/${repo} reference repository. Ariadne will use it as implementation context and avoid direct code copying.`,
      };
    }
    if (value.toLowerCase().endsWith(".pdf") || host.includes("arxiv.org")) {
      return {
        title: parts.at(-1)?.replace(/[-_]/g, " ") || host,
        sourceType: "paper",
        sourceRole: "background_knowledge",
        summary: `${host} paper or PDF source.`,
      };
    }
    return {
      title: parts.at(-1)?.replace(/[-_]/g, " ") || host,
      sourceType: "blog",
      sourceRole: "requirement_source",
      summary: `${host} web source.`,
    };
  } catch {
    const name = value.split(/[\\/]/).filter(Boolean).at(-1) || value;
    return {
      title: name.replace(/[-_]/g, " "),
      sourceType: "note",
      sourceRole: "background_knowledge",
      summary: "Local or manual source.",
    };
  }
}

export function sourceAnalysisLabel(status: string) {
  return {
    pending: "已添加",
    resolving: "解析中",
    fetching: "抓取中",
    analyzing: "分析中",
    analyzed: "分析完成",
    partial: "部分完成",
    blocked: "已阻塞",
    failed: "分析失败",
  }[status] ?? status;
}
