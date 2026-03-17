import type { Movie, MovieSearchResult } from "@/types/api";
import { getProviderNames, normalizeProviderName } from "@/lib/streaming-providers";

export type WhyCard = {
  icon: string;
  title: string;
  description: string;
};

export type StreamingOption = {
  name: string;
  cta: string;
};

export function stripQuotes(text: string): string {
  return text.replace(/^"|"$/g, "");
}

/** Parse a release_date string to a numeric year, or null if invalid. */
export function parseYear(releaseDate: string | null | undefined): number | null {
  if (!releaseDate) return null;
  const date = new Date(releaseDate);
  return Number.isNaN(date.getTime()) ? null : date.getFullYear();
}

/** Format a release_date string as a display year string (e.g. "2021" or "TBA"). */
export function parseYearString(releaseDate: string | null | undefined): string {
  const year = parseYear(releaseDate);
  return year ? String(year) : "TBA";
}

export function runtimeLabel(runtime: number | null | undefined): string | null {
  if (!runtime || runtime <= 0) return null;
  return `${runtime} min`;
}

export function movieYear(movie: MovieSearchResult | Movie): string {
  return parseYearString(movie.release_date);
}

export function movieLanguage(movie: MovieSearchResult | Movie): string {
  const lang = movie.original_language;
  if (typeof lang !== "string" || lang.trim().length === 0) return "N/A";
  return lang.toUpperCase();
}

export function scoreAsPercent(movie: MovieSearchResult): number {
  const score = movie.relevance_score ?? movie.similarity_score ?? 0;
  if (!Number.isFinite(score) || score <= 0) return 0;
  return Math.min(Math.round(score * 100), 99);
}

export function primaryGenre(movie: MovieSearchResult | Movie): string {
  return movie.genres[0]?.name ?? "Drama";
}

export function genreEmoji(movie: Movie | MovieSearchResult): string {
  const first = movie.genres[0]?.name.toLowerCase() ?? "";
  if (first.includes("drama")) return "🎭";
  if (first.includes("thriller")) return "🔍";
  if (first.includes("sci")) return "🛸";
  if (first.includes("horror")) return "🪦";
  if (first.includes("comedy")) return "😂";
  if (first.includes("animation")) return "🧠";
  return "🎬";
}

export function pickWatchLabel(movie: MovieSearchResult, selectedStreaming: string[]): string {
  const providers = getProviderNames(movie).map(normalizeProviderName);
  const selected = selectedStreaming.find((s) => providers.includes(normalizeProviderName(s)));
  if (selected) return selected;
  if (selectedStreaming.length > 0) return selectedStreaming[0];
  return "Watch";
}

export function buildReasons(movie: MovieSearchResult, query: string): string[] {
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

export function detailWhyCards(movie: MovieSearchResult, query: string): WhyCard[] {
  const genre = primaryGenre(movie);

  const first: WhyCard = movie.match_explanation
    ? { icon: "🎯", title: "Direct alignment with your query", description: movie.match_explanation }
    : {
        icon: "🎯",
        title: `Strong ${genre} match`,
        description: `${movie.title} strongly aligns with the themes and tone you asked for in your prompt.`,
      };

  const second: WhyCard = query.toLowerCase().includes("thriller")
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

  const third: WhyCard = {
    icon: "⚡",
    title: "Performance-led intensity",
    description:
      "Character pressure and high-stakes choices create the same focused intensity that typically drives strong FilmFind matches.",
  };

  return [first, second, third];
}

export function detailStreamingOptions(
  movie: MovieSearchResult,
  selectedStreaming: string[]
): StreamingOption[] {
  const fromMovie = getProviderNames(movie);
  const source = fromMovie.length > 0 ? fromMovie : selectedStreaming;
  return source.slice(0, 3).map((name) => ({ name, cta: "Watch →" }));
}
