import { Hand, UserCheck, Zap } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { titleCase } from "@/lib/utils";

interface EventTypeBadgeProps {
  eventType: string;
}

export function EventTypeBadge({
  eventType
}: EventTypeBadgeProps): JSX.Element {
  if (eventType === "hand_raise") {
    return (
      <Badge tone="blue">
        <Hand className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
        Hand Raise
      </Badge>
    );
  }

  if (eventType === "customer_seated") {
    return (
      <Badge tone="green">
        <UserCheck className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
        Seated
      </Badge>
    );
  }

  return (
    <Badge tone="amber">
      <Zap className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
      {titleCase(eventType)}
    </Badge>
  );
}
