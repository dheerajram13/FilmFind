"use client";

import Image from "next/image";
import { getBackdropUrl, getPlaceholderImage, getPosterUrl } from "@/lib/image-utils";
import {
  detailStreamingOptions,
  detailWhyCards,
  movieLanguage,
  movieYear,
  runtimeLabel,
} from "@/lib/movie-formatters";
import { streamIcon } from "@/lib/streaming-providers";
import type { MovieSearchResult } from "@/types/api";

interface DetailScreenProps {
  detailMovie: MovieSearchResult | null;
  submittedQuery: string;
  similarPicks: MovieSearchResult[];
  selectedStreaming: string[];
  onBackToResults: () => void;
  onOpenDetails: (movie: MovieSearchResult) => void;
}

export function DetailScreen({
  detailMovie,
  submittedQuery,
  similarPicks,
  selectedStreaming,
  onBackToResults,
  onOpenDetails,
}: DetailScreenProps) {
  if (!detailMovie) {
    return (
      <div className="ff-detail-empty">
        <p>No movie selected yet.</p>
        <button type="button" className="ff-cta-secondary" onClick={onBackToResults}>
          ← Back to results
        </button>
      </div>
    );
  }

  const posterUrl =
    getPosterUrl(detailMovie.poster_path, "w500") ||
    getBackdropUrl(detailMovie.backdrop_path, "w780") ||
    getPlaceholderImage();

  const reasons = detailWhyCards(detailMovie, submittedQuery);
  const streams = detailStreamingOptions(detailMovie, selectedStreaming);
  const primaryStream = streams[0]?.name ?? "Netflix";
  const genres = (detailMovie.genres ?? []).slice(0, 3).map((g) => g.name);

  return (
    <>
      <section className="ff-detail-hero">
        <div className="ff-detail-layout">
          <div className="ff-detail-poster">
            <Image
              src={posterUrl}
              alt={`${detailMovie.title} poster`}
              fill
              sizes="200px"
              className="ff-detail-poster-image"
            />
          </div>

          <div className="ff-detail-info">
            <div className="ff-detail-tags">
              {genres.map((tag) => (
                <span className="ff-detail-tag" key={`${detailMovie.id}-${tag}`}>
                  {tag}
                </span>
              ))}
              {runtimeLabel(detailMovie.runtime) && (
                <span className="ff-detail-tag">{runtimeLabel(detailMovie.runtime)}</span>
              )}
            </div>

            <h2 className="ff-detail-title">{detailMovie.title.toUpperCase()}</h2>

            <div className="ff-detail-meta">
              <span className="ff-detail-rating">★ {(detailMovie.vote_average ?? 0).toFixed(1)}</span>
              <span>{movieYear(detailMovie)}</span>
              <span>{movieLanguage(detailMovie)}</span>
            </div>

            <p className="ff-detail-synopsis">
              {detailMovie.overview ||
                "A highly matched pick from your query. FilmFind selected this based on tone, theme, and pacing similarity."}
            </p>

            <div className="ff-detail-ctas">
              <button type="button" className="ff-cta-primary">
                ▶ Watch on {primaryStream}
              </button>
              <button type="button" className="ff-cta-secondary">
                + Save to Watchlist
              </button>
              <button type="button" className="ff-cta-secondary" onClick={onBackToResults}>
                ← Back to results
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="ff-detail-body">
        <div className="ff-detail-grid">
          <div>
            <div className="ff-why-section">
              <div className="ff-why-title">Why FilmFind matched this to your search</div>
              {reasons.map((reason) => (
                <article className="ff-why-card" key={`${detailMovie.id}-${reason.title}`}>
                  <div className="ff-why-card-head">
                    <div className="ff-why-icon">{reason.icon}</div>
                    <div className="ff-why-card-title">{reason.title}</div>
                  </div>
                  <div className="ff-why-card-desc">{reason.description}</div>
                </article>
              ))}
            </div>
          </div>

          <aside className="ff-detail-sidebar">
            <div className="ff-streaming-card">
              <div className="ff-stream-title">Available on</div>
              {streams.map((provider) => (
                <div className="ff-stream-option" key={`${detailMovie.id}-${provider.name}`}>
                  <div className="ff-stream-name">
                    <span>{streamIcon(provider.name)}</span>
                    {provider.name}
                  </div>
                  <button type="button" className="ff-stream-btn">
                    {provider.cta}
                  </button>
                </div>
              ))}
            </div>

            <div className="ff-similar-card">
              <div className="ff-stream-title">Similar picks</div>
              {similarPicks.map((movie) => {
                const imageUrl =
                  getBackdropUrl(movie.backdrop_path, "w780") ||
                  getPosterUrl(movie.poster_path, "w500") ||
                  getPlaceholderImage();
                return (
                  <button
                    key={`similar-${movie.id}`}
                    type="button"
                    className="ff-sim-item"
                    onClick={() => onOpenDetails(movie)}
                  >
                    <div className="ff-sim-poster-mini">
                      <Image
                        src={imageUrl}
                        alt={`${movie.title} thumbnail`}
                        fill
                        sizes="48px"
                        className="ff-sim-poster-image"
                      />
                    </div>
                    <div className="ff-sim-info">
                      <div className="ff-sim-title">{movie.title}</div>
                      <div className="ff-sim-meta">
                        ★ {(movie.vote_average ?? 0).toFixed(1)} · {movieYear(movie)}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </aside>
        </div>
      </section>
    </>
  );
}
