"use client";

import { Search, X, Loader2 } from "lucide-react";
import { useState, useRef } from "react";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  value: string;
  onChange: (query: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  className?: string;
  id?: string;
}

/**
 * Interactive Animated SearchBar
 *
 * Features:
 * - Smooth icon transitions (search ↔ close)
 * - Background glow on focus
 * - Animated loading spinner
 * - Enhanced shadows and micro-interactions
 * - Clean, modern design
 */
export function SearchBar({
  value,
  onChange,
  isLoading = false,
  placeholder = "Search movies, shows, or actors...",
  className,
  id,
}: SearchBarProps) {
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const isTyping = value.trim().length > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
  };

  const handleClear = () => {
    onChange("");
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      handleClear();
    }
  };

  return (
    <form onSubmit={handleSubmit} className={cn("relative w-full", className)}>
      <div
        className={cn(
          "relative flex items-center mx-auto",
          "h-11 w-[380px]",
          "rounded-md",
          "border bg-white shadow-sm",
          "transition-all duration-300",
          isFocused
            ? "shadow-md border-zinc-300"
            : "border-zinc-200 hover:border-zinc-300"
        )}
      >
        {/* Icon Container - with swap animation */}
        <div className="relative flex items-center justify-center w-10 flex-shrink-0">
          {/* Search Icon */}
          <div
            className={cn(
              "absolute left-3 transition-all duration-300 ease-[cubic-bezier(0.694,0.048,0.335,1.000)]",
              isFocused || isTyping
                ? "opacity-0 scale-0 translate-x-4"
                : "opacity-100 scale-100 translate-x-0"
            )}
          >
            <Search size={18} className="text-zinc-400" strokeWidth={2} />
          </div>

          {/* Close Icon - appears when focused/typing */}
          <div
            className={cn(
              "absolute left-3 transition-all duration-300 ease-[cubic-bezier(0.694,0.048,0.335,1.000)]",
              isFocused || isTyping
                ? "opacity-100 scale-100 translate-x-0"
                : "opacity-0 scale-0 -translate-x-4"
            )}
          >
            <button
              type="button"
              onClick={handleClear}
              className="p-0.5 rounded-sm hover:bg-zinc-100 transition-colors"
              aria-label="Clear search"
            >
              <X size={16} className="text-zinc-500" strokeWidth={2.5} />
            </button>
          </div>
        </div>

        {/* Input */}
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
          className={cn(
            "flex-1 bg-transparent px-2 py-2",
            "text-sm text-zinc-900 placeholder:text-zinc-400",
            "outline-none"
          )}
          aria-label="Search movies"
          autoComplete="off"
          spellCheck="false"
        />

        {/* Loading or Search Button */}
        <div className="flex items-center pr-3">
          {isLoading ? (
            <Loader2 size={16} className="animate-spin text-zinc-400" strokeWidth={2} />
          ) : value.trim() ? (
            <button
              type="submit"
              className={cn(
                "p-1.5 rounded-md",
                "bg-red-600 hover:bg-red-700",
                "text-white",
                "transition-colors duration-150"
              )}
              aria-label="Search"
            >
              <Search size={14} strokeWidth={2.5} />
            </button>
          ) : null}
        </div>
      </div>
    </form>
  );
}
