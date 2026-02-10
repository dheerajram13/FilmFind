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
      <div className="rounded-full border border-red-500/30 bg-red-500/10 p-6 shadow-lg">
        <AlertCircle className="text-red-400" size={48} />
      </div>
      <h3 className="mt-6 text-xl font-semibold text-white">
        Something went wrong
      </h3>
      <p className="mt-2 max-w-md text-zinc-400">
        {errorMessage}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className={cn(
            "mt-6 inline-flex items-center gap-2 rounded-lg bg-red-600 px-6 py-3 font-medium text-white",
            "hover:bg-red-500 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-black",
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
