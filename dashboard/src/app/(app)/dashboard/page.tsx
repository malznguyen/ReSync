import { DashboardOverview } from "@/components/DashboardOverview";
import { PageHeader } from "@/components/ui/PageHeader";

export default function DashboardPage(): JSX.Element {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Restaurant Vision Dashboard"
        description="Operate the low-latency camera, zone, event, and analytics surfaces from one control room."
      />
      <DashboardOverview />
    </div>
  );
}
