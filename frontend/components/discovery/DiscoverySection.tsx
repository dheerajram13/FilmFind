"use client";

import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface DiscoverySectionProps {
  onSearchSuggestion: (query: string) => void;
  className?: string;
}

const DISCOVERY_PROMPTS = [
  "Dark sci-fi movies like Blade Runner",
  "Feel-good comedies from the 90s",
  "Intense psychological thrillers",
  "Epic fantasy adventures",
  "Heartwarming family movies",
  "Mind-bending time travel films",
  "Action-packed superhero movies",
  "Romantic dramas that make you cry",
  "Horror movies with unexpected twists",
  "Classic movies from the golden age",
  "Foreign films with subtitles",
  "Documentary films about nature",
];

/**
 * DiscoverySection component for AI-powered search suggestions
 *
 * Features:
 * - Curated search prompts to inspire discovery
 * - Clickable cards that trigger searches
 * - Visual AI branding with sparkle icon
 * - Grid layout with hover effects
 */
export function DiscoverySection({
  onSearchSuggestion,
  className,
}: DiscoverySectionProps) {
  return (
    <div className={cn("", className)}>
      <div className="mb-6 flex items-center gap-2">
        <Sparkles className="text-red-500" size={28} />
        <h2 className="text-2xl font-semibold text-white">
          Discover with AI
        </h2>
      </div>

      <p className="mb-6 text-zinc-400">
        Try these AI-powered searches to find your next favorite movie
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {DISCOVERY_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => onSearchSuggestion(prompt)}
            className="group relative overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 text-left transition-all hover:border-red-500/40 hover:-translate-y-0.5"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-red-500/10 to-orange-400/10 opacity-0 transition-opacity group-hover:opacity-100" />
            <div className="relative flex items-start gap-3">
              <Sparkles
                size={20}
                className="mt-0.5 flex-shrink-0 text-red-400 opacity-60 group-hover:opacity-100"
              />
              <p className="text-sm font-medium text-white">
                {prompt}
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
