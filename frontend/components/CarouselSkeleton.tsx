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
    <div className={cn("", className)}>
      {/* Title Skeleton */}
      {title ? (
        <h2 className="mb-4 text-2xl font-bold text-gray-900 dark:text-gray-100">
          {title}
        </h2>
      ) : (
        <div className="mb-4 h-8 w-48 animate-pulse rounded bg-gray-300 dark:bg-gray-700" />
      )}

      {/* Carousel Skeleton */}
      <div className="flex gap-4 overflow-hidden pb-4">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="flex-shrink-0 w-48">
            {/* Poster */}
            <div className="aspect-[2/3] animate-pulse rounded-lg bg-gray-300 dark:bg-gray-700 mb-2" />

            {/* Title */}
            <div className="h-5 w-full animate-pulse rounded bg-gray-300 dark:bg-gray-700 mb-2" />

            {/* Metadata */}
            <div className="h-4 w-3/4 animate-pulse rounded bg-gray-300 dark:bg-gray-700" />
          </div>
        ))}
      </div>
    </div>
  );
}
