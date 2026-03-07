"use client";

import Image from "next/image";
import { FormEvent, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import apiClient from "@/lib/api-client";
import { getBackdropUrl, getPlaceholderImage, getPosterUrl } from "@/lib/image-utils";
import { SixtySecondMode } from "@/components/home/SixtySecondMode";
import { MovieSearchResult } from "@/types/api";

const SAMPLE_CHIPS = [
  '"F1 but in boxing"',
  '"Slow burn thriller like Parasite"',
  '"Feel-good like Ted Lasso"',
  '"Mind-bending like Inception"',
];

const TRENDING_SEARCHES = [
  "Something like Oppenheimer but lighter",
  "Emotional like Inside Out for adults",
  "Action with a female lead",
  "Horror but no jump scares",
  "Like The Bear but a movie",
];

const NAV_ITEMS = ["How it works", "Watchlist"];
const STREAMING_OPTIONS = ["Netflix", "Prime Video", "HBO Max", "Hulu", "Apple TV+"];
const GENRE_OPTIONS = ["Thriller", "Drama", "Crime", "Mystery"];
const STREAM_ICON_MAP: Record<string, string> = {
  netflix: "📺",
  "prime video": "🎬",
  "hbo max": "🎞️",
  hulu: "🎥",
  "apple tv+": "🍎",
};

type ScreenView = "home" | "results" | "detail";

function stripQuotes(text: string): string {
  return text.replace(/^"|"$/g, "");
}

function parseYear(releaseDate: string | null): number | null {
  if (!releaseDate) return null;
  const date = new Date(releaseDate);
  return Number.isNaN(date.getTime()) ? null : date.getFullYear();
}

function normalizeProviderName(provider: string): string {
  const lower = provider.toLowerCase();
  if (lower.includes("prime")) return "prime video";
  if (lower.includes("hbo") || lower === "max") return "hbo max";
  if (lower.includes("apple")) return "apple tv+";
  return lower;
}

function collectProviderNames(value: unknown, sink: Set<string>) {
  if (!value) return;

  if (Array.isArray(value)) {
    value.forEach((item) => collectProviderNames(item, sink));
    return;
  }

  if (typeof value !== "object") return;

  const objectValue = value as Record<string, unknown>;
  const providerName = objectValue.provider_name;
  if (typeof providerName === "string" && providerName.length > 0) {
    sink.add(providerName);
  }

  Object.values(objectValue).forEach((nested) => collectProviderNames(nested, sink));
}

function getProviderNames(movie: MovieSearchResult): string[] {
  if (!movie.streaming_providers || typeof movie.streaming_providers !== "object") {
    return [];
  }

  const names = new Set<string>();
  const providersRecord = movie.streaming_providers as Record<string, unknown>;
  Object.entries(providersRecord).forEach(([key, value]) => {
    if (key.length > 0 && !/^[A-Z]{2}$/.test(key)) {
      names.add(key);
    }
    collectProviderNames(value, names);
  });

  return Array.from(names);
}

function scoreAsPercent(movie: MovieSearchResult): number {
  const score = movie.final_score ?? movie.similarity_score ?? 0;
  if (!Number.isFinite(score)) return 0;
  if (score > 1) return Math.min(Math.round(score), 100);
  return Math.round(score * 100);
}

function primaryGenre(movie: MovieSearchResult): string {
  return movie.genres[0]?.name ?? "Drama";
}

function pickWatchLabel(movie: MovieSearchResult, selectedStreaming: string[]): string {
  const providers = getProviderNames(movie).map((provider) => normalizeProviderName(provider));
  const selected = selectedStreaming.find((provider) =>
    providers.includes(normalizeProviderName(provider))
  );
  if (selected) return selected;
  if (selectedStreaming.length > 0) return selectedStreaming[0];
  return "Watch";
}

function buildReasons(movie: MovieSearchResult, query: string): string[] {
  const reasons: string[] = [];

  if (movie.match_explanation && movie.match_explanation.length > 0) {
    reasons.push(movie.match_explanation);
  }

  const genre = primaryGenre(movie);
  reasons.push(`Strong ${genre.toLowerCase()} alignment with your query intent.`);
  reasons.push(`Critically rated ${movie.vote_average.toFixed(1)} with high audience pull.`);

  if (query.toLowerCase().includes("thriller")) {
    reasons[1] = "Psychological tension and pacing closely match your thriller request.";
  }

  return reasons.slice(0, 3);
}

function runtimeLabel(runtime: number | null): string | null {
  if (!runtime || runtime <= 0) return null;
  return `${runtime} min`;
}

function movieYear(movie: MovieSearchResult): string {
  const year = parseYear(movie.release_date);
  return year ? String(year) : "TBA";
}

function movieLanguage(movie: MovieSearchResult): string {
  const language = movie.original_language;
  if (typeof language !== "string" || language.trim().length === 0) {
    return "N/A";
  }
  return language.toUpperCase();
}

function streamIcon(providerName: string): string {
  return STREAM_ICON_MAP[normalizeProviderName(providerName)] ?? "▶";
}

function detailWhyCards(movie: MovieSearchResult, query: string) {
  const genre = primaryGenre(movie);
  const firstReason = movie.match_explanation
    ? {
        icon: "🎯",
        title: "Direct alignment with your query",
        description: movie.match_explanation,
      }
    : {
        icon: "🎯",
        title: `Strong ${genre} match`,
        description: `${movie.title} strongly aligns with the themes and tone you asked for in your prompt.`,
      };

  const secondReason = query.toLowerCase().includes("thriller")
    ? {
        icon: "🌀",
        title: "Psychological thriller tension",
        description:
          "The tension is internal, mounting, and sustained, which fits the thriller energy in your search.",
      }
    : {
        icon: "🌀",
        title: "Tone and pacing match",
        description:
          "Narrative rhythm and emotional intensity map closely to the style implied by your search phrase.",
      };

  const thirdReason = {
    icon: "⚡",
    title: "Performance-led intensity",
    description:
      "Character pressure and high-stakes choices create the same focused intensity that typically drives strong FilmFind matches.",
  };

  return [firstReason, secondReason, thirdReason];
}

function detailStreamingOptions(
  movie: MovieSearchResult,
  selectedStreaming: string[]
): { name: string; cta: string }[] {
  const fromMovie = getProviderNames(movie);
  const source = fromMovie.length > 0 ? fromMovie : selectedStreaming;
  return source.slice(0, 3).map((name, index) => ({
    name,
    cta: index === 2 ? "Watch →" : "Watch →",
  }));
}

function ResultCard({
  movie,
  query,
  selectedStreaming,
  onOpenDetails,
}: {
  movie: MovieSearchResult;
  query: string;
  selectedStreaming: string[];
  onOpenDetails: (movie: MovieSearchResult) => void;
}) {
  const year = parseYear(movie.release_date);
  const rating = movie.vote_average ?? 0;
  const genre = primaryGenre(movie);
  const match = scoreAsPercent(movie);
  const watchLabel = pickWatchLabel(movie, selectedStreaming);
  const reasons = buildReasons(movie, query);

  const imageUrl =
    getBackdropUrl(movie.backdrop_path, "w780") ||
    getPosterUrl(movie.poster_path, "w500") ||
    getPlaceholderImage();

  return (
    <article className="ff-r-card">
      <div className="ff-r-poster">
        <Image
          src={imageUrl}
          alt={`${movie.title} poster`}
          fill
          sizes="(max-width: 900px) 100vw, 33vw"
          className="ff-r-poster-image"
        />
        <div className="ff-r-match">★ {match}% match</div>
      </div>

      <div className="ff-r-body">
        <div className="ff-r-top">
          <h3 className="ff-r-title">{movie.title}</h3>
          <button type="button" className="ff-r-save" aria-label={`Save ${movie.title}`}>
            ♡
          </button>
        </div>

        <div className="ff-r-meta">
          <span className="ff-r-rating">★ {rating.toFixed(1)}</span>
          <span>{year ?? "TBA"}</span>
          <span>{genre}</span>
        </div>

        <div className="ff-r-reasons">
          {reasons.map((reason) => (
            <div className="ff-r-reason" key={`${movie.id}-${reason}`}>
              <span className="ff-r-dot" />
              <span>{reason}</span>
            </div>
          ))}
        </div>

        <div className="ff-r-actions">
          <button type="button" className="ff-r-watch">
            ▶ {watchLabel}
          </button>
          <button type="button" className="ff-r-more" onClick={() => onOpenDetails(movie)}>
            Details
          </button>
        </div>
      </div>
    </article>
  );
}

export function FilmfindHome() {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [activeScreen, setActiveScreen] = useState<ScreenView>("home");
  const [selectedMovie, setSelectedMovie] = useState<MovieSearchResult | null>(null);
  const [results, setResults] = useState<MovieSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedStreaming, setSelectedStreaming] = useState<string[]>(["Netflix", "Prime Video"]);
  const [selectedGenres, setSelectedGenres] = useState<string[]>(["Thriller", "Drama"]);
  const [minRating, setMinRating] = useState(7.0);
  const [minYear, setMinYear] = useState(2005);
  const [sixtyModeOpen, setSixtyModeOpen] = useState(false);

  const filteredResults = useMemo(() => {
    return results.filter((movie) => {
      const year = parseYear(movie.release_date);
      const movieGenres = movie.genres.map((genre) => genre.name.toLowerCase());
      const providerNames = getProviderNames(movie).map(normalizeProviderName);

      const ratingMatches = (movie.vote_average ?? 0) >= minRating;
      const yearMatches = year === null || year >= minYear;
      const genreMatches =
        selectedGenres.length === 0 ||
        selectedGenres.some((genre) => movieGenres.includes(genre.toLowerCase()));
      const streamingMatches =
        selectedStreaming.length === 0 ||
        providerNames.length === 0 ||
        selectedStreaming.some((service) =>
          providerNames.includes(normalizeProviderName(service))
        );

      return ratingMatches && yearMatches && genreMatches && streamingMatches;
    });
  }, [minRating, minYear, results, selectedGenres, selectedStreaming]);

  const runSearch = async (nextQuery: string) => {
    const clean = nextQuery.trim();
    if (clean.length < 3) {
      setError("Type at least 3 characters to search.");
      return;
    }

    setQuery(clean);
    setSubmittedQuery(clean);
    setError(null);
    setIsSearching(true);
    setActiveScreen("results");
    setSelectedMovie(null);

    try {
      const response = await apiClient.search(clean, undefined, 20);
      setResults(response.results);
    } catch (searchError) {
      setResults([]);
      setError(searchError instanceof Error ? searchError.message : "Search failed. Please try again.");
    } finally {
      setIsSearching(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void runSearch(query);
  };

  const toggleStreaming = (service: string) => {
    setSelectedStreaming((current) =>
      current.includes(service) ? current.filter((item) => item !== service) : [...current, service]
    );
  };

  const toggleGenre = (genre: string) => {
    setSelectedGenres((current) =>
      current.includes(genre) ? current.filter((item) => item !== genre) : [...current, genre]
    );
  };

  const clearFilters = () => {
    setSelectedStreaming(["Netflix", "Prime Video"]);
    setSelectedGenres(["Thriller", "Drama"]);
    setMinRating(7);
    setMinYear(2005);
  };

  const resetToHome = () => {
    setActiveScreen("home");
    setSubmittedQuery("");
    setSelectedMovie(null);
    setResults([]);
    setError(null);
  };

  const openDetail = (movie: MovieSearchResult) => {
    setSelectedMovie(movie);
    setActiveScreen("detail");
  };

  const backToResults = () => {
    if (submittedQuery.length > 0) {
      setActiveScreen("results");
      return;
    }
    setActiveScreen("home");
  };

  const detailMovie = selectedMovie ?? filteredResults[0] ?? results[0] ?? null;
  const similarPicks = (filteredResults.length > 0 ? filteredResults : results)
    .filter((movie) => (detailMovie ? movie.id !== detailMovie.id : true))
    .slice(0, 4);

  const detailPosterUrl = detailMovie
    ? getPosterUrl(detailMovie.poster_path, "w500") ||
      getBackdropUrl(detailMovie.backdrop_path, "w780") ||
      getPlaceholderImage()
    : null;

  const detailReasons = detailMovie ? detailWhyCards(detailMovie, submittedQuery) : [];
  const detailStreams = detailMovie ? detailStreamingOptions(detailMovie, selectedStreaming) : [];
  const detailPrimaryStream = detailStreams[0]?.name ?? "Netflix";
  const detailGenres = detailMovie ? detailMovie.genres.slice(0, 3).map((genre) => genre.name) : [];

  return (
    <div className="ff-shell">
      <div className="ff-blob ff-blob-gold" />
      <div className="ff-blob ff-blob-orange" />

      <main className="ff-page">
        {activeScreen === "home" && (
          <>
            <nav className="ff-home-nav">
              <div className="ff-home-logo">
                Film<span>Find</span>
              </div>

              <div className="ff-home-nav-links">
                {NAV_ITEMS.map((item) => (
                  <span key={item} className="ff-home-nav-link">
                    {item}
                  </span>
                ))}
                <button type="button" className="ff-home-nav-btn">
                  Sign in
                </button>
              </div>
            </nav>

            <section className="ff-home-hero">
              <p className="ff-home-eyebrow">✦ Not a streaming platform — a smarter way to find one</p>

              <h1 className="ff-home-title">
                DESCRIBE IT.
                <span className="outline">FIND IT.</span>
                <span className="gold">WATCH IT.</span>
              </h1>

              <p className="ff-home-sub">
                Tell FilmFind what you&apos;re in the mood for — in plain English.{" "}
                <em>Get the perfect match in seconds.</em>
              </p>

              <form className="ff-home-search" onSubmit={handleSubmit}>
                <span className="ff-home-search-icon">◈</span>
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  className="ff-home-search-input"
                  placeholder="Like Stranger Things but more horror and less nostalgia..."
                  aria-label="Search"
                />
                <button type="submit" className="ff-home-search-btn">
                  {isSearching ? <Loader2 size={14} className="ff-spin" /> : "Find it →"}
                </button>
              </form>

              <div className="ff-home-or">
                <span className="ff-home-or-line" />
                <span className="ff-home-or-text">OR</span>
                <span className="ff-home-or-line" />
              </div>

              <div className="ff-quick-card">
                <div className="ff-quick-accent" />

                <div className="ff-quick-main">
                  <div className="ff-quick-icon">⚡</div>
                  <div className="ff-quick-copy">
                    <div className="ff-quick-head">
                      <p className="ff-quick-title">Can&apos;t decide what to watch?</p>
                      <span className="ff-quick-badge">60 sec</span>
                    </div>
                    <p className="ff-quick-sub">
                      Answer 3 quick questions. Get one perfect pick. No scrolling required.
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  className="ff-quick-start"
                  onClick={() => setSixtyModeOpen(true)}
                >
                  Start →
                </button>
              </div>

              <div className="ff-home-chips">
                {SAMPLE_CHIPS.map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    className="ff-home-chip"
                    onClick={() => {
                      setQuery(stripQuotes(chip));
                    }}
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </section>

            <section className="ff-home-trending">
              <div className="ff-home-trending-label">
                Trending searches this week
                <span>View all →</span>
              </div>

              <div className="ff-home-trending-pills">
                {TRENDING_SEARCHES.map((text, index) => (
                  <button
                    key={text}
                    type="button"
                    className="ff-home-trending-pill"
                    onClick={() => setQuery(text)}
                  >
                    <span className="t-num">{String(index + 1).padStart(2, "0")}</span>
                    {text}
                  </button>
                ))}
              </div>
            </section>
          </>
        )}

        {activeScreen === "results" && (
          <>
            <nav className="ff-results-nav">
              <button type="button" className="ff-results-logo" onClick={resetToHome}>
                Film<span>Find</span>
              </button>

              <form className="ff-results-search" onSubmit={handleSubmit}>
                <span className="ff-home-search-icon">⌕</span>
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  className="ff-home-search-input"
                  aria-label="Search query"
                />
                <button type="submit" className="ff-home-search-btn">
                  {isSearching ? <Loader2 size={14} className="ff-spin" /> : "Search"}
                </button>
              </form>

              <div className="ff-results-right">
                <span>Watchlist</span>
                <div className="ff-avatar" />
              </div>
            </nav>

            <div className="ff-results-layout">
              <aside className="ff-filters-sidebar">
                <div className="ff-filter-title">
                  Filters
                  <button type="button" onClick={clearFilters}>
                    Clear
                  </button>
                </div>

                <div className="ff-filter-group">
                  <div className="ff-filter-group-label">Streaming on</div>
                  {STREAMING_OPTIONS.map((service) => {
                    const checked = selectedStreaming.includes(service);
                    return (
                      <button
                        key={service}
                        type="button"
                        className="ff-filter-option"
                        onClick={() => toggleStreaming(service)}
                      >
                        <span className={`ff-filter-check ${checked ? "checked" : ""}`}>
                          {checked ? "✓" : ""}
                        </span>
                        {service}
                      </button>
                    );
                  })}
                </div>

                <div className="ff-filter-group">
                  <div className="ff-filter-group-label">Genre</div>
                  {GENRE_OPTIONS.map((genre) => {
                    const checked = selectedGenres.includes(genre);
                    return (
                      <button
                        key={genre}
                        type="button"
                        className="ff-filter-option"
                        onClick={() => toggleGenre(genre)}
                      >
                        <span className={`ff-filter-check ${checked ? "checked" : ""}`}>
                          {checked ? "✓" : ""}
                        </span>
                        {genre}
                      </button>
                    );
                  })}
                </div>

                <div className="ff-filter-group">
                  <div className="ff-filter-group-label">IMDb Rating</div>
                  <input
                    type="range"
                    min={5}
                    max={9.5}
                    step={0.1}
                    value={minRating}
                    onChange={(event) => setMinRating(Number(event.target.value))}
                    className="ff-range"
                  />
                  <div className="ff-range-labels">
                    <span>{minRating.toFixed(1)}+</span>
                    <span>9.5</span>
                  </div>
                </div>

                <div className="ff-filter-group">
                  <div className="ff-filter-group-label">Release Year</div>
                  <input
                    type="range"
                    min={1980}
                    max={new Date().getFullYear()}
                    step={1}
                    value={minYear}
                    onChange={(event) => setMinYear(Number(event.target.value))}
                    className="ff-range"
                  />
                  <div className="ff-range-labels">
                    <span>{minYear}</span>
                    <span>{new Date().getFullYear()}</span>
                  </div>
                </div>
              </aside>

              <section className="ff-results-area">
                <div className="ff-results-topbar">
                  <div className="ff-results-query">
                    <span className="ff-query-label">Query</span>
                    <span className="ff-query-text">&quot;{submittedQuery}&quot;</span>
                  </div>
                  <div className="ff-results-meta">
                    <span>{filteredResults.length}</span> matches found
                  </div>
                </div>

                {isSearching && (
                  <div className="ff-loading-row">
                    <Loader2 size={16} className="ff-spin" />
                    Finding the best matches...
                  </div>
                )}

                {!isSearching && filteredResults.length > 0 && (
                  <div className="ff-results-grid">
                    {filteredResults.map((movie) => (
                      <ResultCard
                        key={movie.id}
                        movie={movie}
                        query={submittedQuery}
                        selectedStreaming={selectedStreaming}
                        onOpenDetails={openDetail}
                      />
                    ))}
                  </div>
                )}

                {!isSearching && filteredResults.length === 0 && (
                  <p className="ff-empty">
                    We couldn&apos;t find an exact match for this query. Try broadening your filters.
                  </p>
                )}
              </section>
            </div>
          </>
        )}

        {activeScreen === "detail" && (
          <>
            {!detailMovie ? (
              <div className="ff-detail-empty">
                <p>No movie selected yet.</p>
                <button type="button" className="ff-cta-secondary" onClick={backToResults}>
                  ← Back to results
                </button>
              </div>
            ) : (
              <>
                <section className="ff-detail-hero">
                  <div className="ff-detail-layout">
                    <div className="ff-detail-poster">
                      {detailPosterUrl ? (
                        <Image
                          src={detailPosterUrl}
                          alt={`${detailMovie.title} poster`}
                          fill
                          sizes="200px"
                          className="ff-detail-poster-image"
                        />
                      ) : (
                        <span>🎬</span>
                      )}
                    </div>

                    <div className="ff-detail-info">
                      <div className="ff-detail-tags">
                        {detailGenres.map((tag) => (
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
                          ▶ Watch on {detailPrimaryStream}
                        </button>
                        <button type="button" className="ff-cta-secondary">
                          + Save to Watchlist
                        </button>
                        <button type="button" className="ff-cta-secondary" onClick={backToResults}>
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
                        <div className="ff-why-title">
                          Why FilmFind matched this to your search
                        </div>
                        {detailReasons.map((reason) => (
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
                        {detailStreams.map((provider) => (
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
                              onClick={() => openDetail(movie)}
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
            )}
          </>
        )}

        {error && <p className="ff-error">{error}</p>}
      </main>

      <SixtySecondMode
        open={sixtyModeOpen}
        onClose={() => setSixtyModeOpen(false)}
        onApplyQuery={(modeQuery) => {
          setSixtyModeOpen(false);
          void runSearch(modeQuery);
        }}
      />
    </div>
  );
}
