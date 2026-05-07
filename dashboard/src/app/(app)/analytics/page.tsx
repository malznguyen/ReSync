import { AnalyticsCharts } from "@/components/charts/AnalyticsCharts";
import { PageHeader } from "@/components/ui/PageHeader";

export default function AnalyticsPage(): JSX.Element {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Analytics"
        description="Review visitor flow and service-demand patterns over a selected date range."
      />
      <AnalyticsCharts />
    </div>
  );
}
