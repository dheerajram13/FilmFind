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
        {/* Left Arrow - Netflix style */}
        {showLeftArrow && (
          <button
            onClick={() => scroll("left")}
            className={cn(
              "absolute left-0 top-0 z-20 flex h-full w-12 items-center justify-center",
              "bg-black/50 backdrop-blur-sm",
              "opacity-0 transition-all duration-300 group-hover:opacity-100",
              "hover:bg-black/70",
              "focus:outline-none focus:ring-2 focus:ring-white/50"
            )}
            aria-label="Scroll left"
          >
            <ChevronLeft size={40} className="text-white drop-shadow-lg" />
          </button>
        )}

        {/* Right Arrow - Netflix style */}
        {showRightArrow && (
          <button
            onClick={() => scroll("right")}
            className={cn(
              "absolute right-0 top-0 z-20 flex h-full w-12 items-center justify-center",
              "bg-black/50 backdrop-blur-sm",
              "opacity-0 transition-all duration-300 group-hover:opacity-100",
              "hover:bg-black/70",
              "focus:outline-none focus:ring-2 focus:ring-white/50"
            )}
            aria-label="Scroll right"
          >
            <ChevronRight size={40} className="text-white drop-shadow-lg" />
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
