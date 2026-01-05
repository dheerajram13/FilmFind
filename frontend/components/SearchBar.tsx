"use client";

import { Search, X } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  onSearch: (query: string) => void;
  placeholder?: string;
  className?: string;
  autoFocus?: boolean;
}

/**
 * SearchBar component with clear functionality
 *
 * Features:
 * - Search icon
 * - Clear button (shown when query is not empty)
 * - Keyboard support (Escape to clear)
 * - Accessible with proper ARIA labels
 */
export function SearchBar({
  onSearch,
  placeholder = "Search for movies... (e.g., 'dark sci-fi like Interstellar')",
  className,
  autoFocus = false,
}: SearchBarProps) {
  const [query, setQuery] = useState("");

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    onSearch(value);
  };

  const handleClear = () => {
    setQuery("");
    onSearch("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      handleClear();
    }
  };

  return (
    <div className={cn("relative w-full", className)}>
      <div className="relative">
        {/* Search Icon */}
        <Search
          className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400"
          size={20}
        />

        {/* Search Input */}
        <input
          type="text"
          value={query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoFocus={autoFocus}
          className={cn(
            "w-full rounded-lg border border-gray-300 bg-white px-12 py-3",
            "text-gray-900 placeholder-gray-400",
            "focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20",
            "dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500",
            "dark:focus:border-blue-400 dark:focus:ring-blue-400/20",
            "transition-colors duration-200"
          )}
          aria-label="Search for movies"
        />

        {/* Clear Button */}
        {query && (
          <button
            onClick={handleClear}
            className={cn(
              "absolute right-4 top-1/2 -translate-y-1/2",
              "rounded-full p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600",
              "dark:hover:bg-gray-700 dark:hover:text-gray-300",
              "transition-colors duration-200",
              "focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            )}
            aria-label="Clear search"
          >
            <X size={18} />
          </button>
        )}
      </div>
    </div>
  );
}
