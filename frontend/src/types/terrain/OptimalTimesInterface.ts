import type { VisibilityMetric } from "./VisibilityInterface";

export interface OptimalTimeCriteriaInterface {
  minimumSunFraction: number;
  minimumEarthFraction: number;
  minimumJointShare: number;
}

export interface OptimalWindowInterface {
  startTime: number;
  endTime: number;
  durationMilliseconds: number;
  startBoundary: "plan" | "missing" | "sample";
  endBoundary: "plan" | "missing" | "sample";
  averageSunFraction: number;
  averageEarthFraction: number;
  averageJointShare: number;
}

export interface OptimalTimesInterface {
  matchingDayCount: number;
  bestWindow: OptimalWindowInterface | null;
  matchingMilliseconds: number;
  calculatedMilliseconds: number;
  totalMilliseconds: number;

  peaks: { sunlight: number; earth: number; joint: number } | null;

  misses: (VisibilityMetric[] | null)[];
}
