# Ariadne Self Improvement Note

## Current Gap

Ariadne should improve daemon heartbeat, safe retry, handoff visibility, and real Codex teammate execution.

## Build Direction

Implement local runtime supervision, assignment retry commands, agent handoff comments, and board visibility without adding a server.

## Acceptance Signals

- daemon status shows heartbeat and stale detection.
- ticket retry creates a new assignment instead of overwriting history.
- ticket handoffs shows planner, execution, review, memory, and build lead transitions.
- real Codex execution remains safety-gated.
