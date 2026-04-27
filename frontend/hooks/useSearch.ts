"use client";

import { type FormEvent, useRef, useState } from "react";
import apiClient from "@/lib/api-client";
import type { MovieSearchResult } from "@/types/api";

export type ScreenView = "home" | "results" | "detail";

export interface UseSearchReturn {
  query: string;
  setQuery: (q: string) => void;
  submittedQuery: string;
  activeScreen: ScreenView;
  selectedMovie: MovieSearchResult | null;
  results: MovieSearchResult[];
  isSearching: boolean;
  error: string | null;
  runSearch: (nextQuery: string) => Promise<void>;
  handleSubmit: (event: FormEvent<HTMLFormElement>) => void;
  openDetail: (movie: MovieSearchResult) => void;
  backToResults: () => void;
  resetToHome: () => void;
}

export function useSearch(): UseSearchReturn {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [activeScreen, setActiveScreen] = useState<ScreenView>("home");
  const [selectedMovie, setSelectedMovie] = useState<MovieSearchResult | null>(null);
  const [results, setResults] = useState<MovieSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const runSearch = async (nextQuery: string): Promise<void> => {
    const clean = nextQuery.trim();
    if (clean.length < 3) {
      setError("Type at least 3 characters to search.");
      return;
    }

    // Cancel any in-flight search before starting a new one
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setQuery(clean);
    setSubmittedQuery(clean);
    setError(null);
    setIsSearching(true);
    setActiveScreen("results");
    setSelectedMovie(null);

    try {
      const response = await apiClient.search(clean, undefined, 20, controller.signal);
      setResults(response.results);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setResults([]);
      setError(err instanceof Error ? err.message : "Search failed. Please try again.");
    } finally {
      setIsSearching(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    void runSearch(query);
  };

  const openDetail = (movie: MovieSearchResult): void => {
    setSelectedMovie(movie);
    setActiveScreen("detail");
  };

  const backToResults = (): void => {
    setActiveScreen(submittedQuery.length > 0 ? "results" : "home");
  };

  const resetToHome = (): void => {
    setActiveScreen("home");
    setSubmittedQuery("");
    setSelectedMovie(null);
    setResults([]);
    setError(null);
  };

  return {
    query,
    setQuery,
    submittedQuery,
    activeScreen,
    selectedMovie,
    results,
    isSearching,
    error,
    runSearch,
    handleSubmit,
    openDetail,
    backToResults,
    resetToHome,
  };
}
