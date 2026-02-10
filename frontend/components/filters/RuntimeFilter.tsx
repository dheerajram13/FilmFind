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
      <label className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
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
                  ? "bg-red-600 text-white hover:bg-red-500"
                  : "border border-zinc-800 bg-zinc-900/60 text-zinc-300 hover:bg-zinc-800"
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
          <label className="mb-1 block text-xs text-zinc-500">
            Min (minutes)
          </label>
          <input
            type="number"
            value={minRuntime ?? ""}
            onChange={(e) => handleMinChange(e.target.value)}
            placeholder="0"
            min={0}
            max={maxRuntime ?? 500}
            className="w-full rounded-md border border-zinc-800 bg-zinc-900/60 px-3 py-2 text-sm text-white placeholder-zinc-500 focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs text-zinc-500">
            Max (minutes)
          </label>
          <input
            type="number"
            value={maxRuntime ?? ""}
            onChange={(e) => handleMaxChange(e.target.value)}
            placeholder="500"
            min={minRuntime ?? 0}
            max={500}
            className="w-full rounded-md border border-zinc-800 bg-zinc-900/60 px-3 py-2 text-sm text-white placeholder-zinc-500 focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
          />
        </div>
      </div>

      {/* Display current range */}
      {(minRuntime !== undefined || maxRuntime !== undefined) && (
        <p className="mt-2 text-xs text-zinc-500">
          {minRuntime ?? 0} - {maxRuntime ?? 500} minutes
        </p>
      )}
    </div>
  );
}
