# GitHub README Note: Tiny CLI Project Pattern

This repository is a tiny Python CLI app. It stores tasks in a local JSON file and exposes commands for adding and listing tasks.

## Existing commands

- `demo-todo add "Buy milk"`
- `demo-todo list`

## Missing feature

The CLI does not provide a machine-readable export command.

## Project implication for Ariadne demo

Ariadne should create a Build Ticket that asks the coding backend to add:

```bash
demo-todo export-json
```

Acceptance criteria:

- command exists;
- output is valid JSON list;
- tests pass;
- implementation changes only target project files.
