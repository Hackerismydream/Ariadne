# 07 — Memory and Feishu Write-back

## Local memory is required

Ariadne 1.0 must write local memory even without Feishu credentials.

Required local files:

```text
.ariadne/memory/decision_log.md
.ariadne/memory/tickets/<ticket_id>.md
.ariadne/memory/build_packets/<packet_id>.json
.ariadne/memory/reviews/<ticket_id>.md
.ariadne/memory/weekly_summary.md
```

## Feishu dry-run is required

Generate Feishu write plan for each completed ticket.

Fields:

- doc title;
- doc body markdown;
- task titles;
- decision log entry;
- run summary;
- next actions;
- dry_run=true;
- required credentials list if user wants real write.

## Optional Feishu API write

Implement only if feasible in the same pass. It must be disabled by default.

Required env vars for real write:

```bash
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_FOLDER_TOKEN=
FEISHU_ENABLE_WRITE=0
```

Optional:

```bash
FEISHU_BASE_URL=https://open.feishu.cn
FEISHU_DOC_PARENT_TYPE=folder
```

Command:

```bash
ari memory sync <ticket_id_or_key> --target feishu --dry-run
ari memory sync <ticket_id_or_key> --target feishu --confirm-write
```

If credentials are missing or `FEISHU_ENABLE_WRITE != 1`, refuse real writes and output a clear dry-run plan.

## Security

Never store secrets in `.ariadne/` artifacts.

Create `.env.example`; never create `.env` with real values.

Add `.env`, `.env.*`, and secrets files to `.gitignore`.
