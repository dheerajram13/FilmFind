import { cn } from "@/lib/utils";

interface MovieCardSkeletonProps {
  className?: string;
}

/**
 * MovieCardSkeleton - Loading placeholder for MovieCard
 *
 * Displays an animated skeleton while movie data is loading
 */
export function MovieCardSkeleton({ className }: MovieCardSkeletonProps) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-lg bg-white shadow-md dark:bg-gray-800",
        className
      )}
    >
      {/* Poster Skeleton */}
      <div className="aspect-[2/3] animate-pulse bg-gray-200 dark:bg-gray-700" />

      {/* Info Skeleton */}
      <div className="p-4">
        {/* Title Skeleton */}
        <div className="mb-2 h-6 w-3/4 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />

        {/* Metadata Skeleton */}
        <div className="flex items-center gap-3">
          <div className="h-4 w-12 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
          <div className="h-4 w-12 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
        </div>

        {/* Genres Skeleton */}
        <div className="mt-2 flex gap-1">
          <div className="h-5 w-16 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700" />
          <div className="h-5 w-20 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700" />
        </div>
      </div>
    </div>
  );
}

interface MovieGridSkeletonProps {
  count?: number;
  className?: string;
}

/**
 * MovieGridSkeleton - Grid of loading skeletons
 *
 * @param count - Number of skeleton cards to display (default: 12)
 */
export function MovieGridSkeleton({ count = 12, className }: MovieGridSkeletonProps) {
  return (
    <div
      className={cn(
        "grid gap-6",
        "grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6",
        className
      )}
    >
      {Array.from({ length: count }).map((_, index) => (
        <MovieCardSkeleton key={index} />
      ))}
    </div>
  );
}
