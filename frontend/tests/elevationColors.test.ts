import assert from "node:assert/strict";
import test from "node:test";
import { elevationColor } from "../src/views/home/viewer/elevationColors.ts";
import { createTileGeometry } from "../src/views/home/viewer/moonGeometry.ts";

test("elevation colors follow a fixed scale with clamped endpoints", () => {
  assert.equal(elevationColor(-10000).getHexString(), "440154");
  assert.equal(elevationColor(-20000).getHexString(), "440154");
  assert.equal(elevationColor(12000).getHexString(), "fde725");
  assert.equal(elevationColor(20000).getHexString(), "fde725");
  assert.equal(elevationColor(1000).getHexString(), "21918c");
});

test("equal elevations have the same color at different tile levels and on skirts", () => {
  const heights = new Float32Array(25).fill(1000);
  const parent = createTileGeometry({ face: 0, level: 0, x: 0, y: 0 }, heights, 5, 1737400);
  const child = createTileGeometry({ face: 0, level: 3, x: 0, y: 0 }, heights, 5, 1737400);
  const expected = elevationColor(1000);

  for (const geometry of [parent, child]) {
    const colors = geometry.getAttribute("color");

    for (let vertexIndex = 0; vertexIndex < colors.count; vertexIndex++) {
      assert(Math.abs(colors.getX(vertexIndex) - expected.r) < 1e-6);
      assert(Math.abs(colors.getY(vertexIndex) - expected.g) < 1e-6);
      assert(Math.abs(colors.getZ(vertexIndex) - expected.b) < 1e-6);
    }

    geometry.dispose();
  }
});
