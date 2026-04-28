import type { Movie, MovieSearchResult, StreamingProvider, StreamingRegion } from "@/types/api";

const STREAM_ICON_MAP: Record<string, string> = {
  netflix: "📺",
  "prime video": "🎬",
  "disney+": "✨",
  "hbo max": "🎞️",
  "apple tv+": "🍎",
  stan: "🎭",
  "paramount+": "⛰️",
  hulu: "🎥",
  crunchyroll: "🍊",
  binge: "📡",
};

/** Normalise a raw provider string to a lowercase canonical key. */
export function normalizeProviderName(provider: string): string {
  const lower = provider.toLowerCase();
  if (lower.includes("prime")) return "prime video";
  if (lower.includes("hbo") || lower === "max") return "hbo max";
  if (lower.includes("apple")) return "apple tv+";
  if (lower.includes("disney")) return "disney+";
  if (lower.includes("paramount")) return "paramount+";
  if (lower.includes("crunchyroll")) return "crunchyroll";
  if (lower.includes("binge")) return "binge";
  if (lower.includes("foxtel")) return "binge";
  if (lower.includes("stan")) return "stan";
  if (lower.includes("netflix")) return "netflix";
  if (lower.includes("hulu")) return "hulu";
  return lower;
}

/** Title-case a normalised provider name for display (e.g. "prime video" → "Prime Video"). */
export function displayProviderName(normalised: string): string {
  return normalised
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/** Return the emoji icon for a provider name (raw or normalised). */
export function streamIcon(providerName: string): string {
  return STREAM_ICON_MAP[normalizeProviderName(providerName)] ?? "▶";
}

/** Collect provider names from a provider list. */
function collectFromList(list: StreamingProvider[] | undefined, sink: Set<string>): void {
  list?.forEach((p) => {
    if (p.provider_name) sink.add(p.provider_name);
  });
}

/** Collect provider names from a region entry. */
function collectFromRegion(region: StreamingRegion, sink: Set<string>): void {
  collectFromList(region.flatrate, sink);
  collectFromList(region.rent, sink);
  collectFromList(region.buy, sink);
  collectFromList(region.free, sink);
  collectFromList(region.ads, sink);
}

/** Extract all provider name strings from a movie's streaming_providers field. */
export function getProviderNames(movie: Movie | MovieSearchResult): string[] {
  if (!movie.streaming_providers) return [];

  const names = new Set<string>();

  Object.entries(movie.streaming_providers).forEach(([key, value]) => {
    if (!value) return;
    if (Array.isArray(value)) {
      collectFromList(value as StreamingProvider[], names);
    } else if (typeof value === "object") {
      // Skip two-letter country-code keys that aren't provider names
      if (!/^[A-Z]{2}$/.test(key)) names.add(key);
      collectFromRegion(value as StreamingRegion, names);
    }
  });

  return Array.from(names);
}

/** Return the primary streaming provider for display (title-cased, falls back to "Netflix"). */
export function primaryProvider(movie: Movie | MovieSearchResult): string {
  const names = getProviderNames(movie);
  if (names.length === 0) return "Netflix";
  return displayProviderName(normalizeProviderName(names[0]));
}
