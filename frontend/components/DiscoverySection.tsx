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
        <Sparkles className="text-purple-600 dark:text-purple-400" size={28} />
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Discover with AI
        </h2>
      </div>

      <p className="mb-6 text-gray-600 dark:text-gray-400">
        Try these AI-powered searches to find your next favorite movie
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {DISCOVERY_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => onSearchSuggestion(prompt)}
            className="group relative overflow-hidden rounded-lg border-2 border-gray-200 bg-white p-4 text-left transition-all hover:border-purple-500 hover:shadow-lg dark:border-gray-700 dark:bg-gray-800 dark:hover:border-purple-400"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-blue-500/5 opacity-0 transition-opacity group-hover:opacity-100" />
            <div className="relative flex items-start gap-3">
              <Sparkles
                size={20}
                className="mt-0.5 flex-shrink-0 text-purple-600 opacity-60 group-hover:opacity-100 dark:text-purple-400"
              />
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {prompt}
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
