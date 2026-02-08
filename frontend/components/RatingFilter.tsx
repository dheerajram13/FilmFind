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
      <label className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
        <Star size={16} className="fill-yellow-400 text-yellow-400" />
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
                  ? "bg-yellow-500 text-white hover:bg-yellow-600"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              )}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      {minRating !== undefined && (
        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
          Showing movies rated {minRating}/10 or higher
        </p>
      )}
    </div>
  );
}
