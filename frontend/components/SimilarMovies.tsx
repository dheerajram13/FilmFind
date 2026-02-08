"use client";

import { MovieSearchResult } from "@/types/api";
import { MovieCard } from "./MovieCard";
import { cn } from "@/lib/utils";

interface SimilarMoviesProps {
  movies: MovieSearchResult[];
  className?: string;
}

/**
 * SimilarMovies component displays a grid of similar movie recommendations
 *
 * Features:
 * - Grid layout with responsive columns
 * - Reuses MovieCard component
 * - Shows similarity scores
 */
export function SimilarMovies({ movies, className }: SimilarMoviesProps) {
  if (!movies || movies.length === 0) {
    return null;
  }

  return (
    <div className={cn("", className)}>
      <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Similar Movies
      </h2>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {movies.map((movie) => (
          <MovieCard key={movie.id} movie={movie} showScore />
        ))}
      </div>
    </div>
  );
}
