import { AlertCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

interface ErrorStateProps {
  error: Error | string;
  onRetry?: () => void;
  className?: string;
}

/**
 * ErrorState component for displaying errors with retry option
 *
 * Features:
 * - Displays error message
 * - Optional retry button
 * - Accessible error presentation
 */
export function ErrorState({ error, onRetry, className }: ErrorStateProps) {
  const errorMessage = typeof error === "string" ? error : error.message;

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-16 text-center",
        className
      )}
      role="alert"
      aria-live="polite"
    >
      <div className="rounded-full bg-red-100 p-6 dark:bg-red-900/20">
        <AlertCircle className="text-red-600 dark:text-red-400" size={48} />
      </div>
      <h3 className="mt-6 text-xl font-semibold text-gray-900 dark:text-gray-100">
        Something went wrong
      </h3>
      <p className="mt-2 max-w-md text-gray-600 dark:text-gray-400">
        {errorMessage}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className={cn(
            "mt-6 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white",
            "hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
            "dark:bg-blue-500 dark:hover:bg-blue-600 dark:focus:ring-offset-gray-900",
            "transition-colors duration-200"
          )}
        >
          <RefreshCw size={18} />
          Try Again
        </button>
      )}
    </div>
  );
}
