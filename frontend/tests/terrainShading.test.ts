import assert from "node:assert/strict";
import test from "node:test";
import type { SiteTerrainInterface } from "../src/types/terrain/SiteTerrainInterface.ts";
import { sampleGrid, terrainNormals, terrainPixels } from "../src/views/home/plan/terrainShading.ts";

const SIZE = 9;
const MOON_RADIUS = 1737400;
const EASTERN_SUN = { azimuthDegrees: 90, elevationDegrees: 5 };

function terrain(height: (row: number, column: number) => number, referenceRadiusMeters = MOON_RADIUS): SiteTerrainInterface {
  const heightsMeters = Array.from({ length: SIZE * SIZE }, (_, index) => height(Math.floor(index / SIZE), index % SIZE));

  return { selectionId: 1, radiusMeters: 400, gridSize: SIZE, spacingMeters: 100, referenceRadiusMeters, heightsMeters };
}

function shade(site: SiteTerrainInterface, sun: { azimuthDegrees: number; elevationDegrees: number }, fractions: number[] | null = null) {
  return terrainPixels(site, terrainNormals(site), sun, fractions && { gridSize: 3, fractions });
}

function pixel(pixels: Uint8ClampedArray, row: number, column: number) {
  const offset = (row * SIZE + column) * 4;

  return [pixels[offset]!, pixels[offset + 1]!, pixels[offset + 2]!, pixels[offset + 3]!];
}

test("bilinear sampling skips samples outside the circle", () => {
  const grid = { gridSize: 2, fractions: [0, 1, null, 1] };

  assert.equal(sampleGrid(grid, 0.5, 0), 0.5);
  assert.equal(sampleGrid(grid, 0.5, 1), 1);
  assert.equal(sampleGrid({ gridSize: 2, fractions: [null, null, null, null] }, 0.5, 0.5), null);
});

test("pixels outside the site's circle stay transparent", () => {
  const pixels = shade(
    terrain(() => 0),
    EASTERN_SUN
  );

  assert.equal(pixel(pixels, 0, 0)[3], 0);
  assert.equal(pixel(pixels, 4, 4)[3], 255);
});

test("flat ground visibly darkens as a low Sun sets and stays dark at night", () => {
  const flat = terrain(() => 0);
  const brightness = (elevationDegrees: number) => pixel(shade(flat, { azimuthDegrees: 90, elevationDegrees }), 4, 4)[0]!;

  assert.ok(brightness(4) - brightness(0) > 60);
  assert.equal(brightness(0), brightness(-10));
  assert.ok(brightness(-10) < 30);
  assert.ok(brightness(90) < 250);
});

test("the east side of a ridge is brighter than the west side under an eastern Sun", () => {
  const pixels = shade(
    terrain((_, column) => 300 - Math.abs(column - 4) * 60),
    EASTERN_SUN
  );

  assert.ok(pixel(pixels, 4, 2)[0] < pixel(pixels, 4, 6)[0]);
});

test("shading from Earth's direction lights the opposite ridge face when Earth is west of the site", () => {
  const ridge = terrain((_, column) => 300 - Math.abs(column - 4) * 60);
  const earth = { azimuthDegrees: 270, elevationDegrees: 5 };
  const sunlightPixels = shade(ridge, EASTERN_SUN);
  const earthPixels = shade(ridge, earth);

  assert.ok(pixel(sunlightPixels, 4, 2)[0] < pixel(sunlightPixels, 4, 6)[0]);
  assert.ok(pixel(earthPixels, 4, 2)[0] > pixel(earthPixels, 4, 6)[0]);
  assert.equal(pixel(earthPixels, 4, 2)[0], pixel(earthPixels, 4, 2)[2]);
});

test("ground curving toward a low Sun is brighter than ground curving away", () => {
  const pixels = shade(
    terrain(() => 0, 4000),
    EASTERN_SUN
  );

  assert.ok(pixel(pixels, 4, 0)[0] < pixel(pixels, 4, 8)[0]);
});

