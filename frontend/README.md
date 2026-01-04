# FilmFind Frontend

AI-Powered Movie Discovery Engine - Frontend Application

## Tech Stack

- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript (strict mode)
- **Styling**: TailwindCSS 4.x
- **UI Components**: ShadCN UI
- **Icons**: Lucide React
- **State Management**: React Hooks
- **API Client**: Custom fetch wrapper with error handling

## Project Structure

```
frontend/
├── app/                    # Next.js App Router
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Home page
│   └── globals.css        # Global styles with Tailwind directives
├── components/             # React components
├── lib/                    # Utility functions
│   ├── utils.ts           # Class name utilities (cn)
│   └── api-client.ts      # Backend API client
├── hooks/                  # Custom React hooks
├── types/                  # TypeScript type definitions
│   └── api.ts             # API response types
├── public/                 # Static assets
├── .env.local.example     # Environment variables template
├── next.config.ts         # Next.js configuration
├── tailwind.config.ts     # Tailwind configuration
├── tsconfig.json          # TypeScript configuration
└── package.json           # Dependencies and scripts
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Installation

1. Install dependencies:
```bash
npm install
```

2. Create environment file:
```bash
cp .env.local.example .env.local
```

3. Update `.env.local` with your backend API URL:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

Create a production build:

```bash
npm run build
```

### Start Production Server

```bash
npm start
```

### Type Checking

Run TypeScript type checker:

```bash
npm run type-check
```

### Linting

Run ESLint:

```bash
npm run lint
```

## API Client

The `lib/api-client.ts` provides a type-safe wrapper around the backend API:

```typescript
import apiClient from "@/lib/api-client";

// Search for movies
const results = await apiClient.search("dark sci-fi like Interstellar");

// Get movie details
const movie = await apiClient.getMovie(550);

// Get similar movies
const similar = await apiClient.getSimilarMovies(550);

// Filter movies
const filtered = await apiClient.filterMovies({ genres: ["Action"], min_year: 2020 });

// Get trending movies
const trending = await apiClient.getTrending();
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` |
| `NEXT_PUBLIC_DEBUG` | Enable debug mode | `false` |

## Features

- ✅ Next.js 14 with App Router
- ✅ TypeScript with strict mode
- ✅ TailwindCSS 4.x
- ✅ ShadCN UI utilities
- ✅ API client with error handling
- ✅ Type-safe API responses
- ✅ Environment configuration
- ✅ ESLint + TypeScript linting
- ✅ TMDB image optimization

## Next Steps

Module 4.2 will add:
- Search interface with debouncing
- Movie cards and results display
- Loading states and error handling
- Advanced filters UI
- Movie detail pages
