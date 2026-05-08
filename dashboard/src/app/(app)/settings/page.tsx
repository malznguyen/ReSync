import { SystemControls } from "@/components/system/SystemControls";
import { PageHeader } from "@/components/ui/PageHeader";

export default function SettingsPage(): JSX.Element {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Settings"
        description="Control runtime debugging and processing switches from the Dashboard."
      />
      <SystemControls />
    </div>
  );
}
