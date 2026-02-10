"use client";

import { cn } from "@/lib/utils";

interface CarouselSkeletonProps {
  title?: string;
  count?: number;
  className?: string;
}

/**
 * CarouselSkeleton component for loading state
 *
 * Features:
 * - Animated skeleton matching MovieCarousel layout
 * - Configurable number of cards
 * - Optional title skeleton
 */
export function CarouselSkeleton({
  title,
  count = 6,
  className,
}: CarouselSkeletonProps) {
  return (
    <div className={cn("relative", className)}>
      {/* Title Skeleton */}
      {title ? (
        <h2 className="mb-6 text-xl font-semibold text-white sm:text-2xl">
          {title}
        </h2>
      ) : (
        <div className="mb-6 h-8 w-48 animate-pulse rounded bg-zinc-800/50" />
      )}

      {/* Carousel Skeleton */}
      <div className="flex gap-3 overflow-hidden pb-6 sm:gap-4">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="w-[160px] flex-shrink-0 sm:w-[200px] md:w-[220px] lg:w-[240px]">
            {/* Poster */}
            <div className="aspect-[2/3] animate-pulse rounded-md bg-zinc-800/50 mb-2" />

            {/* Title */}
            <div className="h-4 w-full animate-pulse rounded bg-zinc-800/30 mb-2" />

            {/* Metadata */}
            <div className="h-3 w-3/4 animate-pulse rounded bg-zinc-800/30" />
          </div>
        ))}
      </div>
    </div>
  );
}
