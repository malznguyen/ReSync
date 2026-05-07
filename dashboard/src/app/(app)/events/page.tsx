import { EventFeed } from "@/components/event-feed/EventFeed";
import { PageHeader } from "@/components/ui/PageHeader";

export default function EventsPage(): JSX.Element {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Events"
        description="Monitor customer seated and hand-raise events as the analytics service emits them."
      />
      <EventFeed />
    </div>
  );
}
