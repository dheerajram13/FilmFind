"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface LanguageSelectorProps {
  selectedLanguage?: string;
  onChange: (language: string | undefined) => void;
  className?: string;
}

// Common languages with ISO 639-1 codes
const LANGUAGES = [
  { code: "en", name: "English" },
  { code: "es", name: "Spanish" },
  { code: "fr", name: "French" },
  { code: "de", name: "German" },
  { code: "it", name: "Italian" },
  { code: "ja", name: "Japanese" },
  { code: "ko", name: "Korean" },
  { code: "zh", name: "Chinese" },
  { code: "hi", name: "Hindi" },
  { code: "ru", name: "Russian" },
  { code: "pt", name: "Portuguese" },
  { code: "ar", name: "Arabic" },
];

/**
 * LanguageSelector component for choosing a single language
 *
 * Features:
 * - Grid layout with language buttons
 * - Visual selection state with checkmarks
 * - Single-select support
 * - Uses ISO 639-1 language codes
 */
export function LanguageSelector({
  selectedLanguage,
  onChange,
  className,
}: LanguageSelectorProps) {
  const toggleLanguage = (code: string) => {
    onChange(selectedLanguage === code ? undefined : code);
  };

  return (
    <div className={cn("", className)}>
      <label className="mb-3 block text-sm font-semibold text-white">
        Languages
      </label>
      <div className="grid grid-cols-2 gap-2">
        {LANGUAGES.map((language) => {
          const isSelected = selectedLanguage === language.code;
          return (
            <button
              key={language.code}
              type="button"
              onClick={() => toggleLanguage(language.code)}
              className={cn(
                "flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-all",
                isSelected
                  ? "bg-red-600 text-white hover:bg-red-500"
                  : "border border-zinc-800 bg-zinc-900/60 text-zinc-300 hover:bg-zinc-800"
              )}
            >
              <span>{language.name}</span>
              {isSelected && <Check size={16} className="ml-2" />}
            </button>
          );
        })}
      </div>
      {selectedLanguage && (
        <p className="mt-2 text-xs text-zinc-500">
          {
            LANGUAGES.find((language) => language.code === selectedLanguage)?.name
          } selected
        </p>
      )}
    </div>
  );
}