test("the sunlight map tints shadow blue and sunlight gold over the shaded terrain", () => {
  const site = terrain(() => 0);
  const plain = pixel(shade(site, EASTERN_SUN), 4, 4);
  const [shadowRed, , shadowBlue] = pixel(shade(site, EASTERN_SUN, Array(9).fill(0)), 4, 4);
  const [sunRed, , sunBlue] = pixel(shade(site, EASTERN_SUN, Array(9).fill(1)), 4, 4);

  assert.equal(plain[0], plain[2]);
  assert.ok(shadowBlue > shadowRed);
  assert.ok(sunRed > sunBlue);
});

test("calculated shadows remove direct Sun lighting while retaining terrain relief", () => {
  const ridge = terrain((_, column) => 300 - Math.abs(column - 4) * 60);
  const shadow = shade(ridge, EASTERN_SUN, Array(9).fill(0));
  const lit = shade(ridge, EASTERN_SUN, Array(9).fill(1));

  const westernSun = { azimuthDegrees: 270, elevationDegrees: 5 };

  assert.deepEqual(shadow, shade(ridge, westernSun, Array(9).fill(0)));
  assert.notDeepEqual(pixel(shadow, 4, 2), pixel(shadow, 4, 6));
  assert.ok(pixel(shadow, 4, 6)[0] > 0);
  assert.ok(pixel(shadow, 4, 6)[0] < pixel(lit, 4, 6)[0]);
  assert.ok(pixel(lit, 4, 2)[0] < pixel(lit, 4, 6)[0]);
});

test("missing sunlight samples preserve the uncalculated terrain shading", () => {
  const ridge = terrain((_, column) => 300 - Math.abs(column - 4) * 60);
  const plain = shade(ridge, EASTERN_SUN);
  const missing = terrainPixels(ridge, terrainNormals(ridge), EASTERN_SUN, { gridSize: 3, fractions: Array(9).fill(null) });

  assert.deepEqual(missing, plain);
});

test("Earth and joint visibility fractions do not act as sunlight shadow masks", () => {
  const ridge = terrain((_, column) => 300 - Math.abs(column - 4) * 60);

  for (const metric of ["earth", "joint"] as const) {
    const pixels = terrainPixels(ridge, terrainNormals(ridge), EASTERN_SUN, { gridSize: 3, fractions: Array(9).fill(0) }, metric);

    assert.ok(pixel(pixels, 4, 2)[0] < pixel(pixels, 4, 6)[0]);
  }
});

test("Sun, Earth, and joint overlays share calculated Sun shadows and terrain relief", () => {
  const ridge = terrain((_, column) => 300 - Math.abs(column - 4) * 60);
  const shadow = { gridSize: 3, fractions: Array(9).fill(0) };
  const sunlight = terrainPixels(ridge, terrainNormals(ridge), EASTERN_SUN, shadow);

  for (const metric of ["earth", "joint"] as const) {
    const pixels = terrainPixels(ridge, terrainNormals(ridge), EASTERN_SUN, shadow, metric, shadow);

    assert.deepEqual(pixels, sunlight);
  }
});

test("Earth visibility colors blocked terrain neutral slate and visible terrain blue", () => {
  const site = terrain(() => 0);
  const normals = terrainNormals(site);
  const blocked = terrainPixels(site, normals, EASTERN_SUN, { gridSize: 3, fractions: Array(9).fill(0) }, "earth");
  const visible = terrainPixels(site, normals, EASTERN_SUN, { gridSize: 3, fractions: Array(9).fill(1) }, "earth");

  const [blockedRed, blockedGreen, blockedBlue] = pixel(blocked, 4, 4);
  const [visibleRed, visibleGreen, visibleBlue] = pixel(visible, 4, 4);

  assert.ok(blockedRed <= blockedBlue);
  assert.ok(blockedRed + blockedGreen + blockedBlue < visibleRed + visibleGreen + visibleBlue);
  assert.ok(visibleBlue > visibleRed && visibleBlue > visibleGreen);
});
