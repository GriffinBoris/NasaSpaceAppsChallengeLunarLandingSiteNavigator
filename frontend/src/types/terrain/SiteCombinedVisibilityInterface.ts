import type { TerrainLocationInterface } from "./TerrainLocationInterface";
import type { VisibilityGridInterface } from "./SiteTerrainInterface";

export interface CombinedSampleInterface extends TerrainLocationInterface {
  visibleSeconds: number;
}

export interface CombinedGridInterface {
  gridSize: number;
  radiusMeters: number;
  spacingMeters: number;
  samples: (CombinedSampleInterface | null)[];
}

export interface SiteCombinedVisibilityInterface {
  resultRevision: number;
  reset: boolean;
  selectionId: number;
  totalSeconds: number;
  checkedSeconds: number;
  checkedFrames: number;
  expectedFrames: number;
  grid: CombinedGridInterface | null;
  previews: (VisibilityGridInterface & { frameId: number })[];
}

export interface BestCombinedSampleInterface extends TerrainLocationInterface {
  x: number;
  y: number;
  fraction: number;
  matchingSamples: number;
}
