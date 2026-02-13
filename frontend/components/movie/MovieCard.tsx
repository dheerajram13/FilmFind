"use client";

import { Star } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { Movie, MovieSearchResult } from "@/types/api";
import { cn } from "@/lib/utils";
import { getPosterUrl, getPlaceholderImage } from "@/lib/image-utils";

interface MovieCardProps {
  movie: Movie | MovieSearchResult;
  className?: string;
  showScore?: boolean;
  priority?: boolean;
}

/**
 * Premium MovieCard - Figma Design Implementation
 *
 * Features:
 * - Clean poster with NO text overlays
 * - Info section below image
 * - Hover: gradient overlay + play button
 * - Purple glow effect on hover
 * - Rating badge top-right only
 * - Smooth scale animation
 */
export function MovieCard({ movie, className, priority = false }: MovieCardProps) {
  const posterUrl = getPosterUrl(movie.poster_path) || getPlaceholderImage();

  const releaseYear = movie.release_date
    ? new Date(movie.release_date).getFullYear()
    : null;

  const genres = movie.genres
    ?.slice(0, 2)
    .map((g) => g.name)
    .join(", ");

  const rating = movie.vote_average || 0;

  return (
    <Link
      href={`/movie/${movie.id}`}
      className={cn(
        "group relative block overflow-hidden rounded-xl",
        "bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50",
        "transition-all duration-300 ease-out",
        "hover:scale-105 hover:-translate-y-2 hover:z-10",
        "focus:outline-none focus:ring-2 focus:ring-purple-500/50",
        className
      )}
      aria-label={`View details for ${movie.title}`}
    >
      {/* Poster Image Container */}
      <div className="relative aspect-[2/3] overflow-hidden bg-zinc-900">
        <Image
          src={posterUrl}
          alt={`${movie.title} poster`}
          fill
          className={cn(
            "object-cover transition-transform duration-500",
            "group-hover:scale-110"
          )}
          sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 20vw"
          priority={priority}
        />

        {/* Gradient overlay - ONLY on hover */}
        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10" />

        {/* Rating badge - top-right, always visible */}
        {rating > 0 && (
          <div className="absolute top-3 right-3 bg-black/80 backdrop-blur-md rounded-full px-2.5 py-1 flex items-center gap-1 z-30">
            <Star className="w-4 h-4 text-yellow-500" fill="currentColor" />
            <span className="text-sm font-semibold text-white">{rating.toFixed(1)}</span>
          </div>
        )}
      </div>

      {/* Movie info - BELOW poster, not overlay */}
      <div className="p-4">
        <h3 className="font-semibold text-white mb-1 line-clamp-1 group-hover:text-purple-400 transition-colors duration-300">
          {movie.title}
        </h3>
        <div className="flex items-center justify-between text-sm">
          <span className="text-zinc-400">{releaseYear || "N/A"}</span>
          {genres && <span className="text-zinc-500 line-clamp-1">{genres}</span>}
        </div>
      </div>

      {/* Purple glow effect on hover */}
      <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
        <div className="absolute inset-0 rounded-xl shadow-[0_0_30px_rgba(168,85,247,0.4)]" />
      </div>
    </Link>
  );
}
