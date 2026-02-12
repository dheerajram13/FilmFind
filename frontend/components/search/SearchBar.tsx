"use client";

import { Search, Sparkles, Loader2 } from "lucide-react";
import { useState, useRef } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  value: string;
  onChange: (query: string) => void;
  onSearch?: () => void;
  isLoading?: boolean;
  placeholder?: string;
  className?: string;
  id?: string;
}

/**
 * Premium SearchBar - Figma Design Implementation
 *
 * Features:
 * - Glass morphism background (dark translucent)
 * - Purple glow on focus
 * - Constrained width (max-w-2xl)
 * - 56px height (h-14)
 * - Gradient search button
 * - Smooth transitions
 */
export function SearchBar({
  value,
  onChange,
  onSearch,
  isLoading = false,
  placeholder = "Describe the movie or show you're looking for...",
  className,
  id,
}: SearchBarProps) {
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
    <form onSubmit={handleSubmit} className={cn("relative w-full max-w-3xl mx-auto", className)}>
      {/* Glow effect on focus */}
      <motion.div
        className="absolute inset-0 rounded-2xl bg-gradient-to-r from-purple-600/20 via-blue-600/20 to-purple-600/20 blur-xl"
        animate={{ opacity: isFocused ? 1 : 0 }}
        transition={{ duration: 0.3 }}
      />

      {/* Search input container */}
      <div
        className={cn(
          "relative bg-zinc-900/90 backdrop-blur-xl border border-zinc-800/50 rounded-2xl overflow-hidden shadow-2xl",
          "transition-all duration-300",
          isFocused && "border-purple-500/30"
        )}
      >
        <div className="flex items-center px-6 py-5">
          <Search className="w-6 h-6 text-zinc-400 mr-4 flex-shrink-0" />

          <input
            ref={inputRef}
            id={id}
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="flex-1 bg-transparent text-white placeholder:text-zinc-500 outline-none text-lg"
            aria-label="Search movies"
            autoComplete="off"
            spellCheck="false"
          />

          <button
            type="submit"
            disabled={isLoading}
            className={cn(
              "ml-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white px-7 py-3.5 rounded-xl font-semibold text-base",
              "flex items-center gap-2 shadow-lg shadow-purple-500/30 hover:shadow-purple-500/50",
              "transition-all duration-300 hover:scale-105 active:scale-95",
              "disabled:opacity-60 disabled:cursor-not-allowed"
            )}
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Sparkles className="w-5 h-5" />
            )}
            <span>Search</span>
          </button>
        </div>

        {/* Animated purple accent line at bottom */}
        <motion.div
          className="absolute bottom-0 left-8 h-[2px] bg-gradient-to-r from-purple-500 via-blue-500 to-transparent"
          animate={{
            width: isFocused ? "112px" : "0px",
            opacity: isFocused ? 1 : 0
          }}
          transition={{ duration: 0.3 }}
        />
      </div>
    </form>
  );
}
