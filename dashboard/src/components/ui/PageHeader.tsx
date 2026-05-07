interface PageHeaderProps {
  title: string;
  description: string;
  action?: React.ReactNode;
}

export function PageHeader({
  title,
  description,
  action
}: PageHeaderProps): JSX.Element {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-3xl">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-lagoon-600">
          ReSync Control
        </p>
        <h1 className="mt-2 font-display text-3xl font-black tracking-normal text-ink-900 md:text-4xl">
          {title}
        </h1>
        <p className="mt-2 text-sm leading-6 text-ink-500">{description}</p>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
