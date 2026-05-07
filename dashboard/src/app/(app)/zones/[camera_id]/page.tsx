import { ZonePainter } from "@/components/zone-painter/ZonePainter";
import { PageHeader } from "@/components/ui/PageHeader";

interface ZonePainterPageProps {
  params: {
    camera_id: string;
  };
}

export default function ZonePainterPage({
  params
}: ZonePainterPageProps): JSX.Element {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Zone Painter"
        description="Draw, adjust, and save normalized polygons over the active HLS camera feed."
      />
      <ZonePainter cameraId={params.camera_id} />
    </div>
  );
}
