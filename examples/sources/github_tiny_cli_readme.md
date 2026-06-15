# GitHub README Note - Tiny CLI Project Pattern

This README describes a small Python CLI called `demo-todo`.

## Current commands

```bash
demo-todo add "task"
demo-todo list
```

## Useful pattern

Small CLIs should expose machine-readable export commands so other agents and
automation tools can inspect state without scraping text output.

## Suggested build action

Add JSON export command to the target CLI project.
