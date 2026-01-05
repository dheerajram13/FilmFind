"use client";

import { useCallback, useEffect, useState } from "react";
import { SearchBar } from "@/components/SearchBar";
import { SearchResults } from "@/components/SearchResults";
import { useDebounce } from "@/hooks/useDebounce";
import apiClient, { APIError } from "@/lib/api-client";
import { MovieSearchResult, SearchResponse } from "@/types/api";

export default function Home() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MovieSearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const debouncedQuery = useDebounce(query, 300);

  const performSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.search(searchQuery, undefined, 20) as SearchResponse;
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

  const handleRetry = () => {
    performSearch(debouncedQuery);
  };

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
            <div className="w-full max-w-3xl">
              <SearchBar onSearch={setQuery} autoFocus />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
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
    </div>
  );
}
