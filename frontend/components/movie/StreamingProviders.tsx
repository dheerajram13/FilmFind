"use client";

import { Tv } from "lucide-react";
import { cn } from "@/lib/utils";

interface StreamingProvidersProps {
  providers: Record<string, unknown>;
  className?: string;
}

/**
 * StreamingProviders component displays where the movie is available to watch
 *
 * Features:
 * - Lists streaming services by region
 * - Groups by type (stream/rent/buy)
 * - Displays provider names
 */
export function StreamingProviders({ providers, className }: StreamingProvidersProps) {
  if (!providers || Object.keys(providers).length === 0) {
    return null;
  }

  // Parse providers data (format may vary based on backend implementation)
  const providerRegions = Object.entries(providers);

  if (providerRegions.length === 0) {
    return null;
  }

  return (
    <div className={cn("", className)}>
      <h2 className="text-2xl font-semibold text-white mb-4">
        Where to Watch
      </h2>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
        {providerRegions.map(([region, data]) => {
          const regionData = data as Record<string, unknown>;
          const regionName = region.toUpperCase();

          return (
            <div key={region} className="mb-6 last:mb-0">
              <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                <Tv size={20} />
                {regionName}
              </h3>

              <div className="space-y-4">
                {/* Streaming */}
                {regionData.flatrate && Array.isArray(regionData.flatrate) ? (
                  <div>
                    <p className="text-sm font-medium text-zinc-400 mb-2">
                      Stream
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {(regionData.flatrate as Array<{ provider_name: string }>).map((provider, idx) => (
                        <span
                          key={idx}
                          className="rounded-full bg-emerald-500/15 px-3 py-1.5 text-xs font-semibold text-emerald-300"
                        >
                          {String(provider.provider_name)}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}

                {/* Rent */}
                {regionData.rent && Array.isArray(regionData.rent) ? (
                  <div>
                    <p className="text-sm font-medium text-zinc-400 mb-2">
                      Rent
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {(regionData.rent as Array<{ provider_name: string }>).map((provider, idx) => (
                        <span
                          key={idx}
                          className="rounded-full bg-sky-500/15 px-3 py-1.5 text-xs font-semibold text-sky-300"
                        >
                          {String(provider.provider_name)}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}

                {/* Buy */}
                {regionData.buy && Array.isArray(regionData.buy) ? (
                  <div>
                    <p className="text-sm font-medium text-zinc-400 mb-2">
                      Buy
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {(regionData.buy as Array<{ provider_name: string }>).map((provider, idx) => (
                        <span
                          key={idx}
                          className="rounded-full bg-orange-500/15 px-3 py-1.5 text-xs font-semibold text-orange-300"
                        >
                          {String(provider.provider_name)}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>

      <p className="mt-3 text-xs text-zinc-500">
        Streaming availability data provided by TMDB
      </p>
    </div>
  );
}
