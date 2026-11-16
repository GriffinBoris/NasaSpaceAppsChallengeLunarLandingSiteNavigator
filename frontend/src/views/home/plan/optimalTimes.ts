import type { OptimalTimeCriteriaInterface, OptimalTimesInterface, OptimalWindowInterface } from "@/types/terrain/OptimalTimesInterface";
import type { SunlightFrameInterface } from "@/types/terrain/SunlightFrameInterface";
import type { SunlightStudyInterface } from "@/types/terrain/SunlightStudyInterface";
import type { VisibilityMetric } from "@/types/terrain/VisibilityInterface";
import { studySchedule } from "./planTimeline.ts";

const DAY_MILLISECONDS = 86400000;

interface VisibilitySample {
  startTime: number;
  endTime: number;
  visibility: { sunlight: number; earth: number; joint: number } | null;
  missed: VisibilityMetric[] | null;
  matches: boolean;
}

interface WindowTotals {
  startIndex: number;
  startTime: number;
  endTime: number;
  durationMilliseconds: number;
  sunlightSum: number;
  earthSum: number;
  jointSum: number;
}

export function optimalTimes(
  study: SunlightStudyInterface,
  frames: SunlightFrameInterface[],
  selectionId: number,
  criteria: OptimalTimeCriteriaInterface
): OptimalTimesInterface {
  const framesByTime = new Map<number, SunlightFrameInterface>();

  for (const frame of frames) {
    if (frame.selectionId === selectionId) {
      framesByTime.set(Date.parse(frame.timestamp), frame);
    }
  }

  const endTime = Date.parse(study.endTime);
  const stepMilliseconds = study.stepSeconds * 1000;
  const samples: VisibilitySample[] = [];
  let calculatedMilliseconds = 0;
  let matchingMilliseconds = 0;
  const peaks = { sunlight: 0, earth: 0, joint: 0 };

  for (const startTime of studySchedule(study)) {
    const frame = framesByTime.get(startTime);
    const sampleEndTime = Math.min(startTime + stepMilliseconds, endTime);
    const visibility =
      frame && frame.visibleSunFraction !== null && frame.visibleEarthFraction !== null && frame.jointVisibleShare !== null
        ? { sunlight: frame.visibleSunFraction, earth: frame.visibleEarthFraction, joint: frame.jointVisibleShare }
        : null;
    const missed = visibility && missedMinimums(visibility, criteria);
    const matches = missed !== null && missed.length === 0;

    samples.push({ startTime, endTime: sampleEndTime, visibility, missed, matches });

    if (visibility) {
      calculatedMilliseconds += sampleEndTime - startTime;
      peaks.sunlight = Math.max(peaks.sunlight, visibility.sunlight);
      peaks.earth = Math.max(peaks.earth, visibility.earth);
      peaks.joint = Math.max(peaks.joint, visibility.joint);
    }

    if (matches) {
      matchingMilliseconds += sampleEndTime - startTime;
    }
  }

  return {
    matchingDayCount: matchingDayCount(samples),
    bestWindow: bestMatchingWindow(samples),
    matchingMilliseconds,
    calculatedMilliseconds,
    totalMilliseconds: endTime - Date.parse(study.startTime),
    peaks: calculatedMilliseconds ? peaks : null,
    misses: samples.map((sample) => sample.missed),
  };
}

function missedMinimums(visibility: { sunlight: number; earth: number; joint: number }, criteria: OptimalTimeCriteriaInterface) {
  const missed: VisibilityMetric[] = [];

  if (visibility.sunlight < criteria.minimumSunFraction) {
    missed.push("sunlight");
  }
  if (visibility.earth < criteria.minimumEarthFraction) {
    missed.push("earth");
  }
  if (visibility.joint === 0 || visibility.joint < criteria.minimumJointShare) {
    missed.push("joint");
  }

  return missed;
}

function matchingDayCount(samples: VisibilitySample[]): number {
  const days = new Set<number>();

  for (const sample of samples) {
    if (!sample.matches) {
      continue;
    }

    const firstDay = Math.floor(sample.startTime / DAY_MILLISECONDS) * DAY_MILLISECONDS;

    for (let day = firstDay; day < sample.endTime; day += DAY_MILLISECONDS) {
      days.add(day);
    }
  }

  return days.size;
}

function bestMatchingWindow(samples: VisibilitySample[]): OptimalWindowInterface | null {
  let bestWindow: OptimalWindowInterface | null = null;
  let activeWindow: WindowTotals | null = null;

  for (let index = 0; index <= samples.length; index++) {
    const sample = samples[index];

    if (sample?.matches) {
      if (!activeWindow) {
        activeWindow = {
          startIndex: index,
          startTime: sample.startTime,
          endTime: sample.endTime,
          durationMilliseconds: 0,
          sunlightSum: 0,
          earthSum: 0,
          jointSum: 0,
        };
      }

      const durationMilliseconds = sample.endTime - sample.startTime;

      activeWindow.endTime = sample.endTime;
      activeWindow.durationMilliseconds += durationMilliseconds;
      activeWindow.sunlightSum += sample.visibility!.sunlight * durationMilliseconds;
      activeWindow.earthSum += sample.visibility!.earth * durationMilliseconds;
      activeWindow.jointSum += sample.visibility!.joint * durationMilliseconds;
      continue;
    }

    if (!activeWindow) {
      continue;
    }

    const window: OptimalWindowInterface = {
      startTime: activeWindow.startTime,
      endTime: activeWindow.endTime,
      durationMilliseconds: activeWindow.durationMilliseconds,
      startBoundary: sampleBoundary(samples[activeWindow.startIndex - 1]),
      endBoundary: sampleBoundary(sample),
      averageSunFraction: activeWindow.sunlightSum / activeWindow.durationMilliseconds,
      averageEarthFraction: activeWindow.earthSum / activeWindow.durationMilliseconds,
      averageJointShare: activeWindow.jointSum / activeWindow.durationMilliseconds,
    };

    if (
      !bestWindow ||
      window.durationMilliseconds > bestWindow.durationMilliseconds ||
      (window.durationMilliseconds === bestWindow.durationMilliseconds && window.averageJointShare > bestWindow.averageJointShare)
    ) {
      bestWindow = window;
    }

    activeWindow = null;
  }

  return bestWindow;
}

function sampleBoundary(sample: VisibilitySample | undefined): OptimalWindowInterface["startBoundary"] {
  if (!sample) {
    return "plan";
  }

  return sample.visibility ? "sample" : "missing";
}

export function formatOptimalDuration(milliseconds: number): string {
  const totalSeconds = Math.round(milliseconds / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const parts: string[] = [];

  if (days) {
    parts.push(`${days} d`);
  }
  if (hours) {
    parts.push(`${hours} h`);
  }
  if (minutes) {
    parts.push(`${minutes} min`);
  }
  if (seconds) {
    parts.push(`${seconds} s`);
  }

  return parts.length ? parts.join(" ") : "0 min";
}
