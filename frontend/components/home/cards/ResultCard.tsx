"use client";

import Image from "next/image";
import { getBackdropUrl, getPlaceholderImage, getPosterUrl } from "@/lib/image-utils";
import {
  buildReasons,
  parseYear,
  pickWatchLabel,
  primaryGenre,
  runtimeLabel,
  scoreAsPercent,
} from "@/lib/movie-formatters";
import type { MovieSearchResult } from "@/types/api";

interface ResultCardProps {
  movie: MovieSearchResult;
  rank: number;
  query: string;
  selectedStreaming: string[];
  expandedId: number | null;
  onToggleExpand: (id: number) => void;
  onOpenDetails: (movie: MovieSearchResult) => void;
}

export function ResultCard({
  movie,
  rank,
  query,
  selectedStreaming,
  expandedId,
  onToggleExpand,
  onOpenDetails,
}: ResultCardProps) {
  const year = parseYear(movie.release_date);
  const rating = movie.vote_average ?? 0;
  const genre = primaryGenre(movie);
  const match = scoreAsPercent(movie);
  const watchLabel = pickWatchLabel(movie, selectedStreaming);
  const reasons = buildReasons(movie, query);
  const runtime = runtimeLabel(movie.runtime);
  const isExpanded = expandedId === movie.id;
  const rankOpacity = Math.max(0.62, 1 - (rank - 1) * 0.08);
  const similarityPct = Math.round((movie.similarity_score ?? 0) * 100);

  const imageUrl =
    getBackdropUrl(movie.backdrop_path, "w780") ||
    getPosterUrl(movie.poster_path, "w500") ||
    getPlaceholderImage();

  return (
    <article
      className={`ff-r-card${isExpanded ? " expanded" : ""}`}
      style={{ opacity: rankOpacity }}
    >
      <div className="ff-r-poster">
        <Image
          src={imageUrl}
          alt={`${movie.title} poster`}
          fill
          sizes="(max-width: 900px) 100vw, 33vw"
          className="ff-r-poster-image"
        />
        <div className="ff-r-poster-grad" />
        <div className="ff-r-rank-badge">{rank}</div>
        <div className="ff-r-match-badge">
          <span className="ff-badge-star">★</span>
          <span className="ff-badge-pct">{match}%</span>
        </div>
      </div>

      <div className="ff-r-body">
        <h3 className="ff-r-title">{movie.title}</h3>

        <div className="ff-r-meta">
          <span className="ff-r-rating">★ {rating.toFixed(1)}</span>
          <span className="ff-r-dot" />
          <span>{year ?? "TBA"}</span>
          <span className="ff-r-dot" />
          <span>{genre}</span>
          {runtime && (
            <>
              <span className="ff-r-dot" />
              <span>{runtime}</span>
            </>
          )}
        </div>

        <div className="ff-r-reasons">
          {reasons.map((reason) => (
            <div className="ff-r-reason" key={`${movie.id}-${reason}`}>
              <div className="ff-reason-dot" />
              <span className="ff-reason-text">{reason}</span>
            </div>
          ))}
        </div>

        <div className="ff-r-actions">
          <button type="button" className="ff-r-watch">
            ▶ {watchLabel}
          </button>
          <button
            type="button"
            className="ff-r-more"
            onClick={(e) => {
              e.stopPropagation();
              onOpenDetails(movie);
            }}
          >
            Details
          </button>
        </div>
      </div>

      <button
        type="button"
        className="ff-r-expand"
        onClick={() => onToggleExpand(movie.id)}
      >
        {isExpanded ? "▴ hide breakdown" : "▾ score breakdown"}
      </button>

      <div className="ff-r-breakdown">
        <div className="ff-breakdown-title">Score breakdown</div>
        <div className="ff-score-bars">
          <div className="ff-score-row">
            <span className="ff-score-lbl">Narrative fit</span>
            <div className="ff-score-track">
              <div className="ff-score-fill ff-fill-gold" style={{ width: `${match}%` }} />
            </div>
            <span className="ff-score-num">{(match / 100).toFixed(2)}</span>
          </div>
          <div className="ff-score-row">
            <span className="ff-score-lbl">Semantic fit</span>
            <div className="ff-score-track">
              <div className="ff-score-fill ff-fill-teal" style={{ width: `${similarityPct}%` }} />
            </div>
            <span className="ff-score-num">{(movie.similarity_score ?? 0).toFixed(2)}</span>
          </div>
        </div>
        {movie.match_explanation && (
          <div className="ff-breakdown-note">
            Matched on: <em>{movie.match_explanation}</em>
          </div>
        )}
      </div>
    </article>
  );
}
