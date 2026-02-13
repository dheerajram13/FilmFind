"use client";

import { useCallback, useEffect, useState, useMemo } from "react";
import { Film, Sparkles, TrendingUp, Zap } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { FilterPanel } from "@/components/filters/FilterPanel";
import { SearchBar } from "@/components/search/SearchBar";
import { StickySearchBar } from "@/components/search/StickySearchBar";
import { SearchResults } from "@/components/search/SearchResults";
import { MovieCard } from "@/components/movie/MovieCard";
import { CarouselSkeleton } from "@/components/discovery/CarouselSkeleton";
import { useTrending } from "@/hooks/useTrending";
import apiClient, { APIError } from "@/lib/api-client";
import { useFilters } from "@/lib/filter-context";
import { MovieSearchResult, QueryInterpretation, SearchFilters, SearchResponse } from "@/types/api";

export default function Home() {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [results, setResults] = useState<MovieSearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [queryInterpretation, setQueryInterpretation] = useState<QueryInterpretation | undefined>(
    undefined
  );
  const [isFilterOpen, setIsFilterOpen] = useState(false);

  const { filters } = useFilters();

  // Fetch trending movies
  const { movies: trendingMovies, isLoading: isTrendingLoading } = useTrending(60);

  const activeFilterCount = useMemo(() => {
    return Object.entries(filters).reduce((count, [key, value]) => {
      if (key === "include_adult") return count;
      if (Array.isArray(value)) return value.length > 0 ? count + 1 : count;
      if (value === undefined || value === null) return count;
      return count + 1;
    }, 0);
  }, [filters]);

  // Perform search
  const performSearch = useCallback(async (searchQuery: string, activeFilters: SearchFilters) => {
    if (!searchQuery.trim()) {
      setResults([]);
      setError(null);
      setQueryInterpretation(undefined);
      return;
    }

    if (searchQuery.trim().length < 3) {
      setResults([]);
      setError(null);
      setQueryInterpretation(undefined);
      return;
    }

    setIsLoading(true);
    setError(null);
    setQueryInterpretation(undefined);

    try {
      const response = await apiClient.search(searchQuery, activeFilters, 30) as SearchResponse;
      setResults(response.results);
      setQueryInterpretation(response.query_interpretation);
    } catch (err) {
      console.error("Search error:", err);
      if (err instanceof APIError) {
        setError(new Error(`Search failed: ${err.message}`));
      } else {
        setError(new Error("Failed to search movies. Please try again."));
      }
      setResults([]);
      setQueryInterpretation(undefined);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Trigger search only when submittedQuery changes
  useEffect(() => {
    performSearch(submittedQuery, filters);
  }, [submittedQuery, filters, performSearch]);

  // Handle search submission (Enter key or Search button click)
  const handleSearch = useCallback(() => {
    setSubmittedQuery(query);
  }, [query]);

  const handleRetry = useCallback(() => {
    performSearch(submittedQuery, filters);
  }, [performSearch, submittedQuery, filters]);

  const hasSearchQuery = submittedQuery.trim().length > 0;

  useEffect(() => {
    if (!hasSearchQuery && isFilterOpen) {
      setIsFilterOpen(false);
    }
  }, [hasSearchQuery, isFilterOpen]);

  // Organize trending movies into sections
  const trendingSections = useMemo(() => {
    if (!trendingMovies || trendingMovies.length === 0) {
      return {
        trendingNow: [],
        aiPicks: [],
      };
    }

    const trendingNow = [...trendingMovies]
      .sort((a, b) => (b.popularity || 0) - (a.popularity || 0))
      .slice(0, 6);

    const aiPicks = [...trendingMovies]
      .filter((m) => (m.vote_count || 0) > 50)
      .sort((a, b) => (b.vote_average || 0) - (a.vote_average || 0))
      .slice(0, 4);

    return {
      trendingNow,
      aiPicks,
    };
  }, [trendingMovies]);

  return (
    <div className="min-h-screen w-full bg-black text-white overflow-x-hidden">
      {/* Ambient background gradients */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <motion.div
          animate={{
            opacity: [0.04, 0.08, 0.04],
            scale: [1, 1.06, 1],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="absolute top-16 left-1/4 w-72 h-72 bg-purple-600/12 rounded-full blur-[120px]"
        />
        <motion.div
          animate={{
            opacity: [0.04, 0.08, 0.04],
            scale: [1, 1.06, 1],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 1
          }}
          className="absolute bottom-0 right-1/4 w-72 h-72 bg-blue-600/12 rounded-full blur-[120px]"
        />
      </div>

      {/* Content */}
      <div className="relative z-10">
        {/* Header */}
        <AnimatePresence mode="wait">
          {!hasSearchQuery && (
            <motion.header
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="border-b border-zinc-800/60 backdrop-blur-xl bg-black/60"
            >
              <div className="max-w-7xl mx-auto px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Film className="w-8 h-8 text-purple-500" />
                    <div>
                      <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
                        FilmFind
                      </h1>
                      <p className="text-xs text-zinc-500">AI-Powered Discovery</p>
                    </div>
                  </div>

                  <nav className="flex items-center gap-6">
                    <a href="#" className="text-zinc-400 hover:text-white transition-colors duration-200">Browse</a>
                    <a href="#" className="text-zinc-400 hover:text-white transition-colors duration-200">Trending</a>
                    <a href="#" className="text-zinc-400 hover:text-white transition-colors duration-200">My List</a>
                  </nav>
                </div>
              </div>
            </motion.header>
          )}
        </AnimatePresence>

        {/* Sticky Search Bar - Only when showing results */}
        <AnimatePresence>
          {hasSearchQuery && (
            <StickySearchBar
              value={query}
              onChange={setQuery}
              onSearch={handleSearch}
              isLoading={isLoading}
              onFilterClick={() => setIsFilterOpen((prev) => !prev)}
              filterCount={activeFilterCount}
            />
          )}
        </AnimatePresence>

        {/* Main Content */}
        <main>
          <AnimatePresence mode="wait">
            {!hasSearchQuery ? (
              /* Browse View - Figma design */
              <motion.div
                key="browse"
                initial={{ opacity: 1 }}
                exit={{ opacity: 0, y: -50 }}
                transition={{ duration: 0.4 }}
              >
                {/* Hero Section */}
                <section className="pt-20 pb-16">
                  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.6 }}
                      className="mb-8"
                    >
                      <motion.div
                        animate={{ rotate: [0, 360] }}
                        transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                        className="inline-block mb-6"
                      >
                        <Sparkles className="w-12 h-12 text-purple-400" />
                      </motion.div>

                      <h2 className="text-6xl font-bold mb-4 bg-gradient-to-r from-white via-purple-200 to-blue-200 bg-clip-text text-transparent">
                        Discover Your Next
                        <br />
                        Favorite Film
                      </h2>
                      <p className="text-xl text-zinc-400 max-w-2xl mx-auto">
                        Harness the power of AI to find movies and shows that match your exact mood,
                        vibe, and preferences with natural language search.
                      </p>
                    </motion.div>

                    <SearchBar
                      value={query}
                      onChange={setQuery}
                      onSearch={handleSearch}
                      isLoading={isLoading}
                    />
                  </div>
                </section>

                {/* Trending Section */}
                <section className="py-16">
                  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.5 }}
                      className="flex items-center gap-3 mb-8"
                    >
                      <TrendingUp className="w-6 h-6 text-orange-500" />
                      <h3 className="text-3xl font-bold">Trending Now</h3>
                    </motion.div>

                    {isTrendingLoading ? (
                      <CarouselSkeleton />
                    ) : (
                      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
                        {trendingSections.trendingNow.map((movie, index) => (
                          <MovieCard key={movie.id} movie={movie} priority={index < 6} />
                        ))}
                      </div>
                    )}
                  </div>
                </section>

                {/* AI Recommendations Section */}
                <section className="py-16">
                  <div className="max-w-7xl mx-auto px-6">
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.5 }}
                      className="flex items-center gap-3 mb-8"
                    >
                      <Zap className="w-6 h-6 text-purple-500" />
                      <h3 className="text-3xl font-bold">AI Picks For You</h3>
                      <span className="text-sm text-zinc-500 bg-zinc-900/50 px-3 py-1 rounded-full border border-zinc-800">
                        Personalized
                      </span>
                    </motion.div>

                    {isTrendingLoading ? (
                      <CarouselSkeleton />
                    ) : (
                      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                        {trendingSections.aiPicks.map((movie, index) => (
                          <MovieCard key={movie.id} movie={movie} priority={index < 4} />
                        ))}
                      </div>
                    )}
                  </div>
                </section>
              </motion.div>
            ) : (
              /* Search Results View */
              <motion.div
                key="results"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.4 }}
                className="min-h-[calc(100vh-80px)] px-6 py-8"
              >
                <FilterPanel
                  isOpen={isFilterOpen}
                  onClose={() => setIsFilterOpen(false)}
                />
                <div className="max-w-7xl mx-auto">
                  <SearchResults
                    query={submittedQuery}
                    results={results}
                    isLoading={isLoading}
                    error={error}
                    onRetry={handleRetry}
                    queryInterpretation={queryInterpretation}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </main>

        {/* Footer */}
        <footer className="border-t border-zinc-900/60 py-10 mt-16">
          <div className="max-w-7xl mx-auto px-6 text-center text-zinc-500">
            <p className="flex items-center justify-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-purple-500" />
              <span>Powered by advanced AI & semantic search technology</span>
            </p>
            <p className="text-sm">© {new Date().getFullYear()} FilmFind. Discover intelligently.</p>
          </div>
        </footer>
      </div>
    </div>
  );
}
