"use client";

import { Clock } from "lucide-react";
import { cn } from "@/lib/utils";

interface RuntimeFilterProps {
  minRuntime?: number;
  maxRuntime?: number;
  onChange: (minRuntime: number | undefined, maxRuntime: number | undefined) => void;
  className?: string;
}

const RUNTIME_PRESETS = [
  { label: "Any", min: undefined, max: undefined },
  { label: "Short (<90m)", min: undefined, max: 90 },
  { label: "Medium (90-150m)", min: 90, max: 150 },
  { label: "Long (>150m)", min: 150, max: undefined },
];

/**
 * RuntimeFilter component for selecting movie runtime range
 *
 * Features:
 * - Quick preset buttons
 * - Custom min/max input fields
 * - Shows runtime in minutes
 */
export function RuntimeFilter({
  minRuntime,
  maxRuntime,
  onChange,
  className,
}: RuntimeFilterProps) {
  const handleMinChange = (value: string) => {
    const runtime = value ? parseInt(value, 10) : undefined;
    if (runtime !== undefined && (runtime < 0 || runtime > 500)) {
      return;
    }
    onChange(runtime, maxRuntime);
  };

  const handleMaxChange = (value: string) => {
    const runtime = value ? parseInt(value, 10) : undefined;
    if (runtime !== undefined && (runtime < 0 || runtime > 500)) {
      return;
    }
    onChange(minRuntime, runtime);
  };

  const isPresetSelected = (preset: typeof RUNTIME_PRESETS[0]) => {
    return minRuntime === preset.min && maxRuntime === preset.max;
  };

  return (
    <div className={cn("", className)}>
      <label className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
        <Clock size={16} />
        Runtime
      </label>

      {/* Presets */}
      <div className="mb-3 grid grid-cols-2 gap-2">
        {RUNTIME_PRESETS.map((preset) => {
          const isSelected = isPresetSelected(preset);
          return (
            <button
              key={preset.label}
              type="button"
              onClick={() => onChange(preset.min, preset.max)}
              className={cn(
                "rounded-md px-3 py-2 text-xs font-medium transition-all",
                isSelected
                  ? "bg-green-600 text-white hover:bg-green-700"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              )}
            >
              {preset.label}
            </button>
          );
        })}
      </div>

      {/* Custom Range */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs text-gray-600 dark:text-gray-400">
            Min (minutes)
          </label>
          <input
            type="number"
            value={minRuntime ?? ""}
            onChange={(e) => handleMinChange(e.target.value)}
            placeholder="0"
            min={0}
            max={maxRuntime ?? 500}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs text-gray-600 dark:text-gray-400">
            Max (minutes)
          </label>
          <input
            type="number"
            value={maxRuntime ?? ""}
            onChange={(e) => handleMaxChange(e.target.value)}
            placeholder="500"
            min={minRuntime ?? 0}
            max={500}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500"
          />
        </div>
      </div>

      {/* Display current range */}
      {(minRuntime !== undefined || maxRuntime !== undefined) && (
        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
          {minRuntime ?? 0} - {maxRuntime ?? 500} minutes
        </p>
      )}
    </div>
  );
}
