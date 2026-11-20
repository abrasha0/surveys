# AnkieterAI frontend

React single-page app for AnkieterAI: login, starting the processing, verifying the AI
results and downloading the CSV. The UI is in Polish.

Stack: React 19, TypeScript, Vite 8, React Router, TanStack Query, Zustand,
Tailwind CSS 4, oxlint. Requires Node.js 20.19+ or 22.12+.

```bash
npm install
npm run dev       # dev server on http://localhost:5173, proxies /api to localhost:8000
npm run lint      # oxlint
npm run build     # type check and production build into dist/
```

The backend must be running on port 8000 (see the main [README](../../README.md)).

## Layout

```
src/
  app/          entry point, routes, layout, auth guard
  api/          fetch wrapper and TanStack Query hooks
  features/     screens: auth, welcome, verification, complete
  components/   page image viewer, page tabs, spinner
  hooks/        draft sync, Space shortcut
  store/        Zustand store: selected page, validation state, drafts (localStorage)
  utils/        ETA formatting
  constants.ts  shared constants
```

See [docs/architecture.md](../../docs/architecture.md) for how the frontend talks to the
API.
