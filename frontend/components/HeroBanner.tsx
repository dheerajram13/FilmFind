"use client";

import { Play, Info, Star } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { Movie } from "@/types/api";
import { cn } from "@/lib/utils";

interface HeroBannerProps {
  movie: Movie;
  className?: string;
}

/**
 * HeroBanner component for featured movie on homepage
 *
 * Features:
 * - Large backdrop image with gradient overlay
 * - Movie title, overview, and metadata
 * - Action buttons (More Info, Play Trailer)
 * - Responsive design
 */
export function HeroBanner({ movie, className }: HeroBannerProps) {
  const backdropUrl = movie.backdrop_path
    ? `https://image.tmdb.org/t/p/original${movie.backdrop_path}`
    : null;

  const releaseYear = movie.release_date
    ? new Date(movie.release_date).getFullYear()
    : null;

  return (
    <div className={cn("relative h-[70vh] min-h-[500px] w-full overflow-hidden", className)}>
      {/* Backdrop Image */}
      {backdropUrl && (
        <div className="absolute inset-0">
          <Image
            src={backdropUrl}
            alt={movie.title}
            fill
            className="object-cover"
            priority
          />
          {/* Gradient Overlays */}
          <div className="absolute inset-0 bg-gradient-to-r from-black via-black/60 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-t from-gray-50 via-transparent to-transparent dark:from-gray-900" />
        </div>
      )}

      {/* Content */}
      <div className="relative h-full mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-full flex-col justify-center max-w-2xl">
          {/* Title */}
          <h1 className="mb-4 text-4xl font-bold text-white sm:text-5xl lg:text-6xl drop-shadow-lg">
            {movie.title}
          </h1>

          {/* Metadata */}
          <div className="mb-4 flex items-center gap-4 text-white/90">
            {movie.vote_average > 0 && (
              <div className="flex items-center gap-1">
                <Star className="fill-yellow-400 text-yellow-400" size={20} />
                <span className="font-semibold">{movie.vote_average.toFixed(1)}</span>
              </div>
            )}
            {releaseYear && <span className="font-medium">{releaseYear}</span>}
            {movie.genres && movie.genres.length > 0 && (
              <span className="font-medium">{movie.genres[0].name}</span>
            )}
          </div>

          {/* Overview */}
          {movie.overview && (
            <p className="mb-6 text-lg text-white/90 line-clamp-3 drop-shadow">
              {movie.overview}
            </p>
          )}

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-3">
            <Link
              href={`/movie/${movie.id}`}
              className="flex items-center gap-2 rounded-md bg-white px-6 py-3 text-base font-semibold text-gray-900 transition-all hover:bg-white/90"
            >
              <Info size={20} />
              More Info
            </Link>
            <button
              className="flex items-center gap-2 rounded-md bg-white/20 px-6 py-3 text-base font-semibold text-white backdrop-blur-sm transition-all hover:bg-white/30"
              onClick={() => {
                // Placeholder for trailer functionality
                alert("Trailer functionality coming soon!");
              }}
            >
              <Play size={20} />
              Play Trailer
            </button>
          </div>

          {/* Genres */}
          {movie.genres && movie.genres.length > 0 && (
            <div className="mt-6 flex flex-wrap gap-2">
              {movie.genres.slice(0, 4).map((genre) => (
                <span
                  key={genre.id}
                  className="rounded-full bg-white/20 px-3 py-1 text-sm font-medium text-white backdrop-blur-sm"
                >
                  {genre.name}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
