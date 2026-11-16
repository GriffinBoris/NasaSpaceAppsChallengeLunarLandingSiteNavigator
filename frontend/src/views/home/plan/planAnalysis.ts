import type {
  DaySunlightInterface,
  SunlightRunInterface,
  SiteMetricsInterface,
  VisibilityCalendarInterface,
} from "@/types/terrain/PlanAnalysisInterface";
import { averageSun, formatDuration, formatUtc, isFullSun, sunlightRuns, type SunlightSeries } from "./planTimeline.ts";

const HOUR = 3600000;
const DAY = 24 * HOUR;

export function siteMetrics(series: SunlightSeries): SiteMetricsInterface {
  let calculatedCount = 0;
  let fullyLitCount = 0;

  for (const fraction of series) {
    if (fraction === null) {
      continue;
    }

    calculatedCount++;

    if (isFullSun(fraction)) {
      fullyLitCount++;
    }
  }

  return {
    calculatedCount,
    average: averageSun(series),
    fullyLitShare: calculatedCount ? fullyLitCount / calculatedCount : null,
    darkRuns: sunlightRuns(series, "dark"),
    longestSunlit: sunlightRuns(series, "sunlit")[0] ?? null,
  };
}

function startOfDay(timestamp: number): number {
  return Math.floor(timestamp / DAY) * DAY;
}

export function dailySunlight(schedule: number[], series: SunlightSeries): DaySunlightInterface[] {
  if (!schedule.length) {
    return [];
  }

  const firstDay = startOfDay(schedule[0]!);
  const dayCount = (startOfDay(schedule[schedule.length - 1]!) - firstDay) / DAY + 1;
  const totals = new Array<number>(dayCount).fill(0);
  const counts = new Array<number>(dayCount).fill(0);

  for (let index = 0; index < schedule.length; index++) {
    const timestamp = schedule[index]!;
    const fraction = series[index]!;

    if (fraction === null) {
      continue;
    }

    const dayIndex = (startOfDay(timestamp) - firstDay) / DAY;

    totals[dayIndex]! += fraction;
    counts[dayIndex]!++;
  }

  return counts.map((count, dayIndex) => ({
    day: firstDay + dayIndex * DAY,
    average: count ? totals[dayIndex]! / count : null,
    calculatedCount: count,
  }));
}

export function visibilityCalendar(schedule: number[], series: SunlightSeries, stepSeconds: number): VisibilityCalendarInterface | null {
  const bucket = Math.max(stepSeconds * 1000, HOUR);

  if (bucket >= DAY || !schedule.length) {
    return null;
  }

  const columnCount = Math.round(DAY / bucket);
  const firstDay = startOfDay(schedule[0]!);
  const dayCount = (startOfDay(schedule[schedule.length - 1]!) - firstDay) / DAY + 1;
  const totals = Array.from({ length: dayCount }, () => new Array<number>(columnCount).fill(0));
  const counts = Array.from({ length: dayCount }, () => new Array<number>(columnCount).fill(0));

  for (let index = 0; index < schedule.length; index++) {
    const timestamp = schedule[index]!;
    const fraction = series[index]!;

    if (fraction === null) {
      continue;
    }

    const day = startOfDay(timestamp);
    const row = (day - firstDay) / DAY;
    const column = Math.floor((timestamp - day) / bucket);

    totals[row]![column]! += fraction;
    counts[row]![column]!++;
  }

  return {
    columnHours: bucket / HOUR,
    days: counts.map((rowCounts, row) => ({
      day: firstDay + row * DAY,
      cells: rowCounts.map((count, column) => (count ? totals[row]![column]! / count : null)),
    })),
  };
}

export function runDuration(
  run: SunlightRunInterface,
  scheduleLength: number,
  stepSeconds: number,
  windowSeconds: number
): { text: string; isBound: boolean } {
  const seconds = Math.min(run.length * stepSeconds, windowSeconds - run.startIndex * stepSeconds);

  return { text: formatDuration(seconds), isBound: run.startIndex === 0 || run.startIndex + run.length >= scheduleLength };
}

export function runDurationLabel(run: SunlightRunInterface, scheduleLength: number, stepSeconds: number, windowSeconds: number): string {
  const { text, isBound } = runDuration(run, scheduleLength, stepSeconds, windowSeconds);

  return isBound ? `At least ${text}` : text;
}

export function planInsight(
  sites: { name: string; metrics: SiteMetricsInterface }[],
  schedule: number[],
  stepSeconds: number,
  windowSeconds: number
): { lead: string; detail: string } {
  const measured = sites.filter((site) => site.metrics.average !== null);

  if (!measured.length) {
    return { lead: "No results yet.", detail: "" };
  }

  const duration = (run: SunlightRunInterface) => {
    const { text, isBound } = runDuration(run, schedule.length, stepSeconds, windowSeconds);

    return `${isBound ? "at least" : "about"} ${text}`;
  };
  const startText = (run: SunlightRunInterface) => `${formatUtc(schedule[run.startIndex]!)}${run.startIndex === 0 ? " or earlier" : ""}`;

  const isComplete = (metrics: SiteMetricsInterface) => metrics.calculatedCount === schedule.length;

  if (measured.length === 1) {
    const [site] = measured;
    const longest = site!.metrics.darkRuns[0];
    let darkness = "None of its results so far are fully dark.";

    if (longest) {
      darkness = `Its longest fully dark stretch is ${duration(longest)}, starting ${startText(longest)}.`;
    } else if (isComplete(site!.metrics)) {
      darkness = `None of its samples, checked every ${formatDuration(stepSeconds)}, are fully dark.`;
    }

    return { lead: `${site!.name} averages ${percent(site!.metrics.average!)} visible Sun over this window.`, detail: darkness };
  }

  let brightest = measured[0]!;
  let darkest = measured[0]!;

  for (const site of measured) {
    if (site.metrics.average! > brightest.metrics.average!) {
      brightest = site;
    }

    if ((site.metrics.darkRuns[0]?.length ?? 0) > (darkest.metrics.darkRuns[0]?.length ?? 0)) {
      darkest = site;
    }
  }

  const brightestDark = brightest.metrics.darkRuns[0];
  const lead = `${brightest.name} gets the most sunlight, averaging ${percent(brightest.metrics.average!)} visible Sun.`;
  let detail = "It has no fully dark results so far.";

  if (brightestDark) {
    detail = `Its longest fully dark stretch is ${duration(brightestDark)}.`;
  } else if (isComplete(brightest.metrics)) {
    detail = "None of its samples are fully dark.";
  }

  const darkestRun = darkest.metrics.darkRuns[0];

  if (darkest !== brightest && darkestRun) {
    detail += ` ${darkest.name} has the longest night: ${duration(darkestRun)}, starting ${startText(darkestRun)}.`;
  }

  return { lead, detail };
}

function percent(fraction: number): string {
  return `${Math.round(fraction * 100)}%`;
}
