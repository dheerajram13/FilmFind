"use client";

import Image from "next/image";
import { Star } from "lucide-react";
import { Movie, MovieSearchResult } from "@/types/api";
import { getPosterUrl, getPlaceholderImage } from "@/lib/image-utils";

type TileMovie = Movie | MovieSearchResult;

interface MovieTileProps {
  movie: TileMovie;
  badge?: string;
  footerHint?: string;
}

function getReleaseYear(releaseDate: string | null | undefined): string {
  if (!releaseDate) return "TBA";
  const parsed = new Date(releaseDate);
  if (Number.isNaN(parsed.getTime())) return "TBA";
  return String(parsed.getFullYear());
}

export function MovieTile({ movie, badge, footerHint }: MovieTileProps) {
  const posterUrl = getPosterUrl(movie.poster_path, "w500") ?? getPlaceholderImage();
  const releaseYear = getReleaseYear(movie.release_date);
  const rating = typeof movie.vote_average === "number" ? movie.vote_average.toFixed(1) : "-";

  return (
    <article className="ff-card">
      <div className="ff-card-media">
        <Image
          src={posterUrl}
          alt={`${movie.title} poster`}
          fill
          sizes="(max-width: 768px) 50vw, (max-width: 1280px) 25vw, 20vw"
          className="ff-card-image"
        />
        <div className="ff-card-overlay" />
        {badge && <span className="ff-badge">{badge}</span>}
        <div className="ff-rating">
          <Star size={13} className="ff-rating-star" />
          <span>{rating}</span>
        </div>
      </div>

      <div className="ff-card-body">
        <h3 className="ff-card-title">{movie.title}</h3>
        <p className="ff-card-meta">
          {releaseYear} · {movie.media_type === "tv" ? "Series" : "Movie"}
        </p>
        <p className="ff-card-copy">{movie.overview || "No overview available yet."}</p>
        {footerHint && <p className="ff-card-hint">{footerHint}</p>}
      </div>
    </article>
  );
}
