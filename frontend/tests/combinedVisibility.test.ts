import assert from "node:assert/strict";
import test from "node:test";
import type { CombinedGridInterface, SiteCombinedVisibilityInterface } from "../src/types/terrain/SiteCombinedVisibilityInterface.ts";
import { bestCombinedSample, combinedPlanGrid, mergeCombinedVisibility } from "../src/views/home/plan/combinedVisibility.ts";
import { formatCoordinates } from "../src/views/home/sites/coordinateFormat.ts";

const geometry: CombinedGridInterface = {
  gridSize: 5,
  radiusMeters: 1000,
  spacingMeters: 500,
  samples: Array.from({ length: 25 }, (_, index) => ({ latitude: index, longitude: -index, visibleSeconds: 0 })),
};

test("across-plan fractions use only checked duration and keep the circle mask", () => {
  const combined: SiteCombinedVisibilityInterface = {
    selectionId: 1,
    resultRevision: 2,
    reset: true,
    totalSeconds: 9600,
    checkedSeconds: 6000,
    checkedFrames: 2,
    expectedFrames: 3,
    grid: { ...geometry, samples: [null, { latitude: 1, longitude: 2, visibleSeconds: 3600 }] },
    previews: [],
  };

  assert.deepEqual(combinedPlanGrid(combined), { gridSize: 5, fractions: [null, 0.6] });
  assert.equal(combinedPlanGrid({ ...combined, checkedSeconds: 0 }), null);
  assert.equal(combinedPlanGrid({ ...combined, grid: null }), null);
});

test("best sample ranks duration and picks the nearest center among ties", () => {
  const fractions = Array<number | null>(25).fill(0);

  fractions[0] = null;
  fractions[2] = 0.9;
  fractions[11] = 0.9;
  fractions[12] = 0.5;
  const best = bestCombinedSample({ gridSize: 5, fractions }, geometry);

  assert.deepEqual(best, { latitude: 11, longitude: -11, x: 25, y: 50, fraction: 0.9, matchingSamples: 2 });
});

test("a later higher score replaces earlier ties and counts only the highest score", () => {
  const fractions = Array<number | null>(25).fill(0.5);

  fractions[24] = 1;

  assert.deepEqual(bestCombinedSample({ gridSize: 5, fractions }, geometry), {
    latitude: 24,
    longitude: -24,
    x: 100,
    y: 100,
    fraction: 1,
    matchingSamples: 1,
  });
});

test("selected-time preview indexes map to the exact full-grid coordinates", () => {
  const best = bestCombinedSample({ gridSize: 3, fractions: [null, 0, null, 0, 0, 1, null, 0, null] }, geometry);

  assert.deepEqual(best, { latitude: 14, longitude: -14, x: 100, y: 50, fraction: 1, matchingSamples: 1 });
});

test("blocked or unknown areas do not invent a best location", () => {
  assert.equal(bestCombinedSample({ gridSize: 5, fractions: Array(25).fill(0) }, geometry), null);
  assert.equal(bestCombinedSample({ gridSize: 5, fractions: Array(25).fill(null) }, geometry), null);
});

test("best-location coordinates retain finer precision than site summary labels", () => {
  assert.equal(formatCoordinates(-89.123456, 40.654321, 4), "89.1235°S 40.6543°E");
  assert.equal(formatCoordinates(-89.123456, 40.654321), "89.12°S 40.65°E");
});

test("combined updates retain older previews without adding accumulated duration twice", () => {
  const current: SiteCombinedVisibilityInterface = {
    selectionId: 1,
    resultRevision: 2,
    reset: true,
    totalSeconds: 6000,
    checkedSeconds: 3600,
    checkedFrames: 1,
    expectedFrames: 2,
    grid: geometry,
    previews: [{ frameId: 1, gridSize: 1, fractions: [1] }],
  };
  const changed = {
    ...current,
    resultRevision: 4,
    reset: false,
    checkedSeconds: 6000,
    checkedFrames: 2,
    previews: [{ frameId: 2, gridSize: 1, fractions: [0] }],
  };
  const merged = mergeCombinedVisibility(current, changed);

  assert.deepEqual(
    merged.previews.map((preview) => preview.frameId),
    [1, 2]
  );
  assert.equal(merged.checkedSeconds, 6000);
  assert.deepEqual(mergeCombinedVisibility(merged, changed), merged);
  assert.deepEqual(mergeCombinedVisibility(merged, { ...changed, reset: true }).previews, changed.previews);
});
