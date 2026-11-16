export interface SunlightSelectionSnapshotInterface {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  radiusMeters: number | null;
}

export interface SunlightSelectionInterface extends SunlightSelectionSnapshotInterface {
  createdTs: string;
  updatedTs: string;
}

export interface SunlightSelectionListInterface {
  selections: SunlightSelectionInterface[];
  stepOptions: { seconds: number; label: string }[];
  workerOptions: { value: number; label: string }[];
  defaultWorkerCount: number;
}
