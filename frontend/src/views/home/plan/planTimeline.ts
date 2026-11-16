import type { VisibilityMetric } from "@/types/terrain/VisibilityInterface";
import { frameFraction } from "../visibility/visibilityView.ts";
import type { SunlightRunInterface } from "@/types/terrain/PlanAnalysisInterface";
import type { SunlightFrameInterface } from "@/types/terrain/SunlightFrameInterface";
import type { SunlightStudyInterface } from "@/types/terrain/SunlightStudyInterface";

export type SunlightSeries = (number | null)[];

const SHADOW_LIMIT = 0.005;
const SUNLIGHT_LIMIT = 0.995;

const dateFormat = new Intl.DateTimeFormat("en-US", { timeZone: "UTC", month: "short", day: "numeric" });
const dateYearFormat = new Intl.DateTimeFormat("en-US", { timeZone: "UTC", month: "short", day: "numeric", year: "numeric" });
const timeFormat = new Intl.DateTimeFormat("en-US", { timeZone: "UTC", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

export function studySchedule(study: SunlightStudyInterface): number[] {
  const start = Date.parse(study.startTime);
  const step = study.stepSeconds * 1000;
  const count = Math.ceil((Date.parse(study.endTime) - start) / step);

  return Array.from({ length: count }, (_, index) => start + index * step);
}

export function scheduleIndex(study: SunlightStudyInterface, timestamp: string): number {
  return Math.round((Date.parse(timestamp) - Date.parse(study.startTime)) / (study.stepSeconds * 1000));
}

export function studySeries(
  study: SunlightStudyInterface,
  frames: SunlightFrameInterface[],
  metric: VisibilityMetric = "sunlight"
): Map<number, SunlightSeries> {
  const count = studySchedule(study).length;
  const series = new Map<number, SunlightSeries>();

  for (const selection of study.selections) {
    series.set(selection.id, new Array<number | null>(count).fill(null));
  }

  for (const frame of frames) {
    series.get(frame.selectionId)![scheduleIndex(study, frame.timestamp)] = frameFraction(frame, metric);
  }

  return series;
}

export function isShadow(fraction: number): boolean {
  return fraction <= SHADOW_LIMIT;
}

export function averageSun(series: SunlightSeries): number | null {
  let total = 0;
  let count = 0;

  for (const fraction of series) {
    if (fraction === null) {
      continue;
    }

    total += fraction;
    count++;
  }

  return count ? total / count : null;
}

export function isFullSun(fraction: number): boolean {
  return fraction >= SUNLIGHT_LIMIT;
}

export function sunlightRuns(series: SunlightSeries, kind: "dark" | "sunlit"): SunlightRunInterface[] {
  const runs: SunlightRunInterface[] = [];
  let runStart = -1;

  for (let index = 0; index <= series.length; index++) {
    const fraction = series[index];
    const matches = fraction !== null && fraction !== undefined && isShadow(fraction) === (kind === "dark");

    if (matches && runStart < 0) {
      runStart = index;
    }

    if (!matches && runStart >= 0) {
      runs.push({ startIndex: runStart, length: index - runStart });
      runStart = -1;
    }
  }

  return runs.sort((first, second) => second.length - first.length || first.startIndex - second.startIndex);
}

export function describeState(fraction: number | null): string {
  if (fraction === null) {
    return "Not calculated";
  }
  if (isFullSun(fraction)) {
    return "In sunlight";
  }
  if (isShadow(fraction)) {
    return "In shadow";
  }

  return `${Math.round(fraction * 100)}% of the Sun visible`;
}

export function sunlightLabel(fraction: number | null): string {
  if (fraction === null) {
    return "–";
  }
  if (isFullSun(fraction)) {
    return "Full Sun";
  }
  if (isShadow(fraction)) {
    return "Dark";
  }

  return `${Math.round(fraction * 100)}% Sun`;
}

export function isPlanProcessing(study: SunlightStudyInterface): boolean {
  return study.status === "queued" || study.status === "running" || study.status === "stopping";
}

export function describeQueue(study: SunlightStudyInterface, studies: SunlightStudyInterface[]): string {
  const active = studies.find((other) => other.id !== study.id && (other.status === "running" || other.status === "stopping"));

  return active ? `Starts after ${active.name} finishes` : "Waiting for the calculation worker";
}

export function calculateLabel(study: SunlightStudyInterface): string {
  if (study.status === "failed") {
    return "Retry";
  }

  return study.completedFrames || study.savedResults ? "Continue" : "Calculate";
}

export function describePlanStatus(study: SunlightStudyInterface): string {
  switch (study.status) {
    case "complete":
      return "Complete";
    case "pending":
      return study.savedResults ? "Results incomplete" : "Not calculated";
    case "queued":
      return "Queued";
    case "running":
      if (study.progress?.phase === "preparing") {
        return `Preparing ${study.progress.percentage}%`;
      }

      return `Calculating ${study.progress?.percentage ?? 0}%`;
    case "stopping":
      return "Stopping, keeping completed results";
    case "stopped":
      return "Stopped";
    case "failed":
      return "Failed";
  }
}

export function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60);

  if (minutes < 60) {
    return `${minutes} min`;
  }

  const hours = Math.round(minutes / 60);
  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;

  if (!days) {
    return `${hours} h`;
  }

  return remainingHours ? `${days} d ${remainingHours} h` : `${days} d`;
}

