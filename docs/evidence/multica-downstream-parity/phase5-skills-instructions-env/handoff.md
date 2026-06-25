# M0TR-002: Add DeepSeek-backed LLM client configuration

## Target Repository
/Users/martinlos/code/ariadne-dogfood/mini-code-agent

## Route
- Backend: `codex`
- Planner: `llm`
- Agent runtime: `llm`
- Selected agent: `Phase 3 Codex 1782402810345`

## Selected Skills
- `skill_9179aec0c6a9`

## Agent Instructions
Phase 5 evidence: use attached skills and preserve environment key boundaries.

## Environment Keys
- `CODEX_HOME`
- `DEEPSEEK_API_KEY`

## Task
The target agent needs a real upstream model client and local configuration path.

## Planner Tasks
- Add DeepSeek-backed LLM client configuration

## Allowed Paths
- `mini_code_agent/llm.py`
- `mini_code_agent/config.py`
- `tests/test_llm_config.py`

## Acceptance Criteria
- The implementation is reachable from the Web Workbench product path.
- The behavior writes inspectable run evidence.
- Tests cover the behavior without external credentials.

## Test Command
`/opt/homebrew/bin/pytest`

## Evidence References
- `source_evidence_49bbbf060425`
- `source_evidence_85eabe737a64`
- `source_evidence_407f170c61fb`
- `source_evidence_c1d4b49015ef`
- `source_evidence_189fb0414205`
- `source_evidence_c091afd8c290`
- `source_evidence_fbb7d9874eec`
- `source_evidence_08f634101190`
- `source_evidence_483cc8b4eec3`

## Forbidden Actions
- Do not commit.
- Do not push.
- Do not copy source code from reference repositories.
