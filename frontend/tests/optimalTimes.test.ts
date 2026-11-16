import assert from "node:assert/strict";
import test from "node:test";
import type { OptimalTimeCriteriaInterface } from "../src/types/terrain/OptimalTimesInterface.ts";
import type { SunlightFrameInterface } from "../src/types/terrain/SunlightFrameInterface.ts";
import type { SunlightStudyInterface } from "../src/types/terrain/SunlightStudyInterface.ts";
import { formatOptimalDuration, optimalTimes } from "../src/views/home/plan/optimalTimes.ts";

const MINUTE = 60000;
const MIDNIGHT = Date.parse("2026-11-14T00:00:00Z");
const criteria: OptimalTimeCriteriaInterface = { minimumSunFraction: 0.5, minimumEarthFraction: 0.5, minimumJointShare: 0.5 };

function plan(startMinutes: number, endMinutes: number, stepSeconds = 900): SunlightStudyInterface {
  return {
    id: 1,
    name: "Landing dates",
    datasetId: 1,
    selections: [{ id: 1, name: "Landing region", latitude: -89, longitude: 0, radiusMeters: 10000 }],
    startTime: new Date(MIDNIGHT + startMinutes * MINUTE).toISOString(),
    endTime: new Date(MIDNIGHT + endMinutes * MINUTE).toISOString(),
    stepSeconds,
    workerCount: 4,
    expectedFrames: Math.ceil(((endMinutes - startMinutes) * 60) / stepSeconds),
    completedFrames: 0,
    savedResults: 0,
    resultRevision: 0,
    status: "stopped",
    progress: null,
    errorMessage: "",
    createdTs: "2026-11-14T00:00:00Z",
  };
}

function frameAt(
  minutes: number,
  { sunlight = 1, earth = 1, joint = 1 }: { sunlight?: number | null; earth?: number | null; joint?: number | null } = {}
): SunlightFrameInterface {
  return {
    id: minutes + 1,
    studyId: 1,
    selectionId: 1,
    timestamp: new Date(MIDNIGHT + minutes * MINUTE).toISOString(),
    visibleSunFraction: sunlight,
    visibleEarthFraction: earth,
    earthCenterVisible: earth === null ? null : earth > 0,
    jointVisibleShare: joint,
    resultRevision: 1,
    thumbnail: null,
    earthThumbnail: null,
  };
}

test("a matching time meets all three criteria for the selected site", () => {
  const frames = [
    frameAt(0, { sunlight: 0.6, earth: 0.8, joint: 0.6 }),
    frameAt(15, { sunlight: 0.4, earth: 0.8, joint: 0.8 }),
    frameAt(30, { sunlight: 0.8, earth: 0.4, joint: 0.8 }),
    frameAt(45, { sunlight: 0.8, earth: 0.8, joint: 0.4 }),
    { ...frameAt(0), id: 999, selectionId: 2 },
  ];
  const result = optimalTimes(plan(0, 60), frames, 1, criteria);

  assert.equal(result.matchingMilliseconds, 15 * MINUTE);
  assert.equal(result.calculatedMilliseconds, 60 * MINUTE);
  assert.equal(result.bestWindow!.startTime, MIDNIGHT);
  assert.equal(result.bestWindow!.endTime, MIDNIGHT + 15 * MINUTE);
  assert.equal(result.matchingDayCount, 1);
  assert.deepEqual(result.misses, [[], ["sunlight"], ["earth"], ["joint"]]);
});

test("separately bright and Earth-visible areas cannot create a matching joint window", () => {
  const result = optimalTimes(plan(0, 15), [frameAt(0, { sunlight: 0.9, earth: 0.9, joint: 0 })], 1, { ...criteria, minimumJointShare: 0 });

  assert.equal(result.calculatedMilliseconds, 15 * MINUTE);
  assert.equal(result.matchingMilliseconds, 0);
  assert.equal(result.matchingDayCount, 0);
  assert.equal(result.bestWindow, null);
  assert.deepEqual(result.peaks, { sunlight: 0.9, earth: 0.9, joint: 0 });
  assert.deepEqual(result.misses, [["joint"]]);
});

test("missing frames and missing Earth results break windows and reduce checked coverage", () => {
  const frames = [frameAt(0), frameAt(15), frameAt(45, { earth: null, joint: null }), frameAt(60)];
  const result = optimalTimes(plan(0, 75), frames, 1, criteria);

  assert.equal(result.totalMilliseconds, 75 * MINUTE);
  assert.equal(result.calculatedMilliseconds, 45 * MINUTE);
  assert.equal(result.matchingMilliseconds, 45 * MINUTE);
  assert.deepEqual(result.misses, [[], [], null, null, []]);
  assert.equal(result.bestWindow!.startTime, MIDNIGHT);
  assert.equal(result.bestWindow!.endTime, MIDNIGHT + 30 * MINUTE);
  assert.equal(result.bestWindow!.startBoundary, "plan");
  assert.equal(result.bestWindow!.endBoundary, "missing");

  const resumed = optimalTimes(plan(45, 75), frames, 1, criteria);

  assert.equal(resumed.bestWindow!.startBoundary, "missing");
  assert.equal(resumed.bestWindow!.endBoundary, "plan");
});

