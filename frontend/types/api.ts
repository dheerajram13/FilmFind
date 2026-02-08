/**
 * Type definitions for FilmFind API
 *
 * These types match the Pydantic schemas from the backend.
 */

/**
 * Genre schema
 */
export interface Genre {
  id: number;
  name: string;
}

/**
 * Keyword schema
 */
export interface Keyword {
  id: number;
  name: string;
}

/**
 * Cast member schema
 */
export interface CastMember {
  id: number;
  name: string;
  character_name: string | null;
  profile_path: string | null;
}

/**
 * Movie response schema
 */
export interface Movie {
  id: number;
  tmdb_id: number;
  title: string;
  original_title?: string | null;
  overview: string | null;
  release_date: string | null;
  poster_path: string | null;
  backdrop_path: string | null;
  genres: Genre[];
  keywords?: Keyword[];
  cast_members?: CastMember[];
  vote_average: number;
  vote_count: number;
  popularity: number;
  runtime: number | null;
  original_language: string;
  tagline: string | null;
  streaming_providers?: Record<string, unknown> | null;
}

/**
 * Movie search result with similarity score
 */
export interface MovieSearchResult extends Movie {
  similarity_score?: number;
  final_score?: number;
}

/**
 * Search request schema
 */
export interface SearchRequest {
  query: string;
  filters?: SearchFilters;
  limit?: number;
}

/**
 * Search filters schema
 */
export interface SearchFilters {
  genres?: string[];
  min_year?: number;
  max_year?: number;
  min_rating?: number;
  max_rating?: number;
  languages?: string[];
  min_runtime?: number;
  max_runtime?: number;
  include_adult?: boolean;
}

/**
 * Query interpretation response
 */
export interface QueryInterpretation {
  semantic_query: string;
  intent?: string;
  reference_titles?: string[];
  genres?: string[];
  tones?: string[];
  emotions?: string[];
  themes?: string[];
  undesired_genres?: string[];
  undesired_tones?: string[];
  undesired_emotions?: string[];
  filters_applied?: Record<string, unknown>;
}

/**
 * Search response schema
 */
export interface SearchResponse {
  query: string;
  results: MovieSearchResult[];
  total: number;
  query_interpretation?: QueryInterpretation;
}

/**
 * Similar movies response
 */
export interface SimilarMoviesResponse {
  reference_movie: Movie;
  similar_movies: MovieSearchResult[];
  total: number;
}

/**
 * Filter movies response
 */
export interface FilterMoviesResponse {
  movies: Movie[];
  total: number;
  filters_applied: Record<string, unknown>;
}

/**
 * Trending movies response
 */
export interface TrendingMoviesResponse {
  movies: Movie[];
  total: number;
}

/**
 * Health check response
 */
export interface HealthCheckResponse {
  status: string;
  timestamp: string;
  version: string;
}

/**
 * API Error response
 */
export interface APIErrorResponse {
  detail: string;
  error_code?: string;
  error_type?: string;
}
