import { CameraGrid } from "@/components/camera/CameraGrid";
import { PageHeader } from "@/components/ui/PageHeader";

export default function CamerasPage(): JSX.Element {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Cameras"
        description="Manage RTSP streams and open the zone painter for active dining room cameras."
      />
      <CameraGrid />
    </div>
  );
}
