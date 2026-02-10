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
        "overflow-hidden rounded-md border border-zinc-800 bg-zinc-900/60",
        className
      )}
    >
      {/* Poster Skeleton */}
      <div className="aspect-[2/3] animate-pulse bg-zinc-800/80" />

      {/* Info Skeleton */}
      <div className="p-4">
        {/* Title Skeleton */}
        <div className="mb-2 h-6 w-3/4 animate-pulse rounded bg-zinc-800/80" />

        {/* Metadata Skeleton */}
        <div className="flex items-center gap-3">
          <div className="h-4 w-12 animate-pulse rounded bg-zinc-800/80" />
          <div className="h-4 w-12 animate-pulse rounded bg-zinc-800/80" />
        </div>

        {/* Genres Skeleton */}
        <div className="mt-2 flex gap-1">
          <div className="h-5 w-16 animate-pulse rounded-full bg-zinc-800/80" />
          <div className="h-5 w-20 animate-pulse rounded-full bg-zinc-800/80" />
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
        "flex flex-wrap gap-3 px-4 sm:gap-4 sm:px-6 lg:px-8",
        className
      )}
    >
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="w-[160px] sm:w-[200px] md:w-[220px] lg:w-[240px]"
        >
          <MovieCardSkeleton />
        </div>
      ))}
    </div>
  );
}
