"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface GenreSelectorProps {
  selectedGenres: string[];
  onChange: (genres: string[]) => void;
  className?: string;
}

// Common movie genres from TMDB
const GENRES = [
  "Action",
  "Adventure",
  "Animation",
  "Comedy",
  "Crime",
  "Documentary",
  "Drama",
  "Family",
  "Fantasy",
  "History",
  "Horror",
  "Music",
  "Mystery",
  "Romance",
  "Science Fiction",
  "TV Movie",
  "Thriller",
  "War",
  "Western",
];

/**
 * GenreSelector component for multi-selecting movie genres
 *
 * Features:
 * - Grid layout with clickable genre buttons
 * - Visual selection state with checkmarks
 * - Multi-select support
 */
export function GenreSelector({
  selectedGenres,
  onChange,
  className,
}: GenreSelectorProps) {
  const toggleGenre = (genre: string) => {
    if (selectedGenres.includes(genre)) {
      onChange(selectedGenres.filter((g) => g !== genre));
    } else {
      onChange([...selectedGenres, genre]);
    }
  };

  return (
    <div className={cn("", className)}>
      <label className="mb-3 block text-sm font-semibold text-gray-900 dark:text-gray-100">
        Genres
      </label>
      <div className="grid grid-cols-2 gap-2">
        {GENRES.map((genre) => {
          const isSelected = selectedGenres.includes(genre);
          return (
            <button
              key={genre}
              type="button"
              onClick={() => toggleGenre(genre)}
              className={cn(
                "flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-all",
                isSelected
                  ? "bg-blue-600 text-white hover:bg-blue-700"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              )}
            >
              <span>{genre}</span>
              {isSelected && <Check size={16} className="ml-2" />}
            </button>
          );
        })}
      </div>
      {selectedGenres.length > 0 && (
        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
          {selectedGenres.length} genre{selectedGenres.length !== 1 ? "s" : ""} selected
        </p>
      )}
    </div>
  );
}
