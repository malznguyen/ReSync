import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action
}: EmptyStateProps): JSX.Element {
  return (
    <div className="flex min-h-64 flex-col items-center justify-center rounded-lg border border-dashed border-ink-900/15 bg-white/55 p-8 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-lagoon-100 text-lagoon-600">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </div>
      <h3 className="mt-4 text-lg font-black text-ink-900">{title}</h3>
      <p className="mt-2 max-w-md text-sm leading-6 text-ink-500">
        {description}
      </p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
