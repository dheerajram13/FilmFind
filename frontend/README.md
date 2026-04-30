# FilmFind Frontend

Next.js 16 frontend for the FilmFind semantic movie discovery engine.

## Stack

- **Next.js 16** with App Router
- **React 19**, TypeScript (strict mode)
- **TailwindCSS 4**, Framer Motion
- Custom fetch client with AbortController support

## Quick Start

All commands run inside Docker — no local Node setup needed.

```bash
# From repo root
docker compose up --build

# Lint
docker compose exec frontend npm run lint

# Type check
docker compose exec frontend npm run type-check

# Production build
docker compose exec frontend npm run build
```

Frontend available at http://localhost:3000

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL (for image CDN) | — |

Set these in `.env.local` (or `.env` at repo root for Docker Compose).

## Project Structure

```
frontend/
├── app/
│   ├── page.tsx              # Entry point — renders FilmfindHome
│   ├── layout.tsx            # Root layout + metadata
│   └── globals.css           # Global styles
├── components/home/
│   ├── FilmfindHome.tsx      # Top-level state orchestrator
│   ├── HomeScreen.tsx        # Landing / search input
│   ├── ResultsScreen.tsx     # Search results list
│   ├── DetailScreen.tsx      # Movie detail view
│   ├── ResultCard.tsx        # Individual result card
│   ├── FiltersSidebar.tsx    # Genre/year/streaming filters
│   └── SixtySecondMode.tsx   # 60-second mood-based pick mode
├── hooks/
│   ├── useSearch.ts          # Search state + in-flight abort
│   └── useFilters.ts         # Client-side filter state
├── lib/
│   ├── api-client.ts         # Typed fetch wrapper (AbortSignal support)
│   ├── movie-formatters.ts   # Pure display formatting helpers
│   ├── streaming-providers.ts # Provider name normalisation + icons
│   └── image-utils.ts        # TMDB/Supabase image URL resolution
└── types/
    └── api.ts                # TypeScript interfaces matching backend Pydantic schemas
```

## API Client

```typescript
import apiClient from "@/lib/api-client";

// Search (cancels previous in-flight request automatically)
const results = await apiClient.search("dark sci-fi like Interstellar", undefined, 10);

// 60-second pick
const pick = await apiClient.sixtyPick({ mood: "chill", context: "solo-night", craving: "mind-blown" });

// Log user action
await apiClient.sixtyAction(sessionId, { watch_clicked: true });
```

The `search` and `sixtyPick` methods accept an optional `AbortSignal` — `useSearch` handles cancellation automatically when a new search starts before the previous one finishes.

## Key Design Decisions

- **No global state library** — all state lives in `useSearch` and `useFilters` hooks, passed as props
- **`SixtySecondMode` is dynamically imported** — keeps the main bundle lean since it's a heavy component
- **Image URLs** — `image-utils.ts` resolves TMDB paths to full CDN URLs, with Supabase Storage as the preferred source when available (`poster_supabase_url` takes priority over `poster_path`)
- **Streaming providers** — `streaming-providers.ts` normalises inconsistent TMDB provider name strings (e.g. "Amazon Prime Video" → "prime video") before display
