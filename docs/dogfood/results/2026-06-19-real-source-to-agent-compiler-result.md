# Real Source-to-Agent Compiler Dogfood Result

Date: 2026-06-19

## Scenario

Mini Code Agent dogfood path:

1. User creates or selects a local target project.
2. User adds external inputs such as GitHub repositories and notes.
3. Ariadne fetches or links the source.
4. Ariadne writes typed source artifacts and evidence.
5. Issue Factory compiles target-project issues from typed artifacts.
6. Build Team routes an approved issue.
7. Ariadne writes a frozen HandoffPacket before the assignment can be claimed.

## What Changed

- GitHub URL sources now go through a repository fetch/cache layer.
- Repository sources produce `repository_understanding` artifacts instead of generic knowledge cards.
- Issue Factory rejects selected sources that have not been analyzed into artifacts.
- Issue generation uses typed artifact payloads and evidence refs.
- Demo-oriented `demo_todo` mappings are quarantined to offline regression fixtures.
- Assignment readiness no longer synthesizes fake route or handoff ids.
- Build-team assignment persists a loadable `RouteDecision` and immutable `HandoffPacket`.
- CodexBackend and ClaudeCodeBackend reuse persisted handoff files instead of overwriting them.
- Workbench Sources page now shows source processing state, timeline rows, and clearer CTAs.

## Evidence

Focused verification passed:

- `tests/test_source_repository_fetch.py`
- `tests/test_repository_scanner.py`
- `tests/test_source_analysis.py`
- `tests/test_issue_factory_compiler.py`
- `tests/test_web_dogfood_product_path.py`
- `tests/test_handoff_packet_readiness.py`
- `tests/test_real_backend_gates.py`
- frontend static contract tests
- frontend production build

## Boundaries

- This result does not claim a successful real Codex or Claude execution.
- Automated tests still avoid network and external credentials.
- Real GitHub URL fetch is enabled in product code, but deterministic tests use local repository fixtures or fake fetchers.
- Deep repository semantic understanding is still scan-based, not a full LLM repo analyst.
