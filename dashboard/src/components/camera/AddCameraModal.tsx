"use client";

import { Plus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { ApiClientError, createCamera } from "@/lib/api";
import type { Camera } from "@/types/api";

const RTSP_PATTERN = /^rtsps?:\/\/[^\s/$.?#].[^\s]*$/i;

interface AddCameraModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (camera: Camera) => void;
}

export function AddCameraModal({
  open,
  onClose,
  onCreated
}: AddCameraModalProps): JSX.Element {
  const [name, setName] = useState("");
  const [rtspUrl, setRtspUrl] = useState("");
  const [error, setError] = useState<string | undefined>();
  const [isSaving, setIsSaving] = useState(false);

  const reset = (): void => {
    setName("");
    setRtspUrl("");
    setError(undefined);
  };

  const handleClose = (): void => {
    reset();
    onClose();
  };

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    event.preventDefault();
    setError(undefined);

    if (!RTSP_PATTERN.test(rtspUrl)) {
      setError("Enter a valid rtsp:// or rtsps:// stream URL.");
      return;
    }

    setIsSaving(true);
    try {
      const camera = await createCamera({
        name,
        rtsp_url: rtspUrl,
        status: "active"
      });
      onCreated(camera);
      handleClose();
    } catch (caughtError) {
      const message =
        caughtError instanceof ApiClientError
          ? caughtError.message
          : "Unable to create camera";
      setError(message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      title="Add Camera"
      description="Register an RTSP stream for ingestion."
      onClose={handleClose}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Camera name"
          name="name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Dining room north"
          required
        />
        <Input
          label="RTSP URL"
          name="rtsp_url"
          value={rtspUrl}
          onChange={(event) => setRtspUrl(event.target.value)}
          placeholder="rtsp://mediamtx:8554/dining-room"
          error={error}
          required
        />
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSaving}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            {isSaving ? "Adding" : "Add Camera"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
