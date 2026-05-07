import { ZoneCameraPicker } from "@/components/zone-painter/ZoneCameraPicker";
import { PageHeader } from "@/components/ui/PageHeader";

export default function ZonesPage(): JSX.Element {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Zones"
        description="Select a camera and draw normalized dining-zone polygons over the live HLS stream."
      />
      <ZoneCameraPicker />
    </div>
  );
}
