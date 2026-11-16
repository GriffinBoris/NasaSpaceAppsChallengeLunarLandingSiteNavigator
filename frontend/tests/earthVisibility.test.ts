import assert from "node:assert/strict";
import test from "node:test";
import type { SunlightFrameDetailInterface, SunlightFrameInterface } from "../src/types/terrain/SunlightFrameInterface.ts";
import type { SunlightStudyInterface } from "../src/types/terrain/SunlightStudyInterface.ts";
import { earthCenterSeries, earthMetrics, nextEarthChange } from "../src/views/home/visibility/earthAnalysis.ts";
import {
  frameFraction,
  framePatch,
  frameResultKey,
  frameVisibilityGrid,
  patchFraction,
  patchMetric,
} from "../src/views/home/visibility/visibilityView.ts";

const study: SunlightStudyInterface = {
  id: 1,
  name: "Visibility",
  datasetId: 1,
  selections: [{ id: 1, name: "Rim", latitude: -89.9, longitude: 180, radiusMeters: 2500 }],
  startTime: "2026-11-11T00:00:00Z",
  endTime: "2026-11-11T01:30:00Z",
  stepSeconds: 900,
  workerCount: 4,
  expectedFrames: 6,
  completedFrames: 0,
  savedResults: 0,
  resultRevision: 0,
  status: "running",
  progress: null,
  errorMessage: "",
  createdTs: "2026-11-11T00:00:00Z",
};

function frame(index: number, visible: boolean | null): SunlightFrameInterface {
  return {
    id: index + 1,
    studyId: 1,
    selectionId: 1,
    timestamp: new Date(Date.parse(study.startTime) + index * 900000).toISOString(),
    visibleSunFraction: 0.8,
    visibleEarthFraction: visible === null ? null : Number(visible),
    earthCenterVisible: visible,
    jointVisibleShare: visible === null ? null : 0.5,
    resultRevision: 1,
    thumbnail: null,
    earthThumbnail: null,
  };
}

test("Earth windows keep missing results separate from visibility and obstruction", () => {
  const frames = [frame(0, true), frame(1, true), frame(3, false), frame(4, false), frame(5, true)];
  const series = earthCenterSeries(study, frames, 1);
  const metrics = earthMetrics(series);

  assert.deepEqual(series, [1, 1, null, 0, 0, 1]);
  assert.equal(metrics.availableShare, 0.6);
  assert.deepEqual(metrics.windows, [
    { startIndex: 0, length: 2 },
    { startIndex: 5, length: 1 },
  ]);
  assert.deepEqual(metrics.outages, [{ startIndex: 3, length: 2 }]);
  assert.deepEqual(nextEarthChange(series, 0, 900), { label: "Next Earth change", value: "Missing results" });
  assert.deepEqual(nextEarthChange(series, 3, 900), { label: "Next Earthrise", value: "In 30 min" });
  assert.deepEqual(nextEarthChange([1, 0], 0, 900), { label: "Next Earthset", value: "In 15 min" });
  assert.deepEqual(nextEarthChange([1, 1], 0, 900), { label: "Earth after this time", value: "Visible to plan end" });
  assert.deepEqual(nextEarthChange([null, 1], 0, 900), { label: "Earth at this time", value: "Not calculated" });
  assert.equal(earthMetrics([null, null]).availableShare, null);
});

test("both visibility maps use the current frame's preview while full details are loading", () => {
  const blocked = {
    ...frame(0, false),
    thumbnail: { gridSize: 2, fractions: [0, 0.5, 1, null] },
    earthThumbnail: { gridSize: 2, fractions: [0, 0, 0, null] },
  };
  const visible = { ...frame(1, true), earthThumbnail: { gridSize: 2, fractions: [1, 1, 1, null] } };

  assert.deepEqual(frameVisibilityGrid(blocked, null, "sunlight"), blocked.thumbnail);
  assert.deepEqual(frameVisibilityGrid(blocked, null, "earth"), blocked.earthThumbnail);
  assert.deepEqual(frameVisibilityGrid(visible, null, "earth"), visible.earthThumbnail);
  assert.equal(frameVisibilityGrid(frame(2, null), null, "earth"), null);
  assert.equal(frameVisibilityGrid(null, null, "earth"), null);
});

