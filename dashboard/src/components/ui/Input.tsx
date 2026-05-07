import { type InputHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, hint, error, id, ...props }, ref) => {
    const inputId = id ?? props.name;

    return (
      <label className="block space-y-2" htmlFor={inputId}>
        {label ? (
          <span className="text-sm font-semibold text-ink-700">{label}</span>
        ) : null}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            "h-11 w-full rounded-lg border border-ink-900/10 bg-white/85 px-3 text-sm text-ink-900 outline-none transition placeholder:text-ink-500 focus:border-lagoon-400 focus:ring-4 focus:ring-lagoon-100",
            error ? "border-copper-600 focus:ring-copper-100" : null,
            className
          )}
          {...props}
        />
        {error ? (
          <span className="block text-xs font-medium text-copper-600">{error}</span>
        ) : hint ? (
          <span className="block text-xs text-ink-500">{hint}</span>
        ) : null}
      </label>
    );
  }
);

Input.displayName = "Input";