export function dayTick(index: number, dayCount: number): "always" | "wide" | "narrow" | null {
  const isWeekly = index % 7 === 0;

  if (dayCount > 21) {
    return isWeekly ? "always" : null;
  }
  if (index % 2 === 0) {
    return isWeekly ? "always" : "wide";
  }

  return isWeekly ? "narrow" : null;
}

export function dayLabelClass(index: number, dayCount: number): string {
  if (index < dayCount - 3) {
    return "w-0";
  }

  const isLastWide = index === lastTick(dayCount, "narrow");
  const isLastNarrow = index === lastTick(dayCount, "wide");

  if (isLastWide && isLastNarrow) {
    return "flex w-0 justify-end justify-self-end";
  }
  if (isLastWide) {
    return "w-0 sm:flex sm:justify-end sm:justify-self-end";
  }
  if (isLastNarrow) {
    return "w-0 max-sm:flex max-sm:justify-end max-sm:justify-self-end";
  }

  return "w-0";
}

function lastTick(dayCount: number, hiddenKind: "wide" | "narrow"): number {
  for (let index = dayCount - 1; index >= 0; index--) {
    const tick = dayTick(index, dayCount);

    if (tick && tick !== hiddenKind) {
      return index;
    }
  }

  return -1;
}

export function formatDay(timestamp: number): string {
  return dateFormat.format(timestamp);
}

export function formatUtc(timestamp: number): string {
  return `${dateFormat.format(timestamp)}, ${timeFormat.format(timestamp)} UTC`;
}

export function formatUtcRange(startTime: number, endTime: number): string {
  return `${dateFormat.format(startTime)}, ${timeFormat.format(startTime)} – ${formatUtc(endTime)}`;
}

export function formatWindow(startTime: string, endTime: string): string {
  const start = new Date(startTime);
  const end = new Date(endTime);

  if (!isMidnight(start) || !isMidnight(end)) {
    return `${dateYearFormat.format(start)} ${timeFormat.format(start)} – ${dateYearFormat.format(end)} ${timeFormat.format(end)} UTC`;
  }

  if (start.getUTCFullYear() !== end.getUTCFullYear()) {
    return `${dateYearFormat.format(start)} – ${dateYearFormat.format(end)}`;
  }

  if (start.getUTCMonth() !== end.getUTCMonth()) {
    return `${dateFormat.format(start)} – ${dateYearFormat.format(end)}`;
  }

  return `${dateFormat.format(start)}–${end.getUTCDate()}, ${end.getUTCFullYear()}`;
}

function isMidnight(date: Date): boolean {
  return date.getUTCHours() === 0 && date.getUTCMinutes() === 0;
}
