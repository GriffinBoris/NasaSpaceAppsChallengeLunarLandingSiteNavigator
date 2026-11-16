import type { IlluminationInterface } from "./IlluminationInterface";

export interface IlluminationPatchInterface {
  center: IlluminationInterface;
  gridSize: number;
  radiusMeters: number;
  spacingMeters: number;
  points: ({
    visibleSunFraction: number;
    samplingConverged: boolean;
  } | null)[];
}
