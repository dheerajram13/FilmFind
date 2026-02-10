"use client";

import { useCallback, useEffect, useState, useMemo } from "react";
import { Film, Search as SearchIcon } from "lucide-react";
import { SearchBar } from "@/components/search/SearchBar";
import { SearchResults } from "@/components/search/SearchResults";
import { MovieCarousel } from "@/components/discovery/MovieCarousel";
import { HeroBanner } from "@/components/discovery/HeroBanner";
import { CarouselSkeleton } from "@/components/discovery/CarouselSkeleton";
import { useDebounce } from "@/hooks/useDebounce";
import { useTrending } from "@/hooks/useTrending";
import apiClient, { APIError } from "@/lib/api-client";
import { MovieSearchResult, SearchResponse } from "@/types/api";
import { cn } from "@/lib/utils";

export default function Home() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MovieSearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [isSearchFocused, setIsSearchFocused] = useState(false);

  const debouncedQuery = useDebounce(query, 300);

  // Fetch trending movies - we'll use this for all sections
  const { movies: trendingMovies, isLoading: isTrendingLoading, error: trendingError } = useTrending(60);

  // Perform search
  const performSearch = useCallback(async (searchQuery: string) => {
    // Clear results if query is empty
    if (!searchQuery.trim()) {
      setResults([]);
      setError(null);
      return;
    }

    // Validate minimum query length (backend requires 3 characters)
    if (searchQuery.trim().length < 3) {
      setResults([]);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.search(searchQuery, undefined, 30) as SearchResponse;
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
    performSearch(debouncedQuery);
  }, [debouncedQuery, performSearch]);

  const handleRetry = useCallback(() => {
    performSearch(debouncedQuery);
  }, [performSearch, debouncedQuery]);

  const hasSearchQuery = debouncedQuery.trim().length > 0;

  // Organize trending movies into different sections
  const trendingSections = useMemo(() => {
    if (!trendingMovies || trendingMovies.length === 0) {
      return {
        hero: null,
        trendingNow: [],
        topRated: [],
        recentReleases: [],
      };
    }

    // Featured movie for hero (first trending)
    const hero = trendingMovies[0];

    // Trending Now (highest popularity)
    const trendingNow = [...trendingMovies]
      .sort((a, b) => (b.popularity || 0) - (a.popularity || 0))
      .slice(0, 20);

    // Top Rated (highest rating with minimum votes)
    const topRated = [...trendingMovies]
      .filter((m) => (m.vote_count || 0) > 100)
      .sort((a, b) => (b.vote_average || 0) - (a.vote_average || 0))
      .slice(0, 20);

    // Recent Releases (most recent release dates)
    const recentReleases = [...trendingMovies]
      .filter((m) => m.release_date)
      .sort((a, b) => {
        const dateA = new Date(a.release_date!).getTime();
        const dateB = new Date(b.release_date!).getTime();
        return dateB - dateA;
      })
      .slice(0, 20);

    return {
      hero,
      trendingNow,
      topRated,
      recentReleases,
    };
  }, [trendingMovies]);

  return (
    <div className={cn(
      "min-h-screen transition-colors duration-700 ease-in-out",
      isSearchFocused ? "bg-gradient-to-br from-black via-zinc-950 to-black" : "bg-black"
    )}>
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-gradient-to-b from-black via-black/95 to-transparent">
        <div className="container mx-auto flex items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-red-600 to-red-700">
              <Film className="h-6 w-6 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-red-600">FilmFind</h1>
          </div>

          {/* Search Bar in Header (when scrolled or searching) */}
          {hasSearchQuery && (
            <div className="hidden flex-1 max-w-2xl md:block">
              <SearchBar
                value={query}
                onChange={setQuery}
                isLoading={isLoading}
                placeholder="Search movies..."
              />
            </div>
          )}

          {/* Search Icon Button (mobile) */}
          {!hasSearchQuery && (
            <button
              onClick={() => document.getElementById("main-search")?.focus()}
              className="rounded-full bg-zinc-900 p-2 text-white hover:bg-zinc-800 md:hidden"
            >
              <SearchIcon size={20} />
            </button>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="pt-16">
        {hasSearchQuery ? (
          /* Search Results View */
          <div className="container mx-auto px-4 py-12 sm:px-6 lg:px-8">
            {/* Mobile Search Bar */}
            <div className="mb-8 md:hidden">
              <SearchBar
                value={query}
                onChange={setQuery}
                isLoading={isLoading}
                placeholder="Search movies..."
              />
            </div>

            <SearchResults
              query={debouncedQuery}
              results={results}
              isLoading={isLoading}
              error={error}
              onRetry={handleRetry}
            />
          </div>
        ) : (
          /* Browse View with Centered Search */
          <>
            {/* Centered Search Section */}
            <section className="relative flex min-h-[60vh] items-center justify-center px-4 py-20 sm:px-6 lg:px-8">
              <div className="container mx-auto">
                <div className="mx-auto max-w-3xl space-y-10 text-center">
                  {/* Logo & Title */}
                  <div className="space-y-4">
                    <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-red-600 to-red-700 shadow-2xl shadow-red-500/20">
                      <Film className="h-10 w-10 text-white" />
                    </div>
                    <div>
                      <h1 className="text-5xl font-bold text-white sm:text-6xl">
                        FilmFind
                      </h1>
                      <p className="mt-3 text-lg text-zinc-400">
                        Discover your next favorite movie with AI-powered search
                      </p>
                    </div>
                  </div>

                  {/* Search Bar */}
                  <div className="flex justify-center" onFocus={() => setIsSearchFocused(true)} onBlur={() => setIsSearchFocused(false)}>
                    <SearchBar
                      id="main-search"
                      value={query}
                      onChange={setQuery}
                      isLoading={isLoading}
                      placeholder="Search for movies, shows, or actors..."
                    />
                  </div>

                  {/* Quick Search Examples */}
                  <div className="flex flex-wrap items-center justify-center gap-2">
                    <span className="text-sm text-zinc-500">Try:</span>
                    {["Sci-fi thriller", "Action movies", "Tom Hanks"].map((example) => (
                      <button
                        key={example}
                        onClick={() => setQuery(example)}
                        className="rounded-full bg-zinc-900/50 px-4 py-1.5 text-sm text-zinc-400 transition-all hover:bg-zinc-800 hover:text-white"
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </section>

            {/* Movie Carousels */}
            <section className="space-y-12 px-4 pb-20 pt-12 sm:px-6 lg:px-8">
              {isTrendingLoading ? (
                <>
                  <CarouselSkeleton />
                  <CarouselSkeleton />
                  <CarouselSkeleton />
                </>
              ) : (
                <>
                  {/* Trending Now */}
                  {trendingSections.trendingNow.length > 0 && (
                    <MovieCarousel
                      title="Trending Now"
                      movies={trendingSections.trendingNow}
                    />
                  )}

                  {/* Top Rated */}
                  {trendingSections.topRated.length > 0 && (
                    <MovieCarousel
                      title="Top Rated"
                      movies={trendingSections.topRated}
                    />
                  )}

                  {/* Recent Releases */}
                  {trendingSections.recentReleases.length > 0 && (
                    <MovieCarousel
                      title="New Releases"
                      movies={trendingSections.recentReleases}
                    />
                  )}
                </>
              )}
            </section>
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-900 bg-black py-12">
        <div className="container mx-auto px-4 text-center text-sm text-zinc-500 sm:px-6 lg:px-8">
          <p>© {new Date().getFullYear()} FilmFind. Powered by AI & TMDB.</p>
        </div>
      </footer>
    </div>
  );
}
