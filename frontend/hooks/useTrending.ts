import { useEffect, useState } from "react";
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

  const fetchTrending = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.getTrending(0, limit) as TrendingMoviesResponse;
      setMovies(response.movies);
    } catch (err) {
      console.error("Error fetching trending movies:", err);
      if (err instanceof APIError) {
        setError(new Error(`Failed to fetch trending movies: ${err.message}`));
      } else {
        setError(new Error("Failed to fetch trending movies"));
      }
      setMovies([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTrending();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [limit]);

  return {
    movies,
    isLoading,
    error,
    refetch: fetchTrending,
  };
}
