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
 * Media type enum
 */
export type MediaType = 'movie' | 'tv';

/**
 * Movie response schema (also used for TV shows)
 */
export interface Movie {
  id: number;
  tmdb_id: number;
  media_type: MediaType;
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
  match_explanation?: string | null;
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
  year_min?: number;
  year_max?: number;
  rating_min?: number;
  rating_max?: number;
  runtime_min?: number;
  runtime_max?: number;
  language?: string;
  genres?: string[];
  streaming_providers?: string[];
  exclude_adult?: boolean;
  media_type?: "movie" | "tv_show" | "both";
}

/**
 * Query interpretation response
 */
export interface QueryInterpretation {
  themes?: string[];
  emotions?: string[];
  reference_titles?: string[];
  excluded?: string[];
  tone?: string | null;
  genre_hints?: string[];
  raw_query?: string;
  keywords?: string[];
  plot_elements?: string[];
  tones?: string[];
  intent?: string;
  filters_applied?: Record<string, unknown>;
}

/**
 * Search response schema
 */
export interface SearchResponse {
  query: string;
  results: MovieSearchResult[];
  count: number;
  query_interpretation?: QueryInterpretation;
}

/**
 * Similar movies response
 */
export interface SimilarReferenceMovie {
  id: number;
  title: string;
}

export interface SimilarMoviesResponse {
  reference_movie: SimilarReferenceMovie;
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
  error?: string;
  detail?: string;
  type?: string;
  details?: Record<string, unknown>;
  error_code?: string;
  error_type?: string;
}
