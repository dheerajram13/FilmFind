"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useRef, useState } from "react";
import { Movie, MovieSearchResult } from "@/types/api";
import { MovieCard } from "./MovieCard";
import { cn } from "@/lib/utils";

interface MovieCarouselProps {
  title: string;
  movies: (Movie | MovieSearchResult)[];
  showScore?: boolean;
  className?: string;
}

/**
 * MovieCarousel component for horizontal scrolling movie lists
 *
 * Features:
 * - Horizontal scroll with smooth animations
 * - Navigation arrows (left/right)
 * - Hide arrows when at start/end
 * - Responsive: snap scrolling on mobile, smooth scroll on desktop
 * - Reuses MovieCard component
 */
export function MovieCarousel({
  title,
  movies,
  showScore = false,
  className,
}: MovieCarouselProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showLeftArrow, setShowLeftArrow] = useState(false);
  const [showRightArrow, setShowRightArrow] = useState(true);

  const scroll = (direction: "left" | "right") => {
    if (!scrollContainerRef.current) return;

    const container = scrollContainerRef.current;
    const scrollAmount = container.clientWidth * 0.8; // Scroll 80% of container width

    const newScrollLeft =
      direction === "left"
        ? container.scrollLeft - scrollAmount
        : container.scrollLeft + scrollAmount;

    container.scrollTo({
      left: newScrollLeft,
      behavior: "smooth",
    });
  };

  const handleScroll = () => {
    if (!scrollContainerRef.current) return;

    const container = scrollContainerRef.current;
    const { scrollLeft, scrollWidth, clientWidth } = container;

    // Show/hide arrows based on scroll position
    setShowLeftArrow(scrollLeft > 10);
    setShowRightArrow(scrollLeft < scrollWidth - clientWidth - 10);
  };

  if (!movies || movies.length === 0) {
    return null;
  }

  return (
    <div className={cn("relative", className)}>
      {/* Title */}
      <h2 className="mb-4 text-2xl font-bold text-gray-900 dark:text-gray-100">
        {title}
      </h2>

      {/* Carousel Container */}
      <div className="relative group">
        {/* Left Arrow */}
        {showLeftArrow && (
          <button
            onClick={() => scroll("left")}
            className="absolute left-0 top-1/2 z-10 -translate-y-1/2 rounded-full bg-white/90 p-2 shadow-lg opacity-0 transition-opacity group-hover:opacity-100 hover:bg-white dark:bg-gray-800/90 dark:hover:bg-gray-800"
            aria-label="Scroll left"
          >
            <ChevronLeft size={24} className="text-gray-900 dark:text-gray-100" />
          </button>
        )}

        {/* Right Arrow */}
        {showRightArrow && (
          <button
            onClick={() => scroll("right")}
            className="absolute right-0 top-1/2 z-10 -translate-y-1/2 rounded-full bg-white/90 p-2 shadow-lg opacity-0 transition-opacity group-hover:opacity-100 hover:bg-white dark:bg-gray-800/90 dark:hover:bg-gray-800"
            aria-label="Scroll right"
          >
            <ChevronRight size={24} className="text-gray-900 dark:text-gray-100" />
          </button>
        )}

        {/* Scrollable Movie List */}
        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="flex gap-4 overflow-x-auto scrollbar-hide pb-4 scroll-smooth snap-x snap-mandatory"
          style={{
            scrollbarWidth: "none",
            msOverflowStyle: "none",
          }}
        >
          {movies.map((movie) => (
            <div
              key={movie.id}
              className="flex-shrink-0 w-48 snap-start"
            >
              <MovieCard movie={movie} showScore={showScore} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
