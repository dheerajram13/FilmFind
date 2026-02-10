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
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Panel */}
      <div
        className={cn(
          "fixed right-0 top-0 z-50 h-full w-full transform border-l border-zinc-800 bg-zinc-950/90 shadow-2xl backdrop-blur-xl transition-transform duration-300 sm:w-96",
          isOpen ? "translate-x-0" : "translate-x-full",
          className
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-800 p-4">
          <div className="flex items-center gap-2">
            <Filter size={20} className="text-red-500" />
            <h2 className="text-lg font-semibold text-white">
              Filters
            </h2>
            {hasActiveFilters && (
              <span className="rounded-full bg-red-600 px-2 py-0.5 text-xs font-semibold text-white">
                Active
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-zinc-400 hover:bg-zinc-800 hover:text-white"
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
              <label className="text-sm font-semibold text-white">
                Include Adult Content
              </label>
              <button
                type="button"
                onClick={() => updateFilter("include_adult", !filters.include_adult)}
                className={cn(
                  "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                  filters.include_adult
                    ? "bg-red-600"
                    : "bg-zinc-700"
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
        <div className="absolute bottom-0 left-0 right-0 border-t border-zinc-800 bg-zinc-950/90 p-4">
          <div className="flex gap-3">
            <button
              onClick={handleReset}
              disabled={!hasActiveFilters}
              className={cn(
                "flex flex-1 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all",
                hasActiveFilters
                  ? "bg-zinc-800 text-white hover:bg-zinc-700"
                  : "cursor-not-allowed bg-zinc-900 text-zinc-500"
              )}
            >
              <RotateCcw size={16} />
              Reset
            </button>
            <button
              onClick={handleApply}
              className="flex flex-1 items-center justify-center gap-2 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-red-500"
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
