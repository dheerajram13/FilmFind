"use client";

import { createContext, useContext, useState, ReactNode } from "react";
import { SearchFilters } from "@/types/api";

interface FilterContextType {
  filters: SearchFilters;
  setFilters: (filters: SearchFilters) => void;
  updateFilter: <K extends keyof SearchFilters>(key: K, value: SearchFilters[K]) => void;
  resetFilters: () => void;
  hasActiveFilters: boolean;
}

const FilterContext = createContext<FilterContextType | undefined>(undefined);

const defaultFilters: SearchFilters = {
  genres: [],
  year_min: undefined,
  year_max: undefined,
  rating_min: undefined,
  rating_max: undefined,
  language: undefined,
  runtime_min: undefined,
  runtime_max: undefined,
  exclude_adult: true,
};

export function FilterProvider({ children }: { children: ReactNode }) {
  const [filters, setFilters] = useState<SearchFilters>(defaultFilters);

  const updateFilter = <K extends keyof SearchFilters>(
    key: K,
    value: SearchFilters[K]
  ) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const resetFilters = () => {
    setFilters(defaultFilters);
  };

  const hasActiveFilters = Object.entries(filters).some(([key, value]) => {
    if (key === "exclude_adult") return false; // Don't count default adult-content toggle as active
    if (Array.isArray(value)) return value.length > 0;
    return value !== undefined && value !== null;
  });

  return (
    <FilterContext.Provider
      value={{
        filters,
        setFilters,
        updateFilter,
        resetFilters,
        hasActiveFilters,
      }}
    >
      {children}
    </FilterContext.Provider>
  );
}

export function useFilters() {
  const context = useContext(FilterContext);
  if (!context) {
    throw new Error("useFilters must be used within a FilterProvider");
  }
  return context;
}
