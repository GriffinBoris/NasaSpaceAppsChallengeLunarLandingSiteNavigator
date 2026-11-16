import assert from "node:assert/strict";
import test from "node:test";
import type { SiteHorizonInterface } from "../src/types/terrain/SiteHorizonInterface.ts";
import type { SiteDirectionsInterface } from "../src/types/terrain/SiteTerrainInterface.ts";
import { HORIZON_PLOT, horizonChart } from "../src/views/home/visibility/horizonChart.ts";

const directions: SiteDirectionsInterface = {
  selectionId: 1,
  sun: { azimuthDegrees: [0, 180], elevationDegrees: [-20, 20] },
  earth: { azimuthDegrees: [90, 270], elevationDegrees: [0, 5] },
};

const horizon: SiteHorizonInterface = {
  selectionId: 1,
  azimuthOffsetDegrees: 0,
  bounds: { lowerElevationDegrees: [1, 2, 3, 4], upperElevationDegrees: [2, 3, 4, 5] },
};

const bodyElevations = [directions.sun.elevationDegrees, directions.earth.elevationDegrees];

test("the horizon scale includes the whole plan and keeps the reference horizon between both bodies", () => {
  const chart = horizonChart(horizon, bodyElevations);
  const sun = chart.position({ azimuthDegrees: 90, elevationDegrees: 20 });
  const earth = chart.position({ azimuthDegrees: 270, elevationDegrees: -20 });

  assert.equal(chart.minimumElevation, -25);
  assert.equal(chart.maximumElevation, 25);
  assert.equal(sun.x, 277);
  assert.equal(earth.x, 715);
  assert.ok(sun.y < chart.referenceY && earth.y > chart.referenceY);
  assert.deepEqual(
    chart.compassTicks.map((tick) => tick.label),
    ["N", "E", "S", "W", "N"]
  );
});

test("terrain and uncertainty are drawn as interval steps rather than averaged heights", () => {
  const chart = horizonChart(horizon, bodyElevations);

  assert.ok(chart.terrainPath.startsWith("M 58.00,129.60 L 277.00,129.60 L 277.00,125.20"));
  assert.ok(chart.upperPath.startsWith("M 58.00,125.20 L 277.00,125.20 L 277.00,120.80"));
  assert.ok(chart.uncertaintyPath.endsWith("58.00,125.20 Z"));
});

test("rotated polar horizons wrap at north without joining across the plot", () => {
  const chart = horizonChart({ ...horizon, azimuthOffsetDegrees: 45 }, bodyElevations);

  assert.ok(chart.terrainPath.startsWith("M 58.00,116.40 L 167.50,116.40"));
  assert.ok(chart.terrainPath.includes("L 934.00,116.40"));
  assert.equal(chart.position({ azimuthDegrees: 360, elevationDegrees: 0 }).x, HORIZON_PLOT.left);
  assert.equal(chart.position({ azimuthDegrees: -90, elevationDegrees: 0 }).x, 715);
});

test("missing terrain leaves the skyline empty while retaining the Sun and Earth positions", () => {
  const chart = horizonChart(null, bodyElevations);

  assert.equal(chart.terrainPath, "");
  assert.equal(chart.uncertaintyPath, "");
  assert.equal(chart.position({ azimuthDegrees: 180, elevationDegrees: 0 }).y, chart.referenceY);
  assert.equal(horizonChart(null, []).minimumElevation, -5);
  assert.equal(horizonChart(null, []).maximumElevation, 5);
});
