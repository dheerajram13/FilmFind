"use client";

import { X, Filter, RotateCcw } from "lucide-react";
import { useFilters } from "@/lib/filter-context";
import { GenreSelector } from "./GenreSelector";
import { LanguageSelector } from "./LanguageSelector";
import { YearRangeSlider } from "./YearRangeSlider";
import { RatingFilter } from "./RatingFilter";
import { RuntimeFilter } from "./RuntimeFilter";
import { cn } from "@/lib/utils";

interface FilterPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onApply?: () => void;
  className?: string;
}

/**
 * FilterPanel component - sidebar/modal for advanced search filters
 *
 * Features:
 * - Responsive: sidebar on desktop, full-screen on mobile
 * - All filter components integrated
 * - Apply/Reset buttons
 * - Active filter count badge
 * - Smooth slide-in animation
 */
export function FilterPanel({
  isOpen,
  onClose,
  onApply,
  className,
}: FilterPanelProps) {
  const { filters, updateFilter, resetFilters, hasActiveFilters } = useFilters();

  const handleApply = () => {
    onApply?.();
    onClose();
  };

  const handleReset = () => {
    resetFilters();
  };

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Panel */}
      <div
        className={cn(
          "fixed right-0 top-0 z-50 h-full w-full transform bg-white shadow-2xl transition-transform duration-300 dark:bg-gray-900 sm:w-96",
          isOpen ? "translate-x-0" : "translate-x-full",
          className
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 p-4 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <Filter size={20} className="text-blue-600 dark:text-blue-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Filters
            </h2>
            {hasActiveFilters && (
              <span className="rounded-full bg-blue-600 px-2 py-0.5 text-xs font-semibold text-white">
                Active
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100"
            aria-label="Close filters"
          >
            <X size={20} />
          </button>
        </div>

        {/* Filter Content */}
        <div className="h-[calc(100%-8rem)] overflow-y-auto p-4">
          <div className="space-y-6">
            {/* Genres */}
            <GenreSelector
              selectedGenres={filters.genres || []}
              onChange={(genres) => updateFilter("genres", genres)}
            />

            {/* Languages */}
            <LanguageSelector
              selectedLanguages={filters.languages || []}
              onChange={(languages) => updateFilter("languages", languages)}
            />

            {/* Release Year */}
            <YearRangeSlider
              minYear={filters.min_year}
              maxYear={filters.max_year}
              onChange={(min, max) => {
                updateFilter("min_year", min);
                updateFilter("max_year", max);
              }}
            />

            {/* Rating */}
            <RatingFilter
              minRating={filters.min_rating}
              onChange={(rating) => updateFilter("min_rating", rating)}
            />

            {/* Runtime */}
            <RuntimeFilter
              minRuntime={filters.min_runtime}
              maxRuntime={filters.max_runtime}
              onChange={(min, max) => {
                updateFilter("min_runtime", min);
                updateFilter("max_runtime", max);
              }}
            />

            {/* Adult Content Toggle */}
            <div className="flex items-center justify-between">
              <label className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                Include Adult Content
              </label>
              <button
                type="button"
                onClick={() => updateFilter("include_adult", !filters.include_adult)}
                className={cn(
                  "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                  filters.include_adult
                    ? "bg-blue-600"
                    : "bg-gray-300 dark:bg-gray-700"
                )}
              >
                <span
                  className={cn(
                    "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                    filters.include_adult ? "translate-x-6" : "translate-x-1"
                  )}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 border-t border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <div className="flex gap-3">
            <button
              onClick={handleReset}
              disabled={!hasActiveFilters}
              className={cn(
                "flex flex-1 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all",
                hasActiveFilters
                  ? "bg-gray-100 text-gray-900 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700"
                  : "cursor-not-allowed bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-600"
              )}
            >
              <RotateCcw size={16} />
              Reset
            </button>
            <button
              onClick={handleApply}
              className="flex flex-1 items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-blue-700"
            >
              <Filter size={16} />
              Apply Filters
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
