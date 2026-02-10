import { Search, Film } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  type?: "no-results" | "start-search";
  query?: string;
  className?: string;
}

/**
 * EmptyState component for different empty scenarios
 *
 * Types:
 * - "no-results": Show when search returns no results
 * - "start-search": Show when user hasn't searched yet
 */
export function EmptyState({
  type = "start-search",
  query,
  className,
}: EmptyStateProps) {
  if (type === "no-results") {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center py-16 text-center",
          className
        )}
      >
        <div className="rounded-full border border-zinc-800 bg-zinc-900/70 p-6 shadow-lg">
          <Search className="text-zinc-400" size={48} />
        </div>
        <h3 className="mt-6 text-xl font-semibold text-white">
          No movies found
        </h3>
        <p className="mt-2 max-w-md text-zinc-400">
          {query ? (
            <>
              We couldn&apos;t find any movies matching <strong>&quot;{query}&quot;</strong>.
              Try different keywords or filters.
            </>
          ) : (
            "Try adjusting your search or filters to find what you're looking for."
          )}
        </p>
        <div className="mt-6 text-sm text-zinc-500">
          <p className="font-medium">Search tips:</p>
          <ul className="mt-2 space-y-1 text-left">
            <li>• Try using movie titles, genres, or themes</li>
            <li>• Use natural language like &quot;dark sci-fi like Interstellar&quot;</li>
            <li>• Reference movies you enjoyed for better recommendations</li>
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-16 text-center",
        className
      )}
    >
      <div className="rounded-full border border-zinc-800 bg-zinc-900/70 p-6 shadow-lg">
        <Film className="text-red-500" size={48} />
      </div>
      <h3 className="mt-6 text-2xl font-semibold text-white">
        Discover Your Next Favorite Movie
      </h3>
      <p className="mt-2 max-w-lg text-zinc-400">
        Use natural language to search for movies. Try describing what you&apos;re in the mood
        for, like &quot;dark sci-fi thriller like Blade Runner&quot; or &quot;heartwarming animated films&quot;.
      </p>
      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        <ExampleQuery text="Movies like Inception" />
        <ExampleQuery text="Dark fantasy adventure" />
        <ExampleQuery text="Romantic comedies from 2020s" />
      </div>
    </div>
  );
}

function ExampleQuery({ text }: { text: string }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 px-4 py-2 text-sm text-zinc-300">
      {text}
    </div>
  );
}
