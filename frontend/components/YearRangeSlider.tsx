"use client";

import { cn } from "@/lib/utils";

interface YearRangeSliderProps {
  minYear?: number;
  maxYear?: number;
  onChange: (minYear: number | undefined, maxYear: number | undefined) => void;
  className?: string;
}

const EARLIEST_YEAR = 1900;
const CURRENT_YEAR = new Date().getFullYear();

/**
 * YearRangeSlider component for selecting release year range
 *
 * Features:
 * - Dual input fields for min/max year
 * - Validation (min <= max)
 * - Clear button to reset
 * - Shows current selection
 */
export function YearRangeSlider({
  minYear,
  maxYear,
  onChange,
  className,
}: YearRangeSliderProps) {
  const handleMinChange = (value: string) => {
    const year = value ? parseInt(value, 10) : undefined;
    if (year !== undefined && (year < EARLIEST_YEAR || year > CURRENT_YEAR)) {
      return;
    }
    onChange(year, maxYear);
  };

  const handleMaxChange = (value: string) => {
    const year = value ? parseInt(value, 10) : undefined;
    if (year !== undefined && (year < EARLIEST_YEAR || year > CURRENT_YEAR)) {
      return;
    }
    onChange(minYear, year);
  };

  const handleClear = () => {
    onChange(undefined, undefined);
  };

  const hasValue = minYear !== undefined || maxYear !== undefined;

  return (
    <div className={cn("", className)}>
      <div className="mb-3 flex items-center justify-between">
        <label className="block text-sm font-semibold text-gray-900 dark:text-gray-100">
          Release Year
        </label>
        {hasValue && (
          <button
            type="button"
            onClick={handleClear}
            className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
          >
            Clear
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* Min Year */}
        <div>
          <label className="mb-1 block text-xs text-gray-600 dark:text-gray-400">
            From
          </label>
          <input
            type="number"
            value={minYear ?? ""}
            onChange={(e) => handleMinChange(e.target.value)}
            placeholder={String(EARLIEST_YEAR)}
            min={EARLIEST_YEAR}
            max={maxYear ?? CURRENT_YEAR}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500"
          />
        </div>

        {/* Max Year */}
        <div>
          <label className="mb-1 block text-xs text-gray-600 dark:text-gray-400">
            To
          </label>
          <input
            type="number"
            value={maxYear ?? ""}
            onChange={(e) => handleMaxChange(e.target.value)}
            placeholder={String(CURRENT_YEAR)}
            min={minYear ?? EARLIEST_YEAR}
            max={CURRENT_YEAR}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500"
          />
        </div>
      </div>

      {/* Display current range */}
      {hasValue && (
        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
          {minYear ?? EARLIEST_YEAR} - {maxYear ?? CURRENT_YEAR}
        </p>
      )}
    </div>
  );
}
