"use client";

import { MovieCard } from "./MovieCard";
import { MovieGridSkeleton } from "./MovieCardSkeleton";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
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

  // No results
  if (results.length === 0) {
    return <EmptyState type="no-results" query={query} className={className} />;
  }

  // Results grid
  return (
    <div className={cn("space-y-4", className)}>
      {/* Results count */}
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Found <strong>{results.length}</strong> {results.length === 1 ? "movie" : "movies"}
        {query && (
          <>
            {" "}
            for <strong>&quot;{query}&quot;</strong>
          </>
        )}
      </div>

      {/* Results grid */}
      <div className="grid gap-6 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
        {results.map((movie) => (
          <MovieCard key={movie.id} movie={movie} showScore={showScore} />
        ))}
      </div>
    </div>
  );
}
