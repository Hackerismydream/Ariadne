# Ariadne Workbench Frontend

This is the standalone Ariadne frontend lane. It is a local-first React/Vite
workbench that adapts Multica's issue-agent-runtime UI pattern for Ariadne's
`/goal` product direction.

## Run

```bash
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173/
```

Use a custom port:

```bash
npm run dev -- --port 5177
```

## Build

```bash
npm run build
```

The deployable static output is:

```text
frontend/ariadne-workbench/dist/
```

## Verify

From the repository root:

```bash
scripts/verify_workbench.sh
```

The script syncs local `.ariadne/` data into the ignored
`public/web_data/workbench.json` snapshot and then runs the production build.

## Current Pages

- 当前 Goal
- Issues board
- Ticket detail inspector
- 智能体
- 运行时
- Skills
- 收件箱

## Boundaries

- This frontend does not depend on Multica runtime, auth, or backend APIs.
- It does not mutate Ariadne core domain models.
- It starts with typed local seed data and is ready for a future Ariadne data
  adapter.
- Multica screenshots and source files are used only as design and interaction
  references.
