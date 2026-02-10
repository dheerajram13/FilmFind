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
      <label className="mb-3 block text-sm font-semibold text-white">
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
                  ? "bg-red-600 text-white hover:bg-red-500"
                  : "border border-zinc-800 bg-zinc-900/60 text-zinc-300 hover:bg-zinc-800"
              )}
            >
              <span>{genre}</span>
              {isSelected && <Check size={16} className="ml-2" />}
            </button>
          );
        })}
      </div>
      {selectedGenres.length > 0 && (
        <p className="mt-2 text-xs text-zinc-500">
          {selectedGenres.length} genre{selectedGenres.length !== 1 ? "s" : ""} selected
        </p>
      )}
    </div>
  );
}
