"use client";

import { Star } from "lucide-react";
import { cn } from "@/lib/utils";

interface RatingFilterProps {
  minRating?: number;
  onChange: (minRating: number | undefined) => void;
  className?: string;
}

const RATING_OPTIONS = [
  { value: undefined, label: "Any" },
  { value: 5, label: "5+" },
  { value: 6, label: "6+" },
  { value: 7, label: "7+" },
  { value: 8, label: "8+" },
  { value: 9, label: "9+" },
];

/**
 * RatingFilter component for setting minimum rating threshold
 *
 * Features:
 * - Quick select buttons for common rating thresholds
 * - Visual selection state
 * - Star icon for rating context
 */
export function RatingFilter({
  minRating,
  onChange,
  className,
}: RatingFilterProps) {
  return (
    <div className={cn("", className)}>
      <label className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
        <Star size={16} className="fill-amber-400 text-amber-400" />
        Minimum Rating
      </label>

      <div className="grid grid-cols-3 gap-2">
        {RATING_OPTIONS.map((option) => {
          const isSelected = minRating === option.value;
          return (
            <button
              key={option.label}
              type="button"
              onClick={() => onChange(option.value)}
              className={cn(
                "rounded-md px-3 py-2 text-sm font-medium transition-all",
                isSelected
                  ? "bg-amber-500 text-white hover:bg-amber-400"
                  : "border border-zinc-800 bg-zinc-900/60 text-zinc-300 hover:bg-zinc-800"
              )}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      {minRating !== undefined && (
        <p className="mt-2 text-xs text-zinc-500">
          Showing movies rated {minRating}/10 or higher
        </p>
      )}
    </div>
  );
}
