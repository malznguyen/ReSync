import { cn } from "@/lib/utils";

interface PanelProps {
  children?: React.ReactNode;
  className?: string;
}

export function Panel({ children, className }: PanelProps): JSX.Element {
  return (
    <section className={cn("glass-panel rounded-lg p-5", className)}>
      {children}
    </section>
  );
}
