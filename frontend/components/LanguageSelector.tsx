"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface LanguageSelectorProps {
  selectedLanguages: string[];
  onChange: (languages: string[]) => void;
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
 * LanguageSelector component for multi-selecting languages
 *
 * Features:
 * - Grid layout with language buttons
 * - Visual selection state with checkmarks
 * - Multi-select support
 * - Uses ISO 639-1 language codes
 */
export function LanguageSelector({
  selectedLanguages,
  onChange,
  className,
}: LanguageSelectorProps) {
  const toggleLanguage = (code: string) => {
    if (selectedLanguages.includes(code)) {
      onChange(selectedLanguages.filter((lang) => lang !== code));
    } else {
      onChange([...selectedLanguages, code]);
    }
  };

  return (
    <div className={cn("", className)}>
      <label className="mb-3 block text-sm font-semibold text-gray-900 dark:text-gray-100">
        Languages
      </label>
      <div className="grid grid-cols-2 gap-2">
        {LANGUAGES.map((language) => {
          const isSelected = selectedLanguages.includes(language.code);
          return (
            <button
              key={language.code}
              type="button"
              onClick={() => toggleLanguage(language.code)}
              className={cn(
                "flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-all",
                isSelected
                  ? "bg-purple-600 text-white hover:bg-purple-700"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              )}
            >
              <span>{language.name}</span>
              {isSelected && <Check size={16} className="ml-2" />}
            </button>
          );
        })}
      </div>
      {selectedLanguages.length > 0 && (
        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
          {selectedLanguages.length} language{selectedLanguages.length !== 1 ? "s" : ""} selected
        </p>
      )}
    </div>
  );
}
