/**
 * API Client for FilmFind Backend
 *
 * Provides type-safe API calls to the FastAPI backend.
 * Handles errors, retries, and response transformation.
 */

import {
  FilterMoviesResponse,
  HealthCheckResponse,
  Movie,
  SearchFilters,
  SearchResponse,
  SimilarMoviesResponse,
  TrendingMoviesResponse,
} from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_PREFIX = "/api";

/**
 * Custom error class for API errors
 */
export class APIError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string
  ) {
    super(message);
    this.name = "APIError";
  }
}

/**
 * Generic fetch wrapper with error handling
 */
async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${API_PREFIX}${endpoint}`;

  const defaultHeaders = {
    "Content-Type": "application/json",
  };

  const config: RequestInit = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage =
        (typeof errorData.error === "string" && errorData.error) ||
        (typeof errorData.detail === "string" && errorData.detail) ||
        `API Error: ${response.statusText}`;
      throw new APIError(
        response.status,
        response.statusText,
        errorMessage
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new Error(`Network error: ${error instanceof Error ? error.message : "Unknown error"}`);
  }
}

/**
 * API client object with methods for all endpoints
 */
export const apiClient = {
  /**
   * Search for movies using natural language
   */
  search: async (
    query: string,
    filters?: SearchFilters,
    limit = 10
  ): Promise<SearchResponse> => {
    const cleanFilters = filters
      ? Object.fromEntries(
          Object.entries(filters).filter(([, value]) => value !== undefined)
        )
      : undefined;

    return fetchAPI<SearchResponse>("/search", {
      method: "POST",
      body: JSON.stringify({ query, filters: cleanFilters, limit }),
    });
  },

  /**
   * Get movie details by ID
   */
  getMovie: async (movieId: number): Promise<Movie> => {
    return fetchAPI<Movie>(`/movie/${movieId}`, {
      method: "GET",
    });
  },

  /**
   * Get similar movies
   */
  getSimilarMovies: async (
    movieId: number,
    skip = 0,
    limit = 10
  ): Promise<SimilarMoviesResponse> => {
    return fetchAPI<SimilarMoviesResponse>(
      `/movie/similar/${movieId}?skip=${skip}&limit=${limit}`,
      {
        method: "GET",
      }
    );
  },

  /**
   * Filter movies by criteria
   */
  filterMovies: async (
    filters: SearchFilters,
    skip = 0,
    limit = 20
  ): Promise<FilterMoviesResponse> => {
    const cleanFilters = Object.fromEntries(
      Object.entries(filters).filter(([, value]) => value !== undefined)
    );
    return fetchAPI<FilterMoviesResponse>(`/filter?skip=${skip}&limit=${limit}`, {
      method: "POST",
      body: JSON.stringify(cleanFilters),
    });
  },

  /**
   * Get trending movies
   */
  getTrending: async (skip = 0, limit = 20): Promise<TrendingMoviesResponse> => {
    return fetchAPI<TrendingMoviesResponse>(`/trending?skip=${skip}&limit=${limit}`, {
      method: "GET",
    });
  },

  /**
   * Health check
   */
  healthCheck: async (): Promise<HealthCheckResponse> => {
    return fetchAPI<HealthCheckResponse>("/health", {
      method: "GET",
    });
  },
};

export default apiClient;
