"use client";

import {
  CONTENT_TYPE_OPTIONS,
  GENRE_OPTIONS,
  RATING_MAX,
  RATING_MIN,
  STREAMING_OPTIONS,
  YEAR_MIN,
} from "@/lib/constants";

interface FiltersSidebarProps {
  selectedStreaming: string[];
  selectedGenres: string[];
  selectedContentTypes: string[];
  minRating: number;
  minYear: number;
  onToggleStreaming: (service: string) => void;
  onToggleGenre: (genre: string) => void;
  onToggleContentType: (ct: string) => void;
  onChangeMinRating: (value: number) => void;
  onChangeMinYear: (value: number) => void;
  onClearFilters: () => void;
}

export function FiltersSidebar({
  selectedStreaming,
  selectedGenres,
  selectedContentTypes,
  minRating,
  minYear,
  onToggleStreaming,
  onToggleGenre,
  onToggleContentType,
  onChangeMinRating,
  onChangeMinYear,
  onClearFilters,
}: FiltersSidebarProps) {
  const currentYear = new Date().getFullYear();

  return (
    <aside className="ff-filters-sidebar">
      <div className="ff-filter-title">
        Filters
        <button type="button" onClick={onClearFilters}>
          Clear
        </button>
      </div>

      <div className="ff-filter-group">
        <div className="ff-filter-group-label">Streaming on</div>
        {STREAMING_OPTIONS.map((service) => {
          const checked = selectedStreaming.includes(service);
          return (
            <button
              key={service}
              type="button"
              className="ff-filter-option"
              onClick={() => onToggleStreaming(service)}
            >
              <span className={`ff-filter-check ${checked ? "checked" : ""}`}>
                {checked ? "✓" : ""}
              </span>
              {service}
            </button>
          );
        })}
      </div>

      <div className="ff-filter-group">
        <div className="ff-filter-group-label">Genre</div>
        {GENRE_OPTIONS.map((genre) => {
          const checked = selectedGenres.includes(genre);
          return (
            <button
              key={genre}
              type="button"
              className="ff-filter-option"
              onClick={() => onToggleGenre(genre)}
            >
              <span className={`ff-filter-check ${checked ? "checked" : ""}`}>
                {checked ? "✓" : ""}
              </span>
              {genre}
            </button>
          );
        })}
      </div>

      <div className="ff-filter-group">
        <div className="ff-filter-group-label">Content type</div>
        {CONTENT_TYPE_OPTIONS.map((ct) => {
          const checked = selectedContentTypes.includes(ct);
          return (
            <button
              key={ct}
              type="button"
              className="ff-filter-option"
              onClick={() => onToggleContentType(ct)}
            >
              <span className={`ff-filter-check ${checked ? "checked" : ""}`}>
                {checked ? "✓" : ""}
              </span>
              {ct}
            </button>
          );
        })}
      </div>

      <div className="ff-filter-group">
        <div className="ff-filter-group-label">IMDb Rating</div>
        <input
          type="range"
          min={RATING_MIN}
          max={RATING_MAX}
          step={0.1}
          value={minRating}
          onChange={(e) => onChangeMinRating(Number(e.target.value))}
          className="ff-range"
        />
        <div className="ff-range-labels">
          <span>{minRating.toFixed(1)}+</span>
          <span>{RATING_MAX}</span>
        </div>
      </div>

      <div className="ff-filter-group">
        <div className="ff-filter-group-label">Release Year</div>
        <input
          type="range"
          min={YEAR_MIN}
          max={currentYear}
          step={1}
          value={minYear}
          onChange={(e) => onChangeMinYear(Number(e.target.value))}
          className="ff-range"
        />
        <div className="ff-range-labels">
          <span>{minYear}</span>
          <span>{currentYear}</span>
        </div>
      </div>
    </aside>
  );
}
