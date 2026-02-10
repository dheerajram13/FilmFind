"use client";

import { MovieCard } from "@/components/movie/MovieCard";
import { MovieGridSkeleton } from "@/components/movie/MovieCardSkeleton";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { MovieSearchResult } from "@/types/api";
import { cn } from "@/lib/utils";

interface SearchResultsProps {
  results: MovieSearchResult[];
  isLoading: boolean;
  error: Error | null;
  query: string;
  onRetry?: () => void;
  showScore?: boolean;
  className?: string;
}

/**
 * SearchResults component displays search results in a grid
 *
 * Features:
 * - Grid layout (responsive columns)
 * - Loading state with skeletons
 * - Empty state when no results
 * - Error state with retry
 * - Shows similarity/final scores
 */
export function SearchResults({
  results,
  isLoading,
  error,
  query,
  onRetry,
  showScore = true,
  className,
}: SearchResultsProps) {
  // Loading state
  if (isLoading) {
    return <MovieGridSkeleton count={12} className={className} />;
  }

  // Error state
  if (error) {
    return <ErrorState error={error} onRetry={onRetry} className={className} />;
  }

  // No search query yet
  if (!query.trim()) {
    return <EmptyState type="start-search" className={className} />;
  }

  // Query too short (minimum 3 characters required)
  if (query.trim().length < 3) {
    return (
      <div className={cn("flex items-center justify-center py-20", className)}>
        <div className="text-center">
          <p className="text-lg text-zinc-400">
            Type at least <span className="font-semibold text-white">3 characters</span> to search
          </p>
        </div>
      </div>
    );
  }

  // No results
  if (results.length === 0) {
    return <EmptyState type="no-results" query={query} className={className} />;
  }

  // Results grid
  return (
    <div className={cn("space-y-6", className)}>
      {/* Results count */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 text-sm text-zinc-400 sm:px-6 lg:px-8">
        <p>
          Found <span className="font-semibold text-white">{results.length}</span>{" "}
          {results.length === 1 ? "movie" : "movies"}
          {query && (
            <>
              {" "}
              for <span className="font-semibold text-white">&quot;{query}&quot;</span>
            </>
          )}
        </p>
        <span className="rounded-full border border-zinc-800 bg-zinc-900 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-zinc-400">
          Sorted by relevance
        </span>
      </div>

      {/* Results grid - matching carousel card sizes */}
      <div className="flex flex-wrap gap-3 px-4 sm:gap-4 sm:px-6 lg:px-8">
        {results.map((movie) => (
          <div
            key={movie.id}
            className="w-[160px] sm:w-[200px] md:w-[220px] lg:w-[240px]"
          >
            <MovieCard movie={movie} showScore={showScore} />
          </div>
        ))}
      </div>
    </div>
  );
}