test("body metrics and frame cache identities change when Earth results arrive", () => {
  const before = frame(0, null);
  const after = { ...frame(0, false), resultRevision: 2 };

  assert.equal(frameFraction(before, "earth"), null);
  assert.equal(frameFraction(after, "earth"), 0);
  assert.equal(frameFraction(after, "sunlight"), 0.8);
  assert.equal(frameFraction(after, "joint"), 0.5);
  assert.notEqual(frameResultKey(before), frameResultKey(after));
});

test("joint maps require sunlight and Earth-center visibility at the same sample", () => {
  const metadata = {
    datasetId: 1,
    timestamp: study.startTime,
    latitude: -89.9,
    longitude: 180,
    frame: "MOON_ME_DE421",
    elevationMeters: 0,
    analysisLevel: 9,
    diskSampleCount: 1024,
    samplingConverged: true,
    fractionTolerance: 0.005,
  };
  const sunlight = {
    ...metadata,
    sunElevationDegrees: 1,
    sunAzimuthDegrees: 90,
    sunAngularRadiusDegrees: 0.27,
    visibleSunFraction: 1,
  };
  const earth = {
    ...metadata,
    earthElevationDegrees: 0.5,
    earthAzimuthDegrees: 180,
    earthAngularRadiusDegrees: 0.95,
    visibleEarthFraction: 0.8,
    earthCenterVisible: true,
  };
  const geometry = { gridSize: 3, radiusMeters: 2500, spacingMeters: 2500 };
  const sunlightPoints = [null, 1, null, 0, 1, 0, null, 1, null];
  const earthPoints = [null, false, null, true, true, true, null, false, null];
  const detail: SunlightFrameDetailInterface = {
    ...frame(0, true),
    jointVisibleShare: 0.2,
    resultRevision: 1,
    result: {
      center: sunlight,
      patch: {
        ...geometry,
        center: sunlight,
        points: sunlightPoints.map((fraction) => (fraction === null ? null : { visibleSunFraction: fraction, samplingConverged: true })),
      },
    },
    earthResult: {
      center: earth,
      patch: {
        ...geometry,
        center: earth,
        points: earthPoints.map((visible) =>
          visible === null ? null : { earthCenterVisible: visible, visibleEarthFraction: Number(visible), samplingConverged: true }
        ),
      },
    },
  };
  const patch = framePatch(detail, "joint")!;

  assert.deepEqual(
    patch.points.map((point) => (point === null ? null : patchFraction(point))),
    [null, 0, null, 0, 1, 0, null, 0, null]
  );
  assert.equal(patchMetric(patch), "joint");
  assert.equal(patchMetric(framePatch(detail, "earth")!), "earth");
  assert.equal(framePatch({ ...detail, jointVisibleShare: null }, "joint"), null);

  assert.deepEqual(frameVisibilityGrid(detail, detail, "earth"), { gridSize: 3, fractions: [null, 0, null, 1, 1, 1, null, 0, null] });
  assert.deepEqual(frameVisibilityGrid(detail, detail, "joint"), { gridSize: 3, fractions: [null, 0, null, 0, 1, 0, null, 0, null] });
  assert.equal(frameVisibilityGrid(detail, null, "joint"), null);
  assert.equal(frameVisibilityGrid({ ...detail, jointVisibleShare: null, resultRevision: 2 }, detail, "joint"), null);

  const nextFrame = { ...frame(1, false), earthThumbnail: { gridSize: 2, fractions: [0, 0, 0, null] } };

  assert.deepEqual(frameVisibilityGrid(nextFrame, detail, "earth"), nextFrame.earthThumbnail);
  assert.equal(frameVisibilityGrid(nextFrame, detail, "joint"), null);
});
