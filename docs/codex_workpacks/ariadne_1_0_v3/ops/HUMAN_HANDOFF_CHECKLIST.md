# Human Handoff Checklist

Before sending this to Codex, the human owner should decide:

1. Continue in the current PR branch or create a new branch.
2. Whether real Codex CLI is available locally.
3. Whether Feishu credentials should be provided now or postponed.
4. Whether the demo must use only FakeCodexBackend or also real CodexBackend.

Recommended minimal handoff:

- give Codex this whole workpack;
- tell Codex to continue from current branch;
- do not provide secrets initially;
- ask Codex to make full demo pass with FakeCodexBackend;
- real Codex/Feishu can be optional adapters.
