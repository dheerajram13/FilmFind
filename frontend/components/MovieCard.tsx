"use client";

import { Star, Calendar } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { Movie, MovieSearchResult } from "@/types/api";
import { cn } from "@/lib/utils";

interface MovieCardProps {
  movie: Movie | MovieSearchResult;
  className?: string;
  showScore?: boolean;
}

/**
 * MovieCard component displays a movie with poster, title, rating, and metadata
 *
 * Features:
 * - TMDB poster image with fallback
 * - Rating with star icon
 * - Release year
 * - Optional similarity/final score badge
 * - Hover effects
 * - Click to navigate to movie detail page
 */
export function MovieCard({ movie, className, showScore = false }: MovieCardProps) {
  const posterUrl = movie.poster_path
    ? `https://image.tmdb.org/t/p/w500${movie.poster_path}`
    : null;

  const releaseYear = movie.release_date
    ? new Date(movie.release_date).getFullYear()
    : null;

  const score = "final_score" in movie ? movie.final_score : "similarity_score" in movie ? movie.similarity_score : null;

  return (
    <Link
      href={`/movie/${movie.id}`}
      className={cn(
        "group block overflow-hidden rounded-lg bg-white shadow-md",
        "transition-all duration-300 hover:shadow-xl hover:scale-[1.02]",
        "dark:bg-gray-800",
        className
      )}
    >
      {/* Poster Image */}
      <div className="relative aspect-[2/3] overflow-hidden bg-gray-200 dark:bg-gray-700">
        {posterUrl ? (
          <Image
            src={posterUrl}
            alt={movie.title}
            fill
            className="object-cover transition-transform duration-300 group-hover:scale-105"
            sizes="(max-width: 768px) 50vw, (max-width: 1200px) 33vw, 25vw"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-gray-400 dark:text-gray-500">
            <span className="text-4xl">🎬</span>
          </div>
        )}

        {/* Score Badge */}
        {showScore && score !== null && score !== undefined && (
          <div className="absolute right-2 top-2 rounded-full bg-black/70 px-2 py-1 text-xs font-semibold text-white backdrop-blur-sm">
            {(score * 100).toFixed(0)}% match
          </div>
        )}
      </div>

      {/* Movie Info */}
      <div className="p-4">
        {/* Title */}
        <h3 className="mb-2 line-clamp-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
          {movie.title}
        </h3>

        {/* Metadata */}
        <div className="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
          {/* Rating */}
          <div className="flex items-center gap-1">
            <Star className="fill-yellow-400 text-yellow-400" size={16} />
            <span className="font-medium">
              {movie.vote_average ? movie.vote_average.toFixed(1) : "N/A"}
            </span>
          </div>

          {/* Release Year */}
          {releaseYear && (
            <>
              <span className="text-gray-400">•</span>
              <div className="flex items-center gap-1">
                <Calendar size={14} />
                <span>{releaseYear}</span>
              </div>
            </>
          )}
        </div>

        {/* Genres */}
        {movie.genres && movie.genres.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {movie.genres.slice(0, 3).map((genre) => (
              <span
                key={genre}
                className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
              >
                {genre}
              </span>
            ))}
          </div>
        )}
      </div>
    </Link>
  );
}
