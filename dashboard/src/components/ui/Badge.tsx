import { cn } from "@/lib/utils";

type BadgeTone = "blue" | "green" | "amber" | "red" | "neutral";

interface BadgeProps {
  children: React.ReactNode;
  tone?: BadgeTone;
  className?: string;
}

const tones: Record<BadgeTone, string> = {
  blue: "border-blue-200 bg-blue-50 text-blue-700",
  green: "border-emerald-200 bg-emerald-50 text-emerald-700",
  amber: "border-amber-200 bg-amber-50 text-amber-800",
  red: "border-red-200 bg-red-50 text-red-700",
  neutral: "border-ink-900/10 bg-white/70 text-ink-700"
};

export function Badge({
  children,
  tone = "neutral",
  className
}: BadgeProps): JSX.Element {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-bold",
        tones[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
