import assert from "node:assert/strict";
import test from "node:test";
import { estimateSolarPower, solarPanelError } from "../src/views/home/visibility/solarPower.ts";

const panel = { areaSquareMeters: 1, efficiencyPercent: 30 };

test("a fully visible overhead Sun supplies the same estimate to both panel orientations", () => {
  const estimate = estimateSolarPower(90, 1, panel)!;

  assert.equal(estimate.levelIrradianceWattsPerSquareMeter, 1361);
  assert.equal(estimate.trackingIrradianceWattsPerSquareMeter, 1361);
  assert.equal(estimate.levelPowerWatts, 408.3);
  assert.equal(estimate.trackingPowerWatts, 408.3);
});

test("a low Sun reduces level-panel output even when the full disk is visible", () => {
  const estimate = estimateSolarPower(30, 1, panel)!;

  assert.ok(Math.abs(estimate.levelPowerWatts - 204.15) < 1e-9);
  assert.equal(estimate.trackingPowerWatts, 408.3);
  assert.ok(Math.abs(estimate.levelIncidenceFraction - 0.5) < 1e-9);
});

test("partial terrain obstruction scales both estimates and complete obstruction produces zero", () => {
  const partial = estimateSolarPower(30, 0.25, panel)!;
  const blocked = estimateSolarPower(30, 0, panel)!;

  assert.ok(Math.abs(partial.levelPowerWatts - 51.0375) < 1e-9);
  assert.equal(partial.trackingPowerWatts, 102.075);
  assert.equal(blocked.levelPowerWatts, 0);
  assert.equal(blocked.trackingPowerWatts, 0);
});

test("a Sun-center at or below the reference horizon contributes no power to a level panel", () => {
  assert.equal(estimateSolarPower(0, 0.5, panel)!.levelPowerWatts, 0);
  assert.equal(estimateSolarPower(-1, 0.1, panel)!.levelPowerWatts, 0);
  assert.ok(estimateSolarPower(-1, 0.1, panel)!.trackingPowerWatts > 0);
});

test("area and efficiency affect electrical output without changing received irradiance", () => {
  const estimate = estimateSolarPower(90, 1, { areaSquareMeters: 2, efficiencyPercent: 15 })!;

  assert.equal(estimate.levelPowerWatts, 408.3);
  assert.equal(estimate.levelIrradianceWattsPerSquareMeter, 1361);
});

test("invalid panel settings withhold estimates rather than clamping or retaining a previous value", () => {
  for (const areaSquareMeters of [0, -1, NaN, Infinity]) {
    const invalid = { ...panel, areaSquareMeters };

    assert.equal(solarPanelError(invalid), "Enter a panel area greater than zero.");
    assert.equal(estimateSolarPower(90, 1, invalid), null);
  }

  for (const efficiencyPercent of [0, -1, 101, NaN, Infinity]) {
    const invalid = { ...panel, efficiencyPercent };

    assert.equal(solarPanelError(invalid), "Enter an efficiency greater than zero and no more than 100%.");
    assert.equal(estimateSolarPower(90, 1, invalid), null);
  }

  assert.equal(estimateSolarPower(90, 1, { areaSquareMeters: 1, efficiencyPercent: 100 })!.levelPowerWatts, 1361);
});
