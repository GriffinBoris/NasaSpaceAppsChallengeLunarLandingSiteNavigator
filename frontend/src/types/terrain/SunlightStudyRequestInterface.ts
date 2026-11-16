export interface SunlightStudyRequestInterface {
  name: string;
  datasetId: number;
  selectionIds: number[];
  startTime: string;
  endTime: string;
  stepSeconds: number;
  workerCount: number;
}
