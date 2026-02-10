"use client";

import { Play, Info, Star } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { Movie } from "@/types/api";
import { getBackdropUrl, getPosterUrl } from "@/lib/image-utils";
import { cn } from "@/lib/utils";

interface HeroBannerProps {
  movie: Movie;
  className?: string;
}

/**
 * Netflix-style Hero Banner Component
 *
 * Features:
 * - Full-width backdrop image with gradient overlay
 * - Movie title, overview, and metadata
 * - Call-to-action buttons (Play, More Info)
 * - Responsive design
 * - Optimized image loading with Next.js Image
 */
export function HeroBanner({ movie, className }: HeroBannerProps) {
  const backdropUrl = getBackdropUrl(movie.backdrop_path, "w1280");
  const posterUrl = getPosterUrl(movie.poster_path, "w500");
  const releaseYear = movie.release_date
    ? new Date(movie.release_date).getFullYear()
    : null;
  const rating = movie.vote_average || 0;

  // Truncate overview to ~200 characters
  const truncatedOverview =
    movie.overview && movie.overview.length > 200
      ? movie.overview.substring(0, 200) + "..."
      : movie.overview;

  return (
    <div className={cn("relative h-[70vh] min-h-[500px] w-full overflow-hidden", className)}>
      {/* Backdrop Image */}
      {backdropUrl ? (
        <div className="absolute inset-0 h-full w-full">
          <Image
            src={backdropUrl}
            alt={`${movie.title} backdrop`}
            fill
            className="object-cover"
            priority
            quality={90}
            sizes="100vw"
          />
        </div>
      ) : (
        <div className="absolute inset-0 bg-gradient-to-r from-zinc-900 to-zinc-800" />
      )}

      {/* Gradient Overlays */}
      <div className="absolute inset-0 bg-gradient-to-r from-black via-black/50 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent" />

      {/* Content */}
      <div className="relative z-10 flex h-full items-end">
        <div className="container mx-auto px-4 pb-16 sm:px-6 lg:px-8">
          <div className="max-w-2xl space-y-6">
            {/* Title */}
            <h1 className="text-4xl font-bold text-white sm:text-5xl lg:text-6xl drop-shadow-2xl">
              {movie.title}
            </h1>

            {/* Metadata */}
            <div className="flex flex-wrap items-center gap-4 text-sm text-white/90">
              {rating > 0 && (
                <div className="flex items-center gap-1.5 rounded bg-white/10 px-2.5 py-1 backdrop-blur-sm">
                  <Star size={14} className="fill-yellow-400 text-yellow-400" />
                  <span className="font-semibold">{rating.toFixed(1)}</span>
                </div>
              )}
              {releaseYear && (
                <span className="font-medium">{releaseYear}</span>
              )}
              {movie.runtime && movie.runtime > 0 && (
                <>
                  <span className="text-white/50">•</span>
                  <span>{Math.floor(movie.runtime / 60)}h {movie.runtime % 60}m</span>
                </>
              )}
            </div>

            {/* Overview */}
            {truncatedOverview && (
              <p className="text-base leading-relaxed text-white/90 drop-shadow-lg sm:text-lg">
                {truncatedOverview}
              </p>
            )}

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-3">
              <Link
                href={`/movie/${movie.id}`}
                className={cn(
                  "group flex items-center gap-2 rounded-md px-6 py-3",
                  "bg-white text-black font-semibold",
                  "transition-all duration-200",
                  "hover:bg-white/90 hover:scale-105",
                  "focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-black"
                )}
              >
                <Play size={20} className="fill-current" />
                <span>More Info</span>
              </Link>

              <Link
                href={`/movie/${movie.id}`}
                className={cn(
                  "group flex items-center gap-2 rounded-md px-6 py-3",
                  "bg-white/20 text-white font-semibold backdrop-blur-sm",
                  "transition-all duration-200",
                  "hover:bg-white/30 hover:scale-105",
                  "focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-black"
                )}
              >
                <Info size={20} />
                <span>Details</span>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom fade for smooth transition to content */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black to-transparent" />
    </div>
  );
}
