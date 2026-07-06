# web (React + Vite + TypeScript)

## Run (Windows / PowerShell)

```powershell
cd apps/web
npm install
Copy-Item .env.example .env.local   # then fill in API base + Supabase anon key
npm run dev
```

Dev server: http://localhost:5173 (calls the API at `VITE_API_BASE_URL`).
Build: `npm run build` · Typecheck: `npm run typecheck` · Lint: `npm run lint` · Format: `npm run format` (Prettier)

## Layout

```
src/
  main.tsx              entry — wraps <App/> in <BrowserRouter>
  app/App.tsx           app shell (header + <AppRoutes/>)
  app/routes.tsx        route table (react-router-dom)
  pages/                screen components (HomePage pings /health; add more)
  lib/api.ts            fetch wrapper (apiGet/Post/Patch/Delete) — all API calls go here
  lib/supabase.ts       the only frontend Supabase client (anon key only)
  components/           shared/layout UI (or features/{domain}/ as it grows)
  styles.css
```

## Docker

```powershell
docker build -t app-web .   # multi-stage: vite build → nginx (SPA fallback in nginx.conf)
```

Rules: see [`docs/08_coding_guidelines/03_react_typescript.md`](../../docs/08_coding_guidelines/03_react_typescript.md).
