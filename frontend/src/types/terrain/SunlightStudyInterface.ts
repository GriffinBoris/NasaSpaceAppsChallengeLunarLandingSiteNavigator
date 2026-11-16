import type { SunlightSelectionSnapshotInterface } from "./SunlightSelectionInterface";
import type { IlluminationProgressInterface } from "./IlluminationProgressInterface";

export interface SunlightStudyProgressInterface extends IlluminationProgressInterface {
  phase?: "preparing" | "calculating";
}

export interface SunlightStudyInterface {
  id: number;
  name: string;
  datasetId: number;
  selections: SunlightSelectionSnapshotInterface[];
  startTime: string;
  endTime: string;
  stepSeconds: number;
  workerCount: number;
  expectedFrames: number;
  completedFrames: number;
  savedResults: number;
  resultRevision: number;
  status: "pending" | "queued" | "running" | "stopping" | "stopped" | "failed" | "complete";
  progress: SunlightStudyProgressInterface | null;
  errorMessage: string;
  createdTs: string;
}
