/**
 * Image utilities for handling TMDB image URLs
 */

const TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p";

/**
 * Get the full URL for a movie poster
 * Handles both relative paths and already-complete URLs
 */
export function getPosterUrl(posterPath: string | null | undefined, size: "w200" | "w500" | "original" = "w500"): string | null {
  if (!posterPath) return null;

  // If it's already a full URL, return as-is
  if (posterPath.startsWith("http")) {
    return posterPath;
  }

  // Otherwise, construct the full URL
  return `${TMDB_IMAGE_BASE}/${size}${posterPath}`;
}

/**
 * Get the full URL for a movie backdrop
 */
export function getBackdropUrl(backdropPath: string | null | undefined, size: "w780" | "w1280" | "original" = "w1280"): string | null {
  if (!backdropPath) return null;

  // If it's already a full URL, return as-is
  if (backdropPath.startsWith("http")) {
    return backdropPath;
  }

  // Otherwise, construct the full URL
  return `${TMDB_IMAGE_BASE}/${size}${backdropPath}`;
}

/**
 * Get placeholder image for missing posters
 */
export function getPlaceholderImage(): string {
  return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='500' height='750' viewBox='0 0 500 750'%3E%3Crect fill='%2318181b' width='500' height='750'/%3E%3Ctext fill='%2371717a' font-family='sans-serif' font-size='48' font-weight='bold' x='50%25' y='50%25' text-anchor='middle' dominant-baseline='middle'%3E🎬%3C/text%3E%3C/svg%3E";
}
