"use client";

import { type FormEvent, useState } from "react";
import { Loader2 } from "lucide-react";
import { ResultCard } from "@/components/home/cards/ResultCard";
import { FiltersSidebar } from "@/components/home/filters/FiltersSidebar";
import type { MovieSearchResult } from "@/types/api";

interface ResultsScreenProps {
  query: string;
  submittedQuery: string;
  isSearching: boolean;
  filteredResults: MovieSearchResult[];
  selectedStreaming: string[];
  selectedGenres: string[];
  selectedContentTypes: string[];
  minRating: number;
  minYear: number;
  onQueryChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onResetToHome: () => void;
  onOpenDetails: (movie: MovieSearchResult) => void;
  onToggleStreaming: (service: string) => void;
  onToggleGenre: (genre: string) => void;
  onToggleContentType: (ct: string) => void;
  onChangeMinRating: (value: number) => void;
  onChangeMinYear: (value: number) => void;
  onClearFilters: () => void;
}

export function ResultsScreen({
  query,
  submittedQuery,
  isSearching,
  filteredResults,
  selectedStreaming,
  selectedGenres,
  selectedContentTypes,
  minRating,
  minYear,
  onQueryChange,
  onSubmit,
  onResetToHome,
  onOpenDetails,
  onToggleStreaming,
  onToggleGenre,
  onToggleContentType,
  onChangeMinRating,
  onChangeMinYear,
  onClearFilters,
}: ResultsScreenProps) {
  const [expandedCardId, setExpandedCardId] = useState<number | null>(null);

  const handleToggleExpand = (id: number): void => {
    setExpandedCardId((prev) => (prev === id ? null : id));
  };

  return (
    <>
      <nav className="ff-results-nav">
        <button type="button" className="ff-results-logo" onClick={onResetToHome}>
          Film<span>Find</span>
        </button>

        <form className="ff-results-search" onSubmit={onSubmit}>
          <span className="ff-home-search-icon">⌕</span>
          <input
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            className="ff-home-search-input"
            aria-label="Search query"
          />
          <button type="submit" className="ff-home-search-btn">
            {isSearching ? <Loader2 size={14} className="ff-spin" /> : "Search"}
          </button>
        </form>

        <div className="ff-results-right">
          <span>Watchlist</span>
          <div className="ff-avatar" />
        </div>
      </nav>

      <div className="ff-results-layout">
        <FiltersSidebar
          selectedStreaming={selectedStreaming}
          selectedGenres={selectedGenres}
          selectedContentTypes={selectedContentTypes}
          minRating={minRating}
          minYear={minYear}
          onToggleStreaming={onToggleStreaming}
          onToggleGenre={onToggleGenre}
          onToggleContentType={onToggleContentType}
          onChangeMinRating={onChangeMinRating}
          onChangeMinYear={onChangeMinYear}
          onClearFilters={onClearFilters}
        />

        <section className="ff-results-area">
          <div className="ff-results-topbar">
            <div className="ff-results-query">
              <span className="ff-query-label">Query</span>
              <span className="ff-query-text">&quot;{submittedQuery}&quot;</span>
            </div>
            <div className="ff-results-meta">
              <span>{filteredResults.length}</span> matches found
            </div>
          </div>

          {isSearching && (
            <div className="ff-loading-row">
              <Loader2 size={16} className="ff-spin" />
              Finding the best matches...
            </div>
          )}

          {!isSearching && filteredResults.length > 0 && (
            <div className="ff-results-grid">
              {filteredResults.map((movie, index) => (
                <ResultCard
                  key={movie.id}
                  movie={movie}
                  rank={index + 1}
                  query={submittedQuery}
                  selectedStreaming={selectedStreaming}
                  expandedId={expandedCardId}
                  onToggleExpand={handleToggleExpand}
                  onOpenDetails={onOpenDetails}
                />
              ))}
            </div>
          )}

          {!isSearching && filteredResults.length === 0 && (
            <p className="ff-empty">
              We couldn&apos;t find an exact match for this query. Try broadening your filters.
            </p>
          )}
        </section>
      </div>
    </>
  );
}
