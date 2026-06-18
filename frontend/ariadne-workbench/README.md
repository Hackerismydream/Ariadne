# Ariadne Workbench Frontend

This is the standalone Ariadne frontend lane. It is a local-first React/Vite
workbench that adapts Multica's issue-agent-runtime UI pattern for Ariadne's
`/goal` product direction.

## Run

Start the local API control plane from the repository root:

```bash
python3.11 -m ariadne_ltb.cli api serve --host 127.0.0.1 --port 8766
```

Then start the frontend:

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

- The product path is API-first through Ariadne's local FastAPI control plane.
- Browser actions call assignment/run/comment APIs; they do not send raw shell
  commands or local filesystem paths.
- If the API is unavailable, the frontend falls back to a generated static
  snapshot and then fixture data. Those fallback modes are read-only.
- Multica screenshots and source files are used only as design and interaction
  references.
