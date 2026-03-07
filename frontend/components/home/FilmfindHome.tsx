"use client";

import { FormEvent, useState } from "react";

const SAMPLE_CHIPS = [
  '"Slow burn thriller like Parasite"',
  '"Feel-good like Ted Lasso"',
  '"Mind-bending like Inception"',
];

const TRENDING_SEARCHES = [
  "Something like Oppenheimer but lighter",
  "Emotional like Inside Out for adults",
  "Action with a female lead",
  "Horror but no jump scares",
  "Like The Bear but a movie",
];

const NAV_ITEMS = ["Discover", "Movies", "Series", "Watchlist"];

function stripQuotes(text: string): string {
  return text.replace(/^"|"$/g, "");
}

export function FilmfindHome() {
  const [query, setQuery] = useState("");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
  };

  return (
    <div className="ff-shell">
      <div className="ff-blob ff-blob-gold" />
      <div className="ff-blob ff-blob-orange" />

      <main className="ff-page">
        <nav className="ff-home-nav">
          <div className="ff-home-logo">
            Film<span>Find</span>
          </div>

          <div className="ff-home-nav-links">
            {NAV_ITEMS.map((item) => (
              <span key={item} className="ff-home-nav-link">
                {item}
              </span>
            ))}
            <button type="button" className="ff-home-nav-btn">
              60s Mode
            </button>
          </div>
        </nav>

        <section className="ff-home-hero">
          <p className="ff-home-eyebrow">✦ Not a streaming platform — a smarter way to find one</p>

          <h1 className="ff-home-title">
            WHAT WILL YOU
            <span className="outline">WATCH</span>
            <span className="gold">TONIGHT?</span>
          </h1>

          <p className="ff-home-sub">
            Tell FilmFind what you&apos;re in the mood for — in plain English.{" "}
            <em>Get the perfect match in seconds.</em>
          </p>

          <form className="ff-home-search" onSubmit={handleSubmit}>
            <span className="ff-home-search-icon">⌕</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="ff-home-search-input"
              placeholder="e.g., something like Whiplash but a thriller"
              aria-label="Search"
            />
            <button type="submit" className="ff-home-search-btn">
              Search
            </button>
          </form>

          <div className="ff-home-chips">
            {SAMPLE_CHIPS.map((chip) => (
              <button
                key={chip}
                type="button"
                className="ff-home-chip"
                onClick={() => setQuery(stripQuotes(chip))}
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
                onClick={() => setQuery(text)}
              >
                <span className="t-num">{String(index + 1).padStart(2, "0")}</span>
                {text}
              </button>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
