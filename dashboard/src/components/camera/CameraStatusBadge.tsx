import { CircleCheck, CircleOff, Clock3 } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { normalizeStatus, titleCase } from "@/lib/utils";

interface CameraStatusBadgeProps {
  status: string;
}

export function CameraStatusBadge({
  status
}: CameraStatusBadgeProps): JSX.Element {
  const normalized = normalizeStatus(status);

  if (normalized === "online") {
    return (
      <Badge tone="green">
        <CircleCheck className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
        Online
      </Badge>
    );
  }

  if (normalized === "offline") {
    return (
      <Badge tone="red">
        <CircleOff className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
        Offline
      </Badge>
    );
  }

  return (
    <Badge tone="amber">
      <Clock3 className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
      {titleCase(status)}
    </Badge>
  );
}
