"use client";

import { useCallback, useEffect, useState } from "react";
import { Filter as FilterIcon } from "lucide-react";
import { SearchBar } from "@/components/SearchBar";
import { SearchResults } from "@/components/SearchResults";
import { FilterPanel } from "@/components/FilterPanel";
import { HeroBanner } from "@/components/HeroBanner";
import { MovieCarousel } from "@/components/MovieCarousel";
import { CarouselSkeleton } from "@/components/CarouselSkeleton";
import { DiscoverySection } from "@/components/DiscoverySection";
import { useDebounce } from "@/hooks/useDebounce";
import { useTrending } from "@/hooks/useTrending";
import { useFilters } from "@/lib/filter-context";
import apiClient, { APIError } from "@/lib/api-client";
import { MovieSearchResult, SearchResponse } from "@/types/api";

export default function Home() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MovieSearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [isFilterOpen, setIsFilterOpen] = useState(false);

  const { filters, hasActiveFilters } = useFilters();
  const debouncedQuery = useDebounce(query, 300);

  // Fetch trending movies for homepage
  const { movies: trendingMovies, isLoading: isTrendingLoading } = useTrending(20);

  const performSearch = useCallback(async (searchQuery: string, searchFilters: typeof filters) => {
    if (!searchQuery.trim()) {
      setResults([]);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Only send non-empty filter values
      const cleanFilters = Object.fromEntries(
        Object.entries(searchFilters).filter(([_, value]) => {
          if (Array.isArray(value)) return value.length > 0;
          return value !== undefined && value !== null;
        })
      );

      const response = await apiClient.search(
        searchQuery,
        Object.keys(cleanFilters).length > 0 ? cleanFilters : undefined,
        20
      ) as SearchResponse;
      setResults(response.results);
    } catch (err) {
      console.error("Search error:", err);
      if (err instanceof APIError) {
        setError(new Error(`Search failed: ${err.message}`));
      } else {
        setError(new Error("Failed to search movies. Please try again."));
      }
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    performSearch(debouncedQuery, filters);
  }, [debouncedQuery, filters, performSearch]);

  const handleRetry = () => {
    performSearch(debouncedQuery, filters);
  };

  const handleApplyFilters = () => {
    // Trigger search with current query and new filters
    if (debouncedQuery.trim()) {
      performSearch(debouncedQuery, filters);
    }
  };

  const handleSearchSuggestion = (suggestion: string) => {
    setQuery(suggestion);
  };

  const hasSearchQuery = debouncedQuery.trim().length > 0;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-950">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center gap-6">
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent sm:text-5xl">
              FilmFind
            </h1>
            <p className="text-center text-gray-600 dark:text-gray-400 max-w-2xl">
              Discover movies using natural language and AI-powered semantic search
            </p>
            <div className="w-full max-w-3xl flex gap-3">
              <SearchBar onSearch={setQuery} autoFocus={false} />
              <button
                onClick={() => setIsFilterOpen(true)}
                className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-blue-700 relative"
              >
                <FilterIcon size={18} />
                <span className="hidden sm:inline">Filters</span>
                {hasActiveFilters && (
                  <span className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-red-500 ring-2 ring-white dark:ring-gray-950" />
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      {hasSearchQuery ? (
        // Search Results
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <SearchResults
            results={results}
            isLoading={isLoading}
            error={error}
            query={debouncedQuery}
            onRetry={handleRetry}
            showScore
          />
        </main>
      ) : (
        // Homepage Discovery
        <main>
          {/* Hero Banner */}
          {!isTrendingLoading && trendingMovies.length > 0 && (
            <HeroBanner movie={trendingMovies[0]} />
          )}

          <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-12">
            {/* Trending Movies */}
            {isTrendingLoading ? (
              <CarouselSkeleton title="Trending Now" />
            ) : trendingMovies.length > 0 ? (
              <MovieCarousel
                title="Trending Now"
                movies={trendingMovies}
              />
            ) : null}

            {/* Discovery Section */}
            <DiscoverySection onSearchSuggestion={handleSearchSuggestion} />

            {/* Popular Movies (subset of trending) */}
            {!isTrendingLoading && trendingMovies.length > 10 && (
              <MovieCarousel
                title="Popular Movies"
                movies={trendingMovies.slice(0, 10)}
              />
            )}
          </div>
        </main>
      )}

      {/* Filter Panel */}
      <FilterPanel
        isOpen={isFilterOpen}
        onClose={() => setIsFilterOpen(false)}
        onApply={handleApplyFilters}
      />
    </div>
  );
}
