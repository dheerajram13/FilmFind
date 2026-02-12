"use client";

import { useState, useRef } from "react";
import { motion } from "framer-motion";
import { Loader2, Search, SlidersHorizontal, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface StickySearchBarProps {
  value: string;
  onChange: (query: string) => void;
  onSearch?: () => void;
  onFilterClick: () => void;
  isLoading?: boolean;
  filterCount?: number;
  placeholder?: string;
  className?: string;
}

/**
 * StickySearchBar - compact search bar for results view
 *
 * Features:
 * - Sticky top positioning
 * - Filter button with active count
 * - Glow on focus + animated accent line
 * - Gradient search button
 */
export function StickySearchBar({
  value,
  onChange,
  onSearch,
  onFilterClick,
  isLoading = false,
  filterCount = 0,
  placeholder = "Search for movies and shows...",
  className,
}: StickySearchBarProps) {
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch?.();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onChange("");
      inputRef.current?.blur();
    }
  };

  return (
    <motion.div
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4, type: "spring", damping: 20 }}
      className={cn(
        "sticky top-0 z-30 border-b border-zinc-800/60 bg-black/80 backdrop-blur-xl",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-6 py-4">
        <form onSubmit={handleSubmit} className="flex items-center gap-3">
          {/* Filter Button */}
          <motion.button
            type="button"
            onClick={onFilterClick}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="relative flex-shrink-0 rounded-xl border border-zinc-800/70 bg-zinc-900/90 p-3 transition-all duration-200 hover:border-zinc-700 hover:bg-zinc-800"
            aria-label="Open filters"
          >
            <SlidersHorizontal className="w-5 h-5 text-zinc-400" />
            {filterCount > 0 && (
              <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-purple-600 text-xs font-semibold text-white">
                {filterCount}
              </span>
            )}
          </motion.button>

          {/* Search Input */}
          <div className="relative flex-1">
            {/* Glow effect */}
            <div
              className={cn(
                "absolute inset-0 rounded-xl bg-gradient-to-r from-purple-600/20 via-blue-600/20 to-purple-600/20 blur-lg transition-opacity duration-300",
                isFocused ? "opacity-100" : "opacity-0"
              )}
            />

            {/* Input container */}
            <div
              className={cn(
                "relative overflow-hidden rounded-xl border border-zinc-800/60 bg-zinc-900/90 backdrop-blur-xl",
                isFocused && "border-purple-500/40"
              )}
            >
              <div className="flex items-center px-4 py-3">
                <Search className="mr-3 h-5 w-5 flex-shrink-0 text-zinc-400" />

                <input
                  ref={inputRef}
                  type="text"
                  value={value}
                  onChange={(e) => onChange(e.target.value)}
                  onFocus={() => setIsFocused(true)}
                  onBlur={() => setIsFocused(false)}
                  onKeyDown={handleKeyDown}
                  placeholder={placeholder}
                  className="flex-1 bg-transparent text-white placeholder:text-zinc-500 outline-none"
                  aria-label="Search movies"
                  autoComplete="off"
                  spellCheck="false"
                />

                <motion.button
                  type="submit"
                  disabled={isLoading}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className={cn(
                    "ml-3 flex flex-shrink-0 items-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-5 py-2 font-semibold text-white shadow-lg shadow-purple-500/30 transition-all duration-300 hover:shadow-purple-500/50",
                    "disabled:cursor-not-allowed disabled:opacity-60"
                  )}
                >
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}
                  <span className="hidden sm:inline">Search</span>
                </motion.button>
              </div>

              {/* Animated accent line */}
              <motion.div
                animate={{ x: isFocused ? [0, 1000] : 0 }}
                transition={{
                  duration: 2,
                  repeat: isFocused ? Infinity : 0,
                  ease: "linear",
                }}
                className="absolute bottom-0 left-0 h-[2px] w-24 bg-gradient-to-r from-transparent via-purple-500 to-transparent"
              />
            </div>
          </div>
        </form>
      </div>
    </motion.div>
  );
}
