# Codebase AI - Frontend

React + Vite frontend for the repository workspace.

## Requirements

- Node.js 20+ (developed against Node 24)
- npm 10+

## Setup

```powershell
cd frontend
npm install
Copy-Item .env.example .env
```

`.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

Only public configuration belongs in `VITE_` variables. Never put Gemini keys,
database credentials or GitHub tokens in the frontend environment.

## Run

```powershell
npm run dev
```

The app runs at http://localhost:5173.

## Build

```powershell
npm run build
npm run preview
```

## Design foundation

- Tokens live in `src/styles/tokens.css` (Tailwind v4 `@theme`).
- Warm canvas `#F5F3EF`, dark workspace `#111827`, brand purple `#A268CF`,
  interaction blue `#5984EA`.
- Inter for interface text, JetBrains Mono for paths, commits and metadata.
- Shared primitives live in `src/components/ui`.

## Structure

```text
src/
  components/
    landing/    # landing-page sections
    layout/     # app shell and navigation
    system/     # real health indicator
    ui/         # shared primitives (button, input, badge, panel)
  features/     # feature API modules
  hooks/        # data hooks
  lib/          # axios client, class-name helper
  pages/        # route-level pages
  styles/       # design tokens
```
