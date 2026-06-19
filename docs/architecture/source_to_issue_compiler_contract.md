# Source-to-Issue Compiler Contract

## Product Promise

Ariadne lets an AI Builder give a project goal and external inputs. Ariadne reads those inputs, turns them into auditable source artifacts and evidence, compiles issue deltas, and routes approved issues to Codex or Claude through a frozen handoff packet.

## Object Boundaries

- `SourceDocument`: identity and provenance of an input.
- `SourceFetchRecord`: how a remote or local source was fetched, linked, cached, or blocked.
- `SourceArtifact`: typed understanding output produced from one source.
- `SourceEvidence`: atomic cited claim from a source artifact.
- `BuildContextManifest`: frozen set of goal, target project, source documents, artifacts, evidence, and backlog fingerprint used by Issue Factory.
- `BacklogPreview`: proposed issue delta.
- `RouteDecision`: Build Lead decision for one approved issue.
- `HandoffPacket`: immutable packet sent to Codex or Claude.

## Required Invariants

- A GitHub repo source cannot become `analyzed` without a successful fetch/cache record or an explicit `blocked` fetch record.
- `knowledge_card` is only a text-source artifact, not the universal representation of all inputs.
- Issue Factory consumes `BuildContextManifest`, not raw source dumps.
- Every production issue operation must include source document ids, source artifact ids, evidence refs, target project id, affected modules, and acceptance criteria.
- An assignment cannot become `ready_to_claim` without a persisted `RouteDecision` and `HandoffPacket`.
- Runtime backends consume the frozen `HandoffPacket` and must not silently generate a conflicting prompt.

## Current Local Implementation

- GitHub URL inputs are resolved by `GitRepositoryFetcher`, cached under `.ariadne/sources/git/`, and recorded as `SourceFetchRecord`.
- Repository inputs emit `repository_understanding` artifacts with README summary, manifest files, entrypoints, selected files, test paths, license notes, reuse notes, and avoid notes.
- Text inputs still emit `knowledge_card` artifacts.
- Issue Factory rejects selected sources that are not `analyzed` or `partial`, or that have no typed artifacts.
- Build-team assignment persists route and handoff data before an assignment becomes claimable.
