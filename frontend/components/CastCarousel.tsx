"use client";

import Image from "next/image";
import { CastMember } from "@/types/api";
import { cn } from "@/lib/utils";

interface CastCarouselProps {
  cast: CastMember[];
  className?: string;
}

/**
 * CastCarousel component displays cast members in a horizontal scrollable list
 *
 * Features:
 * - Profile images with fallback
 * - Actor name and character name
 * - Horizontal scroll on overflow
 * - Responsive grid layout
 */
export function CastCarousel({ cast, className }: CastCarouselProps) {
  if (!cast || cast.length === 0) {
    return null;
  }

  return (
    <div className={cn("", className)}>
      <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Cast
      </h2>

      <div className="overflow-x-auto">
        <div className="flex gap-4 pb-4">
          {cast.slice(0, 12).map((member) => {
            const profileUrl = member.profile_path
              ? `https://image.tmdb.org/t/p/w185${member.profile_path}`
              : null;

            return (
              <div
                key={member.id}
                className="flex-shrink-0 w-32 group cursor-pointer"
              >
                {/* Profile Image */}
                <div className="relative aspect-[2/3] mb-2 rounded-lg overflow-hidden bg-gray-200 dark:bg-gray-700 shadow-md transition-all duration-300 group-hover:shadow-xl group-hover:scale-105">
                  {profileUrl ? (
                    <Image
                      src={profileUrl}
                      alt={member.name}
                      fill
                      className="object-cover"
                      sizes="128px"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-gray-400 dark:text-gray-500">
                      <span className="text-4xl">👤</span>
                    </div>
                  )}
                </div>

                {/* Actor Name */}
                <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 line-clamp-2 mb-1">
                  {member.name}
                </p>

                {/* Character Name */}
                {member.character_name && (
                  <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
                    {member.character_name}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
