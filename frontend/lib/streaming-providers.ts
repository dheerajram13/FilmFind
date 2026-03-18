import type { Movie, MovieSearchResult } from "@/types/api";

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

/** Recursively collect all `provider_name` strings from nested streaming data. */
export function collectProviderNames(value: unknown, sink: Set<string>): void {
  if (!value) return;

  if (Array.isArray(value)) {
    value.forEach((item) => collectProviderNames(item, sink));
    return;
  }

  if (typeof value !== "object") return;

  const obj = value as Record<string, unknown>;
  const name = obj.provider_name;
  if (typeof name === "string" && name.length > 0) {
    sink.add(name);
  }

  Object.values(obj).forEach((nested) => collectProviderNames(nested, sink));
}

/** Extract all provider name strings from a movie's streaming_providers field. */
export function getProviderNames(movie: Movie | MovieSearchResult): string[] {
  if (!movie.streaming_providers || typeof movie.streaming_providers !== "object") {
    return [];
  }

  const names = new Set<string>();
  const providers = movie.streaming_providers as Record<string, unknown>;

  Object.entries(providers).forEach(([key, value]) => {
    // Skip two-letter country-code keys that aren't provider names
    if (key.length > 0 && !/^[A-Z]{2}$/.test(key)) {
      names.add(key);
    }
    collectProviderNames(value, names);
  });

  return Array.from(names);
}

/** Return the primary streaming provider for display (title-cased, falls back to "Netflix"). */
export function primaryProvider(movie: Movie | MovieSearchResult): string {
  const names = getProviderNames(movie);
  if (names.length === 0) return "Netflix";
  return displayProviderName(normalizeProviderName(names[0]));
}
