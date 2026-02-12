"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useRef, useState } from "react";
import { Movie, MovieSearchResult } from "@/types/api";
import { MovieCard } from "@/components/movie/MovieCard";
import { cn } from "@/lib/utils";

interface MovieCarouselProps {
  title?: string;
  movies: (Movie | MovieSearchResult)[];
  showScore?: boolean;
  className?: string;
}

/**
 * Netflix-style MovieCarousel for horizontal scrolling
 *
 * Features:
 * - Dark theme with Netflix-style navigation
 * - Large, prominent arrows visible on hover
 * - Smooth scrolling with fade edges
 * - Larger cards for better visibility
 * - Optimized spacing and layout
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
    const scrollAmount = container.clientWidth * 0.85; // Scroll most of the visible width

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
      {title && (
        <h2 className="mb-6 text-xl font-semibold text-white sm:text-2xl">
          {title}
        </h2>
      )}

      {/* Carousel Container */}
      <div className="group relative">
        {/* Left Arrow - Figma circular glass button */}
        {showLeftArrow && (
          <button
            onClick={() => scroll("left")}
            className={cn(
              "absolute left-3 top-1/2 -translate-y-1/2 z-20",
              "w-10 h-10 rounded-full",
              "bg-black/40 backdrop-blur border border-white/10",
              "opacity-0 transition-all duration-200 group-hover:opacity-100",
              "hover:bg-black/60 hover:scale-110",
              "flex items-center justify-center",
              "focus:outline-none focus:ring-2 focus:ring-white/20"
            )}
            aria-label="Scroll left"
          >
            <ChevronLeft size={20} className="text-white" strokeWidth={2.5} />
          </button>
        )}

        {/* Right Arrow - Figma circular glass button */}
        {showRightArrow && (
          <button
            onClick={() => scroll("right")}
            className={cn(
              "absolute right-3 top-1/2 -translate-y-1/2 z-20",
              "w-10 h-10 rounded-full",
              "bg-black/40 backdrop-blur border border-white/10",
              "opacity-0 transition-all duration-200 group-hover:opacity-100",
              "hover:bg-black/60 hover:scale-110",
              "flex items-center justify-center",
              "focus:outline-none focus:ring-2 focus:ring-white/20"
            )}
            aria-label="Scroll right"
          >
            <ChevronRight size={20} className="text-white" strokeWidth={2.5} />
          </button>
        )}

        {/* Scrollable Movie List */}
        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="flex gap-3 overflow-x-auto overflow-y-visible scrollbar-hide scroll-smooth pb-6 sm:gap-4"
          style={{
            scrollbarWidth: "none",
            msOverflowStyle: "none",
          }}
        >
          {movies.map((movie, index) => (
            <div
              key={movie.id}
              className="flex-shrink-0 w-[160px] sm:w-[200px] md:w-[220px] lg:w-[240px]"
            >
              <MovieCard
                movie={movie}
                showScore={showScore}
                priority={index < 6} // Prioritize first 6 images
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