test("unverified shared coverage is unknown even when both regional averages exist", () => {
  const result = optimalTimes(plan(0, 15), [frameAt(0, { joint: null })], 1, criteria);

  assert.equal(result.calculatedMilliseconds, 0);
  assert.equal(result.bestWindow, null);
});

test("the best window favors duration, then shared coverage, then the earliest time", () => {
  const frames = [
    frameAt(0, { joint: 0.6 }),
    frameAt(15, { joint: 0.6 }),
    frameAt(30, { joint: 0 }),
    frameAt(45, { joint: 0.9 }),
    frameAt(60, { joint: 0.9 }),
    frameAt(75, { joint: 0 }),
    frameAt(90, { joint: 0.95 }),
    frameAt(105, { joint: 0 }),
    frameAt(120, { joint: 0.9 }),
    frameAt(135, { joint: 0.9 }),
  ];
  const result = optimalTimes(plan(0, 150), frames, 1, criteria);

  assert.equal(result.bestWindow!.startTime, MIDNIGHT + 45 * MINUTE);
  assert.equal(result.bestWindow!.durationMilliseconds, 30 * MINUTE);
  assert.equal(result.bestWindow!.averageJointShare, 0.9);
});

test("matching days count once regardless of how many samples match", () => {
  const frames = [frameAt(0)];

  for (let hour = 0; hour < 24; hour++) frames.push(frameAt(1440 + hour * 60, { joint: 0.6 }));

  const result = optimalTimes(plan(0, 2880, 3600), frames, 1, criteria);

  assert.equal(result.matchingDayCount, 2);
  assert.equal(result.calculatedMilliseconds, 1500 * MINUTE);
});

test("matching days span UTC midnight and windows clip a partial final step", () => {
  const frames = [frameAt(1410), frameAt(1470, { sunlight: 0.5, earth: 0.5, joint: 0.5 })];
  const result = optimalTimes(plan(1410, 1510, 3600), frames, 1, criteria);

  assert.equal(result.matchingMilliseconds, 100 * MINUTE);
  assert.equal(result.bestWindow!.endTime, MIDNIGHT + 1510 * MINUTE);
  assert.equal(result.bestWindow!.averageSunFraction, 0.8);
  assert.equal(result.matchingDayCount, 2);
  assert.equal(formatOptimalDuration(result.bestWindow!.durationMilliseconds), "1 h 40 min");
});

test("known failing neighbors bound an interior window", () => {
  const frames = [frameAt(0, { joint: 0 }), frameAt(15), frameAt(30), frameAt(45, { joint: 0 })];
  const window = optimalTimes(plan(0, 60), frames, 1, criteria).bestWindow;

  assert.equal(window!.startBoundary, "sample");
  assert.equal(window!.endBoundary, "sample");
  assert.equal(window!.durationMilliseconds, 30 * MINUTE);
});

test("minimum values are inclusive and tightening them recalculates matches", () => {
  const frames = [frameAt(0, { sunlight: 0.5, earth: 0.5, joint: 0.5 }), frameAt(15, { sunlight: 0.49 })];

  assert.equal(optimalTimes(plan(0, 30), frames, 1, criteria).matchingMilliseconds, 15 * MINUTE);
  assert.equal(optimalTimes(plan(0, 30), frames, 1, { ...criteria, minimumSunFraction: 0.75 }).matchingMilliseconds, 0);
});

test("a partial minute at the plan end is counted only once", () => {
  const result = optimalTimes(plan(0, 15.5), [frameAt(0), frameAt(15)], 1, criteria);

  assert.equal(result.matchingMilliseconds, 15.5 * MINUTE);
  assert.equal(formatOptimalDuration(result.bestWindow!.durationMilliseconds), "15 min 30 s");
});

test("empty plans retain their requested coverage and have no recommendations", () => {
  const result = optimalTimes(plan(0, 60), [], 1, criteria);

  assert.equal(result.totalMilliseconds, 60 * MINUTE);
  assert.equal(result.calculatedMilliseconds, 0);
  assert.equal(result.matchingDayCount, 0);
  assert.equal(result.bestWindow, null);
});

test("duration labels retain minute precision rather than rounding up to hours", () => {
  assert.equal(formatOptimalDuration(75 * MINUTE), "1 h 15 min");
  assert.equal(formatOptimalDuration(1530 * MINUTE), "1 d 1 h 30 min");
  assert.equal(formatOptimalDuration(0), "0 min");
});
