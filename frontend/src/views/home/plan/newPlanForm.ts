import type { PlanLengthInterface, UtcInputInterface } from "@/types/terrain/NewPlanFormInterface";
import { formatDay } from "./planTimeline.ts";

const HOUR = 3600000;
const CLOCK_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;

export const PLAN_LENGTHS: PlanLengthInterface[] = [
  { label: "24 hours", hours: 24 },
  { label: "14 days", hours: 14 * 24 },
  { label: "Lunar day", hours: 29.530589 * 24 },
];

export function toUtcInput(timestamp: number): UtcInputInterface {
  const isoTime = new Date(timestamp).toISOString();

  return { date: isoTime.slice(0, 10), clock: isoTime.slice(11, 16) };
}

export function parseUtcInput(input: UtcInputInterface): number | null {
  if (!CLOCK_PATTERN.test(input.clock)) {
    return null;
  }

  const timestamp = Date.parse(`${input.date}T${input.clock}:00Z`);

  return Number.isNaN(timestamp) ? null : timestamp;
}

export function matchingLength(durationMs: number): PlanLengthInterface | null {
  return PLAN_LENGTHS.find((length) => Math.abs(length.hours * HOUR - durationMs) < 60000) ?? null;
}

export function timesPerSite(durationMs: number, stepSeconds: number): number {
  return durationMs > 0 ? Math.ceil(durationMs / (stepSeconds * 1000)) : 0;
}

export function suggestPlanName(siteNames: string[], start: number, end: number): string {
  if (!siteNames.length) {
    return "";
  }

  const sites = siteNames.length === 1 ? siteNames[0]! : `${siteNames.length} sites`;
  const startDay = formatDay(start);
  const endDay = formatDay(end);

  return startDay === endDay ? `${sites}, ${startDay}` : `${sites}, ${startDay} to ${endDay}`;
}
