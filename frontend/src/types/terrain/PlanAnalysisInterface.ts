import type { SunlightSelectionSnapshotInterface } from "./SunlightSelectionInterface";
import type { SunlightSeries } from "@/views/home/plan/planTimeline";

export interface SunlightRunInterface {
  startIndex: number;
  length: number;
}

export interface SiteMetricsInterface {
  calculatedCount: number;
  average: number | null;
  fullyLitShare: number | null;
  darkRuns: SunlightRunInterface[];
  longestSunlit: SunlightRunInterface | null;
}

export interface DaySunlightInterface {
  day: number;
  average: number | null;
  calculatedCount: number;
}

export interface PlanSiteInterface {
  selection: SunlightSelectionSnapshotInterface;
  series: SunlightSeries;
  metrics: SiteMetricsInterface;
  days: DaySunlightInterface[];
}

export interface VisibilityCalendarInterface {
  columnHours: number;
  days: { day: number; cells: (number | null)[] }[];
}
