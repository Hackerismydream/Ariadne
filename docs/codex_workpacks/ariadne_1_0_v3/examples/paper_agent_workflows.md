# Paper Note: Evidence-Backed Agent Workflows

## Claim

Agent workflows become more reliable when every action is tied to evidence, explicit acceptance criteria, and a reviewable execution record.

## Method

The paper compares free-form agent conversations with structured workflow agents. Structured agents perform better when handoffs are typed and review steps are explicit.

## Project implication for Ariadne

Ariadne should score Build Packets for evidence coverage, acceptance criteria quality, and scope risk before sending them to a coding backend.

## Suggested build action

Create a Build Packet evaluator that computes:

- evidence coverage score;
- task clarity score;
- acceptance criteria score;
- scope creep risk.
