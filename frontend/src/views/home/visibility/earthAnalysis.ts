import type { SunlightFrameInterface } from "@/types/terrain/SunlightFrameInterface";
import type { SunlightStudyInterface } from "@/types/terrain/SunlightStudyInterface";
import { averageSun, formatDuration, scheduleIndex, sunlightRuns, type SunlightSeries } from "../plan/planTimeline.ts";

export function earthCenterSeries(study: SunlightStudyInterface, frames: SunlightFrameInterface[], selectionId: number): SunlightSeries {
  const count = Math.ceil((Date.parse(study.endTime) - Date.parse(study.startTime)) / (study.stepSeconds * 1000));
  const series = new Array<number | null>(count).fill(null);

  for (const frame of frames) {
    if (frame.selectionId !== selectionId || frame.earthCenterVisible === null) {
      continue;
    }

    series[scheduleIndex(study, frame.timestamp)] = Number(frame.earthCenterVisible);
  }

  return series;
}

export function earthMetrics(series: SunlightSeries) {
  return {
    availableShare: averageSun(series),
    windows: sunlightRuns(series, "sunlit").sort((first, second) => first.startIndex - second.startIndex),
    outages: sunlightRuns(series, "dark"),
  };
}

export function nextEarthChange(series: SunlightSeries, index: number, stepSeconds: number): { label: string; value: string } {
  const current = series[index];

  if (current === null || current === undefined) {
    return { label: "Earth at this time", value: "Not calculated" };
  }

  for (let nextIndex = index + 1; nextIndex < series.length; nextIndex++) {
    const value = series[nextIndex];

    if (value === null) {
      return { label: "Next Earth change", value: "Missing results" };
    }
    if (value === current) {
      continue;
    }

    return { label: current ? "Next Earthset" : "Next Earthrise", value: `In ${formatDuration((nextIndex - index) * stepSeconds)}` };
  }

  return { label: "Earth after this time", value: current ? "Visible to plan end" : "Blocked to plan end" };
}
