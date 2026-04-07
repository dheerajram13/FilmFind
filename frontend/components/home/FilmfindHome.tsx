"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useSearch } from "@/hooks/useSearch";
import { useFilters } from "@/hooks/useFilters";
import { HomeScreen } from "@/components/home/HomeScreen";
import { ResultsScreen } from "@/components/home/ResultsScreen";
import { DetailScreen } from "@/components/home/DetailScreen";

// Lazy-load: uses window/navigator APIs — not SSR-compatible
const SixtySecondMode = dynamic(
  () => import("@/components/home/SixtySecondMode").then((m) => ({ default: m.SixtySecondMode })),
  { ssr: false }
);

export function FilmfindHome() {
  const search = useSearch();
  const filters = useFilters(search.results);
  const [sixtyModeOpen, setSixtyModeOpen] = useState(false);

  // Detail view: prefer explicitly selected movie, then fall back to first filtered result
  const detailMovie =
    search.selectedMovie ?? filters.filteredResults[0] ?? search.results[0] ?? null;

  const similarPicks = (filters.filteredResults.length > 0 ? filters.filteredResults : search.results)
    .filter((m) => (detailMovie ? m.id !== detailMovie.id : true))
    .slice(0, 4);

  return (
    <div className="ff-shell">
      <div className="ff-blob ff-blob-gold" />
      <div className="ff-blob ff-blob-orange" />

      <main className="ff-page">
        {search.activeScreen === "home" && (
          <HomeScreen
            query={search.query}
            isSearching={search.isSearching}
            onQueryChange={search.setQuery}
            onSubmit={search.handleSubmit}
            onChipClick={(chip) => void search.runSearch(chip)}
            onTrendingClick={(text) => {
              search.setQuery(text);
              void search.runSearch(text);
            }}
            onOpenSixtyMode={() => setSixtyModeOpen(true)}
          />
        )}

        {search.activeScreen === "results" && (
          <ResultsScreen
            query={search.query}
            submittedQuery={search.submittedQuery}
            isSearching={search.isSearching}
            filteredResults={filters.filteredResults}
            selectedStreaming={filters.selectedStreaming}
            selectedGenres={filters.selectedGenres}
            selectedContentTypes={filters.selectedContentTypes}
            minRating={filters.minRating}
            minYear={filters.minYear}
            onQueryChange={search.setQuery}
            onSubmit={search.handleSubmit}
            onResetToHome={search.resetToHome}
            onOpenDetails={search.openDetail}
            onToggleStreaming={filters.toggleStreaming}
            onToggleGenre={filters.toggleGenre}
            onToggleContentType={filters.toggleContentType}
            onChangeMinRating={filters.setMinRating}
            onChangeMinYear={filters.setMinYear}
            onClearFilters={filters.clearFilters}
          />
        )}

        {search.activeScreen === "detail" && (
          <DetailScreen
            detailMovie={detailMovie}
            submittedQuery={search.submittedQuery}
            similarPicks={similarPicks}
            selectedStreaming={filters.selectedStreaming}
            onBackToResults={search.backToResults}
            onOpenDetails={search.openDetail}
          />
        )}

        {search.error && <p className="ff-error">{search.error}</p>}
      </main>

      <SixtySecondMode
        open={sixtyModeOpen}
        onClose={() => setSixtyModeOpen(false)}
        onApplyQuery={(modeQuery) => {
          setSixtyModeOpen(false);
          void search.runSearch(modeQuery);
        }}
      />
    </div>
  );
}
