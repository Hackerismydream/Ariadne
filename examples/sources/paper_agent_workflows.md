# Paper Note - Evidence-Backed Agent Workflows

## Claim

Agent workflows become more reliable when each action is grounded in explicit
evidence, a clear acceptance criterion, and a bounded tool-use policy.

## Method

The note compares agent loops that act from hidden chain-of-thought with loops
that produce durable task packets, evidence snippets, and reviewable execution
records.

## Project implications

Ariadne should evaluate Build Packet quality before execution. Useful scoring
dimensions include evidence coverage, acceptance criteria quality, and scope
risk.

## Suggested build action

Add Build Packet quality evaluation: evidence coverage, acceptance criteria
quality, and scope risk score.
