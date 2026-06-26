# Phase 5 Skills / Instructions / Environment Evidence

## Scope

Phase 5 makes agent capability configuration affect routing and handoff, not just the profile page.

Implemented behavior:

- Agent Detail / Skills can attach or remove real `.skills` entries through the existing agent update API.
- Agent Detail / Instructions saves the agent system instructions.
- Agent Detail / Environment saves key names only; no secret values are stored or displayed.
- Direct agent assignment copies the selected agent's `skill_ids` into `RouteDecision.skill_refs`.
- Handoff packet markdown includes selected skills, agent instructions, and environment key names.

## Three Anchors

### 1. CDP Observation

The Multica authenticated browser session is unavailable in headless CDP in this environment. The implementation therefore used the source-code anchor and the parity matrix. This is the same observed environment blocker recorded in Phase 3 evidence.

### 2. Multica Source Read

Source files inspected:

- `/Users/martinlos/code/multica/packages/views/agents/components/tabs/skills-tab.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/skill-add-dialog.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/skill-multi-select.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/skill-picker-list.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/tabs/instructions-tab.tsx`
- `/Users/martinlos/code/multica/packages/views/agents/components/tabs/env-tab.tsx`

Extracted semantics:

- Skills are attached to durable agents and can be added or removed from the detail surface.
- Instructions are editable text persisted on the agent.
- Environment values are sensitive; the product should expose key presence/configuration without leaking values.
- Downstream execution should inherit agent capabilities through route/handoff.

### 3. Ariadne Mapping

| Multica concept | Ariadne Phase 5 mapping |
| --- | --- |
| Skill entity | local BuildSkill discovered from `.skills/` |
| Agent-skill binding | `AgentDefinition.skill_ids` |
| Instructions | `AgentDefinition.instructions` |
| Environment | `AgentRuntimeProfile.environment_keys`, key names only |
| Route selected skills | `RouteDecision.skill_refs` |
| Handoff capability context | selected skills + instructions + env key names in handoff markdown |

No new skill binding store was added.

## Browser Verification

Workbench URL:

```text
http://127.0.0.1:8766
```

Browser actions performed:

1. Opened `#team/agents/agent_4b050c358500`.
2. Opened `skills` tab and attached a real `.skills` entry.
3. Opened `instructions` tab and saved:
   `Phase 5 evidence: use attached skills and preserve environment key boundaries.`
4. Opened `environment` tab and saved key names:
   `CODEX_HOME`, `DEEPSEEK_API_KEY`.
5. Opened `#issues/M0TR-002`.
6. Assigned the issue to the same real agent.
7. Verified route and handoff evidence include the agent bindings.

Screenshots:

- `agent-skills-binding.png`
- `agent-instructions-saved.png`
- `agent-env-keys-saved.png`
- `issue-assigned-with-agent-bindings.png`

API / artifact evidence:

- `agent-detail-api.json`
- `issue-detail-api.json`
- `route-decision.json`
- `handoff.md`
- `browser-verification.txt`

Handoff evidence:

```text
## Selected Skills
- `skill_9179aec0c6a9`

## Agent Instructions
Phase 5 evidence: use attached skills and preserve environment key boundaries.

## Environment Keys
- `CODEX_HOME`
- `DEEPSEEK_API_KEY`
```

## Commands Run

```bash
python3.11 -m pytest tests/test_agent_definition_store.py -q
ruff check .
cd frontend/ariadne-workbench && npm run build
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

## Result

Phase 5 acceptance is satisfied:

- Skill binding is persisted on `AgentDefinition`.
- Instructions and environment key names are persisted on `AgentDefinition` / runtime profile.
- Route decision references selected skills.
- Handoff packet carries selected skills, instructions, and environment key names.

Actual external execution remains gated and is not claimed here.
