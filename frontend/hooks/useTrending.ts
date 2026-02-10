import { useCallback, useEffect, useRef, useState } from "react";
import apiClient, { APIError } from "@/lib/api-client";
import { Movie, TrendingMoviesResponse } from "@/types/api";

interface UseTrendingResult {
  movies: Movie[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Custom hook to fetch trending movies
 *
 * @param limit - Number of movies to fetch (default: 20)
 * @returns Trending movies data, loading state, error, and refetch function
 */
export function useTrending(limit = 20): UseTrendingResult {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const isMounted = useRef(true);

  useEffect(() => {
    return () => {
      isMounted.current = false;
    };
  }, []);

  const fetchTrending = useCallback(async () => {
    if (!isMounted.current) return;
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.getTrending(0, limit) as TrendingMoviesResponse;
      if (!isMounted.current) return;
      setMovies(response.movies);
    } catch (err) {
      if (!isMounted.current) return;
      console.error("Error fetching trending movies:", err);
      if (err instanceof APIError) {
        setError(new Error(`Failed to fetch trending movies: ${err.message}`));
      } else {
        setError(new Error("Failed to fetch trending movies"));
      }
      setMovies([]);
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, [limit]);

  useEffect(() => {
    fetchTrending();
  }, [fetchTrending]);

  return {
    movies,
    isLoading,
    error,
    refetch: fetchTrending,
  };
}
