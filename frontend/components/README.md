# FilmFind Components

UI components for the FilmFind search interface.

## Core Components

### SearchBar
**File**: `SearchBar.tsx`

Search input component with clear functionality and keyboard support.

**Features**:
- Search icon indicator
- Clear button (shown when query is not empty)
- Keyboard support (Escape to clear)
- Accessible with ARIA labels
- Dark mode support
- Focus states with ring

**Props**:
```typescript
{
  onSearch: (query: string) => void;  // Callback when query changes
  placeholder?: string;                // Custom placeholder text
  className?: string;                  // Additional CSS classes
  autoFocus?: boolean;                 // Auto-focus on mount
}
```

**Usage**:
```tsx
<SearchBar
  onSearch={setQuery}
  placeholder="Search for movies..."
  autoFocus
/>
```

---

### MovieCard
**File**: `MovieCard.tsx`

Displays a movie with poster, title, rating, and metadata.

**Features**:
- TMDB poster image with Next.js Image optimization
- Fallback for missing posters (🎬 emoji)
- Rating with star icon
- Release year with calendar icon
- Genres as badges (max 3 shown)
- Optional similarity/final score badge
- Hover effects (scale + shadow)
- Click to navigate to movie detail page
- Responsive aspect ratio (2:3)
- Dark mode support

**Props**:
```typescript
{
  movie: Movie | MovieSearchResult;  // Movie data
  className?: string;                 // Additional CSS classes
  showScore?: boolean;                // Show similarity score badge
}
```

**Usage**:
```tsx
<MovieCard
  movie={movieData}
  showScore={true}
/>
```

---

### SearchResults
**File**: `SearchResults.tsx`

Displays search results in a responsive grid with loading, error, and empty states.

**Features**:
- Responsive grid layout (2-6 columns based on screen size)
- Results count display
- Loading state with skeletons
- Empty state when no query
- No results state with search tips
- Error state with retry button
- Shows similarity scores

**Props**:
```typescript
{
  results: MovieSearchResult[];  // Array of movie results
  isLoading: boolean;            // Loading state
  error: Error | null;           // Error object
  query: string;                 // Current search query
  onRetry?: () => void;          // Retry callback
  showScore?: boolean;           // Show scores on cards
  className?: string;            // Additional CSS classes
}
```

**Usage**:
```tsx
<SearchResults
  results={movies}
  isLoading={isLoading}
  error={error}
  query={searchQuery}
  onRetry={handleRetry}
  showScore
/>
```

---

## Loading States

### MovieCardSkeleton
**File**: `MovieCardSkeleton.tsx`

Animated loading skeleton matching MovieCard layout.

**Features**:
- Pulse animation
- Matches MovieCard dimensions
- Dark mode support

**Usage**:
```tsx
<MovieCardSkeleton />
```

---

### MovieGridSkeleton
**File**: `MovieCardSkeleton.tsx`

Grid of loading skeletons.

**Props**:
```typescript
{
  count?: number;      // Number of skeletons (default: 12)
  className?: string;  // Additional CSS classes
}
```

**Usage**:
```tsx
<MovieGridSkeleton count={20} />
```

---

## Empty & Error States

### EmptyState
**File**: `EmptyState.tsx`

Displays empty states with helpful guidance.

**Types**:
- `"start-search"`: Initial state before searching
- `"no-results"`: No movies found for query

**Features**:
- Icon indicators
- Contextual messaging
- Search tips for no results
- Example queries for initial state
- Dark mode support

**Props**:
```typescript
{
  type?: "no-results" | "start-search";
  query?: string;      // Search query (for no-results type)
  className?: string;
}
```

**Usage**:
```tsx
// Initial state
<EmptyState type="start-search" />

// No results
<EmptyState type="no-results" query="nonexistent movie" />
```

---

### ErrorState
**File**: `ErrorState.tsx`

Displays errors with optional retry functionality.

**Features**:
- Error icon
- Error message display
- Optional retry button
- Accessible (role="alert", aria-live)
- Dark mode support

**Props**:
```typescript
{
  error: Error | string;   // Error object or message
  onRetry?: () => void;    // Optional retry callback
  className?: string;
}
```

**Usage**:
```tsx
<ErrorState
  error={error}
  onRetry={handleRetry}
/>
```

---

## Hooks

### useDebounce
**File**: `hooks/useDebounce.ts`

Custom hook for debouncing values (e.g., search input).

**Parameters**:
- `value: T` - The value to debounce
- `delay?: number` - Delay in milliseconds (default: 300)

**Returns**: Debounced value

**Usage**:
```tsx
const [query, setQuery] = useState("");
const debouncedQuery = useDebounce(query, 300);

useEffect(() => {
  if (debouncedQuery) {
    performSearch(debouncedQuery);
  }
}, [debouncedQuery]);
```

---

## Design System

### Colors
- **Primary**: Blue (blue-600, blue-500)
- **Secondary**: Purple (purple-600)
- **Accent**: Yellow (yellow-400 for stars)
- **Gray Scale**: gray-50 to gray-950
- **Error**: Red (red-600, red-400)

### Breakpoints
- **sm**: 640px (3 columns)
- **md**: 768px (4 columns)
- **lg**: 1024px (5 columns)
- **xl**: 1280px (6 columns)

### Grid Layout
```css
grid-cols-2           /* Mobile: 2 columns */
sm:grid-cols-3        /* Small: 3 columns */
md:grid-cols-4        /* Medium: 4 columns */
lg:grid-cols-5        /* Large: 5 columns */
xl:grid-cols-6        /* Extra large: 6 columns */
```

### Dark Mode
All components support dark mode via Tailwind's `dark:` variant.

---

## Accessibility

- **Keyboard Navigation**: Full keyboard support
- **ARIA Labels**: Proper labels for screen readers
- **Focus States**: Visible focus indicators
- **Semantic HTML**: Proper heading hierarchy
- **Alt Text**: Image alt attributes
- **Error Announcements**: Live regions for errors
