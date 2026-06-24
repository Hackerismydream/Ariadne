# Ariadne Workbench Frontend

This is the standalone Ariadne frontend lane. It is a local-first React/Vite
workbench that adapts Multica's issue-agent-runtime UI pattern for Ariadne's
`/goal` product direction.

## Run

Build the frontend and start the local product Workbench from the repository root:

```bash
cd frontend/ariadne-workbench
npm install
npm run build
cd ../..
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

For development hot reload, start the API and Vite separately:

```bash
python3.11 -m ariadne_ltb.cli api serve --host 127.0.0.1 --port 8766
cd frontend/ariadne-workbench
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

The script runs the production build against the API-first frontend. Generated
snapshot files are developer artifacts only and are not loaded by the product
Workbench.

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
- If the API is unavailable, product mode shows a disconnected read-only state.
- Bundled test data is not a product data source. The Workbench either loads
  persisted state from Ariadne's local API or shows a disconnected read-only
  state.
- Multica screenshots and source files are used only as design and interaction
  references.
