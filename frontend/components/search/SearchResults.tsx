"use client";

import { MovieGridSkeleton } from "@/components/movie/MovieCardSkeleton";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { MovieSearchResult, QueryInterpretation } from "@/types/api";
import { cn } from "@/lib/utils";
import { SearchResultCard } from "@/components/search/SearchResultCard";

interface SearchResultsProps {
  results: MovieSearchResult[];
  isLoading: boolean;
  error: Error | null;
  query: string;
  onRetry?: () => void;
  showScore?: boolean;
  queryInterpretation?: QueryInterpretation;
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
  queryInterpretation,
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
    <div className={cn("space-y-8", className)}>
      {/* Results header */}
      <div className="px-2 sm:px-0">
        <h3 className="mb-2 text-2xl font-bold text-white">Search Results</h3>
        <p className="text-zinc-400">
          Found{" "}
          <span className="font-semibold text-purple-400">{results.length}</span>{" "}
          {results.length === 1 ? "match" : "matches"}{" "}
          {query && (
            <>
              for <span className="font-semibold text-white">&quot;{query}&quot;</span>
            </>
          )}
        </p>
      </div>

      {/* Results grid */}
      <div className="grid grid-cols-2 gap-6 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        {results.map((movie, index) => (
          <SearchResultCard
            key={movie.id}
            movie={movie}
            query={query}
            queryInterpretation={queryInterpretation}
            index={index}
            showScore={showScore}
          />
        ))}
      </div>
    </div>
  );
}
