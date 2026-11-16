import assert from "node:assert/strict";
import test from "node:test";
import type { SunlightFrameInterface } from "../src/types/terrain/SunlightFrameInterface.ts";
import type { SunlightStudyInterface } from "../src/types/terrain/SunlightStudyInterface.ts";
import { formatCoordinates, formatRadius } from "../src/views/home/sites/coordinateFormat.ts";
import {
  averageSun,
  calculateLabel,
  dayLabelClass,
  describePlanStatus,
  describeQueue,
  describeState,
  isPlanProcessing,
  formatDuration,
  formatUtc,
  formatWindow,
  studySchedule,
  studySeries,
} from "../src/views/home/plan/planTimeline.ts";

const HOUR = 3600000;

const study: SunlightStudyInterface = {
  id: 7,
  name: "Landing window A",
  datasetId: 2,
  selections: [
    { id: 1, name: "Shackleton rim", latitude: -89.9, longitude: 180, radiusMeters: 2500 },
    { id: 2, name: "Polar reference point", latitude: -89.9, longitude: 180, radiusMeters: null },
  ],
  startTime: "2026-11-11T00:00:00Z",
  endTime: "2026-11-11T05:30:00Z",
  stepSeconds: 3600,
  workerCount: 4,
  expectedFrames: 12,
  completedFrames: 3,
  status: "stopped",
  progress: null,
  errorMessage: "",
  createdTs: "2026-11-11T00:00:00Z",
};

function frame(selectionId: number, timestamp: string, visibleSunFraction: number): SunlightFrameInterface {
  return {
    id: Date.parse(timestamp) + selectionId,
    studyId: study.id,
    selectionId,
    timestamp,
    visibleSunFraction,
    thumbnail: null,
    earthThumbnail: null,
  };
}

test("the schedule matches the backend's end-exclusive, rounded-up sample count", () => {
  const schedule = studySchedule(study);

  assert.equal(schedule.length, 6);
  assert.equal(schedule[0], Date.parse(study.startTime));
  assert.equal(schedule[5], Date.parse(study.startTime) + 5 * HOUR);
});

test("results land at their scheduled time for their own site and missing results stay empty", () => {
  const series = studySeries(study, [
    frame(1, "2026-11-11T02:00:00Z", 0.4),
    frame(2, "2026-11-11T00:00:00Z", 1),
    frame(1, "2026-11-11T05:00:00Z", 0),
  ]);

  assert.deepEqual(series.get(1), [null, null, 0.4, null, null, 0]);
  assert.deepEqual(series.get(2), [1, null, null, null, null, null]);
});

test("the average ignores results that have not been calculated", () => {
  assert.equal(averageSun([1, null, 0, null]), 0.5);
  assert.equal(averageSun([null, null]), null);
});

test("states describe points and regions in plain language", () => {
  assert.equal(describeState(1), "In sunlight");
  assert.equal(describeState(0), "In shadow");
  assert.equal(describeState(0.42), "42% of the Sun visible");
  assert.equal(describeState(null), "Not calculated");
});

test("durations read as minutes, hours, or days and hours", () => {
  assert.equal(formatDuration(900), "15 min");
  assert.equal(formatDuration(14 * 3600), "14 h");
  assert.equal(formatDuration(30 * 3600), "1 d 6 h");
  assert.equal(formatDuration(48 * 3600), "2 d");
});

test("windows show dates only at midnight and include times otherwise", () => {
  assert.equal(formatWindow("2026-11-11T00:00:00Z", "2026-11-19T00:00:00Z"), "Nov 11–19, 2026");
  assert.equal(formatWindow("2026-11-28T00:00:00Z", "2026-12-03T00:00:00Z"), "Nov 28 – Dec 3, 2026");
  assert.equal(formatWindow("2026-12-28T00:00:00Z", "2027-01-03T00:00:00Z"), "Dec 28, 2026 – Jan 3, 2027");
  assert.equal(formatWindow("2026-11-11T12:00:00Z", "2026-11-12T12:00:00Z"), "Nov 11, 2026 12:00 – Nov 12, 2026 12:00 UTC");
  assert.equal(formatUtc(Date.parse("2026-11-14T08:00:00Z")), "Nov 14, 08:00 UTC");
});

test("coordinates use hemisphere letters and regions show their radius", () => {
  assert.equal(formatCoordinates(-89.9, 180), "89.90°S 180.00°E");
  assert.equal(formatCoordinates(0.6741, -23.4216), "0.67°N 23.42°W");
  assert.equal(formatRadius(2500), "2.5 km radius");
  assert.equal(formatRadius(null), "Point");
});

test("queued plans say which plan they wait for, or that the worker has not started them", () => {
  const queued = { ...study, id: 8, name: "Backup window", status: "queued" as const };
  const running = { ...study, status: "running" as const };

  assert.equal(describeQueue(queued, [running, queued]), "Starts after Landing window A finishes");
  assert.equal(describeQueue(queued, [{ ...running, status: "stopping" as const }, queued]), "Starts after Landing window A finishes");
  assert.equal(describeQueue(queued, [{ ...running, status: "complete" as const }, queued]), "Waiting for the calculation worker");
});

test("only queued, running, and stopping plans count as processing", () => {
  const statuses = ["pending", "queued", "running", "stopping", "stopped", "failed", "complete"] as const;

  assert.deepEqual(
    statuses.filter((status) => isPlanProcessing({ ...study, status })),
    ["queued", "running", "stopping"]
  );
});

test("the calculate action reads as retry, continue, or calculate", () => {
  assert.equal(calculateLabel({ ...study, status: "failed" }), "Retry");
  assert.equal(calculateLabel({ ...study, status: "stopped", completedFrames: 3 }), "Continue");
  assert.equal(calculateLabel({ ...study, status: "pending", completedFrames: 0 }), "Calculate");
  assert.equal(calculateLabel({ ...study, status: "pending", completedFrames: 0, savedResults: 2 }), "Continue");
  assert.equal(describePlanStatus({ ...study, status: "pending", completedFrames: 0, savedResults: 2 }), "Results incomplete");
  assert.equal(
    describePlanStatus({ ...study, status: "running", progress: { completed: 1, total: 4, percentage: 25, stage: "Tracing" } }),
    "Calculating 25%"
  );
});

test("terrain preparation reports its own percentage before sunlight results exist", () => {
  const preparing: SunlightStudyInterface = {
    ...study,
    status: "running",
    completedFrames: 0,
    progress: { completed: 2, total: 5, percentage: 40, stage: "Preparing horizons", phase: "preparing" },
  };

  assert.equal(describePlanStatus(preparing), "Preparing 40%");
  assert.equal(
    describePlanStatus({ ...preparing, progress: { completed: 0, total: 4000, percentage: 0, stage: "Tracing", phase: "calculating" } }),
    "Calculating 0%"
  );
});

test("only the last date label at each width hangs from its column's right edge", () => {
  assert.equal(dayLabelClass(14, 15), "flex w-0 justify-end justify-self-end");
  assert.equal(dayLabelClass(12, 15), "w-0");
  assert.equal(dayLabelClass(0, 15), "w-0");

  assert.equal(dayLabelClass(12, 13), "w-0 sm:flex sm:justify-end sm:justify-self-end");
  assert.equal(dayLabelClass(7, 13), "w-0");
});
