"use client";

import { useMemo, useState } from "react";
import {
  CONTENT_TYPE_OPTIONS,
  GENRE_OPTIONS,
  MIN_RATING_DEFAULT,
  MIN_YEAR_DEFAULT,
  STREAMING_OPTIONS,
} from "@/lib/constants";
import { getProviderNames, normalizeProviderName } from "@/lib/streaming-providers";
import { parseYear } from "@/lib/movie-formatters";
import type { MovieSearchResult } from "@/types/api";

export interface UseFiltersReturn {
  selectedStreaming: string[];
  selectedGenres: string[];
  selectedContentTypes: string[];
  minRating: number;
  minYear: number;
  toggleStreaming: (service: string) => void;
  toggleGenre: (genre: string) => void;
  toggleContentType: (ct: string) => void;
  setMinRating: (value: number) => void;
  setMinYear: (value: number) => void;
  clearFilters: () => void;
  filteredResults: MovieSearchResult[];
}

export function useFilters(results: MovieSearchResult[]): UseFiltersReturn {
  const [selectedStreaming, setSelectedStreaming] = useState<string[]>([...STREAMING_OPTIONS]);
  const [selectedGenres, setSelectedGenres] = useState<string[]>([...GENRE_OPTIONS]);
  const [selectedContentTypes, setSelectedContentTypes] = useState<string[]>([
    ...CONTENT_TYPE_OPTIONS,
  ]);
  const [minRating, setMinRating] = useState(MIN_RATING_DEFAULT);
  const [minYear, setMinYear] = useState(MIN_YEAR_DEFAULT);

  const filteredResults = useMemo(() => {
    return results.filter((movie) => {
      const year = parseYear(movie.release_date);
      const movieGenres = movie.genres.map((g) => g.name.toLowerCase());
      const providerNames = getProviderNames(movie).map(normalizeProviderName);

      const ratingMatches = (movie.vote_average ?? 0) >= minRating;
      const yearMatches = year === null || year >= minYear;
      const genreMatches =
        selectedGenres.length === 0 ||
        selectedGenres.some((g) => movieGenres.includes(g.toLowerCase()));
      const streamingMatches =
        selectedStreaming.length === 0 ||
        providerNames.length === 0 ||
        selectedStreaming.some((s) => providerNames.includes(normalizeProviderName(s)));

      return ratingMatches && yearMatches && genreMatches && streamingMatches;
    });
  }, [minRating, minYear, results, selectedGenres, selectedStreaming]);

  const toggleStreaming = (service: string): void => {
    setSelectedStreaming((current) =>
      current.includes(service) ? current.filter((s) => s !== service) : [...current, service]
    );
  };

  const toggleGenre = (genre: string): void => {
    setSelectedGenres((current) =>
      current.includes(genre) ? current.filter((g) => g !== genre) : [...current, genre]
    );
  };

  const toggleContentType = (ct: string): void => {
    setSelectedContentTypes((current) =>
      current.includes(ct) ? current.filter((c) => c !== ct) : [...current, ct]
    );
  };

  const clearFilters = (): void => {
    setSelectedStreaming([...STREAMING_OPTIONS]);
    setSelectedGenres([...GENRE_OPTIONS]);
    setSelectedContentTypes([...CONTENT_TYPE_OPTIONS]);
    setMinRating(MIN_RATING_DEFAULT);
    setMinYear(MIN_YEAR_DEFAULT);
  };

  return {
    selectedStreaming,
    selectedGenres,
    selectedContentTypes,
    minRating,
    minYear,
    toggleStreaming,
    toggleGenre,
    toggleContentType,
    setMinRating,
    setMinYear,
    clearFilters,
    filteredResults,
  };
}
