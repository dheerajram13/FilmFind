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
      <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Where to Watch
      </h2>

      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-md">
        {providerRegions.map(([region, data]) => {
          const regionData = data as Record<string, unknown>;
          const regionName = region.toUpperCase();

          return (
            <div key={region} className="mb-6 last:mb-0">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
                <Tv size={20} />
                {regionName}
              </h3>

              <div className="space-y-4">
                {/* Streaming */}
                {regionData.flatrate && Array.isArray(regionData.flatrate) ? (
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
                      Stream
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {(regionData.flatrate as Array<{ provider_name: string }>).map((provider, idx) => (
                        <span
                          key={idx}
                          className="rounded-md bg-green-100 px-3 py-1.5 text-sm font-medium text-green-700 dark:bg-green-900/30 dark:text-green-300"
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
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
                      Rent
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {(regionData.rent as Array<{ provider_name: string }>).map((provider, idx) => (
                        <span
                          key={idx}
                          className="rounded-md bg-blue-100 px-3 py-1.5 text-sm font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
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
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
                      Buy
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {(regionData.buy as Array<{ provider_name: string }>).map((provider, idx) => (
                        <span
                          key={idx}
                          className="rounded-md bg-purple-100 px-3 py-1.5 text-sm font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-300"
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

      <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
        Streaming availability data provided by TMDB
      </p>
    </div>
  );
}
