"use client";

import { type FormEvent } from "react";
import { Loader2 } from "lucide-react";
import { SAMPLE_CHIPS, TRENDING_SEARCHES } from "@/lib/constants";
import { stripQuotes } from "@/lib/movie-formatters";

interface HomeScreenProps {
  query: string;
  isSearching: boolean;
  onQueryChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onChipClick: (chip: string) => void;
  onTrendingClick: (text: string) => void;
  onOpenSixtyMode: () => void;
}

export function HomeScreen({
  query,
  isSearching,
  onQueryChange,
  onSubmit,
  onChipClick,
  onTrendingClick,
  onOpenSixtyMode,
}: HomeScreenProps) {
  return (
    <>
      <nav className="ff-home-nav">
        <div className="ff-home-logo">
          Film<span>Find</span>
        </div>
        <div className="ff-home-nav-links" />
      </nav>

      <section className="ff-home-hero">
        <p className="ff-home-eyebrow">✦ Not a streaming platform — a smarter way to find one</p>

        <h1 className="ff-home-title">
          DESCRIBE IT.
          <span className="outline">FIND IT.</span>
          WATCH IT.
        </h1>

        <p className="ff-home-sub">
          Tell FilmFind what you&apos;re in the mood for — in plain English.{" "}
          <em>Get the perfect match in seconds.</em>
        </p>

        <form className="ff-home-search" onSubmit={onSubmit}>
          <span className="ff-home-search-icon">◈</span>
          <input
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            className="ff-home-search-input"
            placeholder="Like Stranger Things but more horror and less nostalgia..."
            aria-label="Search"
          />
          <button type="submit" className="ff-home-search-btn">
            {isSearching ? <Loader2 size={14} className="ff-spin" /> : "Find it →"}
          </button>
        </form>

        <div className="ff-home-or">
          <span className="ff-home-or-line" />
          <span className="ff-home-or-text">OR</span>
          <span className="ff-home-or-line" />
        </div>

        <div className="ff-quick-card">
          <div className="ff-quick-accent" />
          <div className="ff-quick-main">
            <div className="ff-quick-icon">⚡</div>
            <div className="ff-quick-copy">
              <div className="ff-quick-head">
                <p className="ff-quick-title">Can&apos;t decide what to watch?</p>
                <span className="ff-quick-badge">60 sec</span>
              </div>
              <p className="ff-quick-sub">
                Answer 3 quick questions. Get one perfect pick. No scrolling required.
              </p>
            </div>
          </div>
          <button type="button" className="ff-quick-start" onClick={onOpenSixtyMode}>
            Start →
          </button>
        </div>

        <div className="ff-home-chips">
          {SAMPLE_CHIPS.map((chip) => (
            <button
              key={chip}
              type="button"
              className="ff-home-chip"
              onClick={() => onChipClick(stripQuotes(chip))}
            >
              {chip}
            </button>
          ))}
        </div>
      </section>

      <section className="ff-home-trending">
        <div className="ff-home-trending-label">
          Trending searches this week
          <span>View all →</span>
        </div>

        <div className="ff-home-trending-pills">
          {TRENDING_SEARCHES.map((text, index) => (
            <button
              key={text}
              type="button"
              className="ff-home-trending-pill"
              onClick={() => onTrendingClick(text)}
            >
              <span className="t-num">{String(index + 1).padStart(2, "0")}</span>
              {text}
            </button>
          ))}
        </div>
      </section>
    </>
  );
}
