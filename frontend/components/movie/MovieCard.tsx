"use client";

import { Star, Calendar, TrendingUp } from "lucide-react";
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
 * Netflix-inspired MovieCard component for dark theme
 *
 * Features:
 * - Netflix-style hover scale and animations
 * - Dark theme optimized colors
 * - Rating badges with better contrast
 * - Smooth transitions and hover states
 * - Optimized for horizontal carousels
 */
export function MovieCard({ movie, className, showScore = false, priority = false }: MovieCardProps) {
  const posterUrl = getPosterUrl(movie.poster_path) || getPlaceholderImage();

  const releaseYear = movie.release_date
    ? new Date(movie.release_date).getFullYear()
    : null;

  const score = "final_score" in movie && movie.final_score
    ? movie.final_score
    : "similarity_score" in movie && movie.similarity_score
      ? movie.similarity_score
      : null;

  const rating = movie.vote_average || 0;
  const hasGoodRating = rating >= 7.0;

  return (
    <Link
      href={`/movie/${movie.id}`}
      className={cn(
        "group relative block overflow-hidden rounded-md",
        "bg-zinc-900/50",
        "transition-all duration-300 ease-out",
        "hover:scale-105 hover:z-10",
        "focus:outline-none focus:ring-2 focus:ring-white/50",
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
            "object-cover transition-all duration-300",
            "group-hover:scale-110"
          )}
          sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 20vw"
          priority={priority}
        />

        {/* Gradient Overlay on Hover */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100 z-[5]" />

        {/* Media Type Badge - Top Left */}
        {movie.media_type && (
          <div className="absolute left-0 top-0 z-[15]">
            <div className="rounded-br-md rounded-tl-md bg-black/80 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-white backdrop-blur-sm">
              {movie.media_type === 'tv' ? 'TV Show' : 'Movie'}
            </div>
          </div>
        )}

        {/* Movie Info Overlay (visible on hover) */}
        <div className="absolute inset-x-0 bottom-0 p-3 opacity-0 transition-opacity duration-300 group-hover:opacity-100 z-[10]">
          <h3 className="line-clamp-2 text-sm font-bold text-white drop-shadow-lg">
            {movie.title}
          </h3>

          {releaseYear && (
            <p className="mt-1 text-xs text-white/80">
              {releaseYear}
            </p>
          )}
        </div>

        {/* Match Score Badge - Top Right */}
        {showScore && score !== null && score !== undefined && score > 0 && (
          <div className="absolute right-0 top-0 z-[20]">
            <div className="flex min-w-[52px] flex-col items-center justify-center rounded-bl-lg rounded-tr-md bg-red-600/95 px-2.5 py-2 shadow-xl backdrop-blur-sm">
              <TrendingUp size={14} className="mb-0.5 text-white" />
              <span className="text-sm font-bold leading-none text-white">
                {(score * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        )}

        {/* Rating Badge - Bottom Right Corner - HIGHEST Z-INDEX */}
        {rating > 0 && (
          <div
            style={{
              position: 'absolute',
              bottom: 0,
              right: 0,
              zIndex: 999
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 12px',
                borderTopLeftRadius: '8px',
                backgroundColor: hasGoodRating ? '#10b981' : rating >= 5.0 ? '#f59e0b' : '#3f3f46',
                color: 'white',
                fontWeight: 'bold',
                fontSize: '16px',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
                border: '2px solid rgba(255, 255, 255, 0.3)',
                backdropFilter: 'blur(12px)'
              }}
            >
              {/* Star Icon */}
              <Star
                size={14}
                style={{ fill: 'white', color: 'white' }}
              />
              {/* Rating Number */}
              <span style={{ lineHeight: 1 }}>
                {rating.toFixed(1)}
              </span>
            </div>
          </div>
        )}
      </div>
    </Link>
  );
}
