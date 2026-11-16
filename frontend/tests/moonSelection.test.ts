import assert from "node:assert/strict";
import test, { afterEach, beforeEach } from "node:test";
import { BufferGeometry, DoubleSide, Float32BufferAttribute, Group, Mesh, MeshBasicMaterial, PerspectiveCamera, Raycaster, Vector3 } from "three";
import type { TerrainLocationInterface } from "../src/types/terrain/TerrainLocationInterface.ts";
import { createTileGeometry } from "../src/views/home/viewer/moonGeometry.ts";
import { intersectTerrain, locationDirection, terrainLocation } from "../src/views/home/viewer/moonPicking.ts";
import { MoonSelection } from "../src/views/home/viewer/moonSelection.ts";
import { AnimationFrame } from "../src/views/home/viewer/animationFrame.ts";

const frames = new Map<number, FrameRequestCallback>();
const originalRequest = Object.getOwnPropertyDescriptor(globalThis, "requestAnimationFrame");
const originalCancel = Object.getOwnPropertyDescriptor(globalThis, "cancelAnimationFrame");
let nextFrame = 0;

beforeEach(() => {
  Object.defineProperty(globalThis, "requestAnimationFrame", {
    configurable: true,
    value: (callback: FrameRequestCallback) => {
      frames.set(++nextFrame, callback);
      return nextFrame;
    },
  });
  Object.defineProperty(globalThis, "cancelAnimationFrame", { configurable: true, value: (frame: number) => frames.delete(frame) });
});

afterEach(() => {
  frames.clear();

  if (originalRequest) Object.defineProperty(globalThis, "requestAnimationFrame", originalRequest);
  else Reflect.deleteProperty(globalThis, "requestAnimationFrame");

  if (originalCancel) Object.defineProperty(globalThis, "cancelAnimationFrame", originalCancel);
  else Reflect.deleteProperty(globalThis, "cancelAnimationFrame");
});

function flushFrame() {
  const callbacks = [...frames.values()];

  frames.clear();

  for (const callback of callbacks) callback(0);
}

test("frame requests share one redraw, stay idle afterward, and stop on disposal", () => {
  const observed: number[] = [];
  let value = 0;
  const frame = new AnimationFrame(() => observed.push(value));

  for (value = 0; value < 100; value++) frame.request();

  assert.deepEqual(observed, []);
  flushFrame();
  assert.deepEqual(observed, [100]);
  flushFrame();
  assert.deepEqual(observed, [100]);

  frame.request();
  frame.dispose();
  frame.request();
  flushFrame();
  assert.deepEqual(observed, [100]);
});

function createTerrain() {
  const terrain = new Group();
  const material = new MeshBasicMaterial({ side: DoubleSide });

  for (let face = 0; face < 6; face++) {
    const geometry = createTileGeometry({ face, level: 0, x: 0, y: 0 }, new Float32Array(25), 5, 1737400);

    terrain.add(new Mesh(geometry, material));
  }

  terrain.updateMatrixWorld(true);

  return terrain;
}

function createCanvas(): HTMLCanvasElement {
  return Object.assign(new EventTarget(), {
    getBoundingClientRect: () => ({ left: 10, top: 20, width: 100, height: 100 }),
  }) as HTMLCanvasElement;
}

function pointerEvent(type: string, clientX: number, clientY: number) {
  return Object.assign(new Event(type), { clientX, clientY, pointerId: 1, button: 0, buttons: 0, isPrimary: true, pointerType: "mouse" });
}

function createSelection() {
  const canvas = createCanvas();
  const terrain = createTerrain();
  const camera = new PerspectiveCamera(42, 1, 0.01, 20);
  const locations: TerrainLocationInterface[] = [];
  const hoveredLocations: (TerrainLocationInterface | null)[] = [];

  camera.position.set(3, 0, 0);
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld(true);

  const selection = new MoonSelection(
    canvas,
    camera,
    terrain,
    5,
    (location) => locations.push(location),
    (location) => hoveredLocations.push(location)
  );

  return { canvas, terrain, locations, hoveredLocations, selection };
}

test("Moon coordinates use north as Y and east toward negative Z", () => {
  for (const [position, latitude, longitude] of [
    [new Vector3(1, 0, 0), 0, 0],
    [new Vector3(0, 1, 0), 90, 0],
    [new Vector3(0, 0, -1), 0, 90],
    [new Vector3(0, 0, 1), 0, -90],
    [new Vector3(0, -1, 0), -90, 0],
  ] as const) {
    const location = terrainLocation(position.clone().multiplyScalar(1.004));

    assert.equal(location.latitude, latitude);
    assert(Math.abs(location.longitude - longitude) < 1e-12);
    assert(locationDirection(location).distanceTo(position) < 1e-12);
  }
});

test("manual coordinates round trip across both hemispheres and the longitude seam", () => {
  for (const location of [
    { latitude: -89.5, longitude: 47.6 },
    { latitude: 34.123456, longitude: -123.987654 },
    { latitude: 0, longitude: 179.999 },
    { latitude: 0, longitude: -179.999 },
  ]) {
    const actual = terrainLocation(locationDirection(location));

    assert(Math.abs(actual.latitude - location.latitude) < 1e-10);
    assert(Math.abs(actual.longitude - location.longitude) < 1e-10);
  }
});

test("picking skips artificial skirts in front of the physical surface", () => {
  const geometry = new BufferGeometry();
  const positions: number[] = [];

  for (const distance of [2, 3]) {
    positions.push(distance, -1, -1, distance, 1, -1, distance, 1, 1, distance, -1, 1);
  }

  geometry.setAttribute("position", new Float32BufferAttribute(positions, 3));
  geometry.setIndex([0, 1, 2, 0, 2, 3, 4, 5, 6, 4, 6, 7]);

  const terrain = new Group().add(new Mesh(geometry, new MeshBasicMaterial({ side: DoubleSide })));
  const raycaster = new Raycaster(new Vector3(4, 0, 0), new Vector3(-1, 0, 0));

  terrain.updateMatrixWorld(true);

  assert.equal(intersectTerrain(raycaster, terrain, 2)?.x, 2);
});

test("picking ignores hidden cached meshes", () => {
  const terrain = createTerrain();
  const hiddenTile = terrain.children[0]!.clone();

  hiddenTile.scale.setScalar(1.1);
  hiddenTile.visible = false;
  terrain.add(hiddenTile);
  terrain.updateMatrixWorld(true);

  const raycaster = new Raycaster(new Vector3(3, 0, 0), new Vector3(-1, 0, 0));

  assert.equal(intersectTerrain(raycaster, terrain, 5)?.x, 1);
});

test("a click selects a terrain location using the canvas bounds", () => {
  const { canvas, locations, selection } = createSelection();

  canvas.dispatchEvent(pointerEvent("pointerdown", 60, 70));
  canvas.dispatchEvent(pointerEvent("pointerup", 60, 70));

  assert.deepEqual(locations, [{ latitude: 0, longitude: 0 }]);

  selection.dispose();
});

test("dragging does not select a point even when the pointer returns to its start", () => {
  const { canvas, locations, selection } = createSelection();

  canvas.dispatchEvent(pointerEvent("pointerdown", 60, 70));
  canvas.dispatchEvent(pointerEvent("pointermove", 80, 70));
  canvas.dispatchEvent(pointerEvent("pointermove", 60, 70));
  canvas.dispatchEvent(pointerEvent("pointerup", 60, 70));

  assert.deepEqual(locations, []);

  selection.dispose();
});

test("clicking empty space leaves the selected location unchanged", () => {
  const { canvas, locations, selection } = createSelection();

  canvas.dispatchEvent(pointerEvent("pointerdown", 10, 20));
  canvas.dispatchEvent(pointerEvent("pointerup", 10, 20));

  assert.deepEqual(locations, []);

  selection.dispose();
});

test("a second touch or cancelled gesture does not select a point", () => {
  const { canvas, locations, selection } = createSelection();

  canvas.dispatchEvent(pointerEvent("pointerdown", 60, 70));
  canvas.dispatchEvent(Object.assign(pointerEvent("pointerdown", 80, 70), { pointerId: 2, isPrimary: false }));
  canvas.dispatchEvent(pointerEvent("pointerup", 60, 70));
  canvas.dispatchEvent(pointerEvent("pointerdown", 60, 70));
  canvas.dispatchEvent(pointerEvent("pointercancel", 60, 70));
  canvas.dispatchEvent(pointerEvent("pointerup", 60, 70));

  assert.deepEqual(locations, []);

  selection.dispose();
});

test("the selection focus follows manual coordinates and updated terrain heights", () => {
  const { selection, terrain } = createSelection();

  selection.setLocation({ latitude: 0, longitude: 0 });

  assert(Math.abs(selection.position.x - 1) < 1e-8);

  terrain.children[0]!.scale.setScalar(1.001);
  terrain.updateMatrixWorld(true);
  selection.refresh();

  assert(Math.abs(selection.position.x - 1.001) < 1e-8);

  selection.setLocation({ latitude: 0, longitude: 90 });

  assert(Math.abs(selection.position.z + 1) < 1e-8);

  selection.dispose();
});

test("hovering previews terrain without changing selected coordinates", () => {
  const { canvas, locations, hoveredLocations, selection } = createSelection();

  canvas.dispatchEvent(pointerEvent("pointermove", 60, 70));
  flushFrame();
  canvas.dispatchEvent(pointerEvent("pointermove", 65, 70));
  flushFrame();

  assert(Math.abs(hoveredLocations[0]!.latitude) < 1e-10);
  assert(Math.abs(hoveredLocations[0]!.longitude) < 1e-10);
  assert(hoveredLocations[1]!.longitude > 0);
  assert.deepEqual(locations, []);

  canvas.dispatchEvent(pointerEvent("pointermove", 10, 20));
  flushFrame();

  assert.equal(hoveredLocations.at(-1), null);

  selection.dispose();
});

test("hover picking uses only the latest pointer position in each frame", () => {
  const { canvas, locations, hoveredLocations, selection } = createSelection();

  canvas.dispatchEvent(pointerEvent("pointermove", 60, 70));
  canvas.dispatchEvent(pointerEvent("pointermove", 65, 70));

  assert.deepEqual(hoveredLocations, []);
  flushFrame();
  assert.equal(hoveredLocations.length, 1);
  assert(hoveredLocations[0]!.longitude > 0);
  assert.deepEqual(locations, []);

  canvas.dispatchEvent(pointerEvent("pointermove", 60, 70));
  selection.clearHover();
  flushFrame();
  assert.deepEqual(hoveredLocations.slice(1), [null]);

  selection.dispose();
});

test("dragging and touch gestures hide the hover preview", () => {
  const { canvas, locations, hoveredLocations, selection } = createSelection();

  canvas.dispatchEvent(pointerEvent("pointermove", 60, 70));
  flushFrame();
  canvas.dispatchEvent(pointerEvent("pointerdown", 60, 70));
  canvas.dispatchEvent(Object.assign(pointerEvent("pointermove", 80, 70), { buttons: 1 }));
  canvas.dispatchEvent(pointerEvent("pointerup", 80, 70));
  canvas.dispatchEvent(Object.assign(pointerEvent("pointermove", 60, 70), { pointerType: "touch" }));
  flushFrame();

  assert.equal(hoveredLocations.length, 2);
  assert(Math.abs(hoveredLocations[0]!.longitude) < 1e-10);
  assert.equal(hoveredLocations[1], null);
  assert.deepEqual(locations, []);

  selection.dispose();
});

for (const eventType of ["pointerleave", "pointercancel"]) {
  test(`${eventType} hides the preview and cancels selection`, () => {
    const { canvas, locations, hoveredLocations, selection } = createSelection();

    canvas.dispatchEvent(pointerEvent("pointermove", 60, 70));
    flushFrame();
    canvas.dispatchEvent(pointerEvent(eventType, 60, 70));

    assert.equal(hoveredLocations.at(-1), null);

    canvas.dispatchEvent(pointerEvent("pointerdown", 60, 70));
    canvas.dispatchEvent(pointerEvent(eventType, 60, 70));
    canvas.dispatchEvent(pointerEvent("pointerup", 60, 70));
    flushFrame();

    assert.deepEqual(locations, []);

    selection.dispose();
  });
}

test("camera changes can clear the preview without changing selected coordinates", () => {
  const { canvas, locations, hoveredLocations, selection } = createSelection();

  canvas.dispatchEvent(pointerEvent("pointermove", 60, 70));
  flushFrame();
  selection.clearHover();

  assert.equal(hoveredLocations.at(-1), null);
  assert.deepEqual(locations, []);

  selection.dispose();
});

test("disposing selection removes click and hover listeners", () => {
  const { canvas, locations, hoveredLocations, selection } = createSelection();

  canvas.dispatchEvent(pointerEvent("pointermove", 60, 70));
  selection.dispose();
  flushFrame();

  canvas.dispatchEvent(pointerEvent("pointerdown", 60, 70));
  canvas.dispatchEvent(pointerEvent("pointermove", 60, 70));
  canvas.dispatchEvent(pointerEvent("pointerup", 60, 70));
  canvas.dispatchEvent(pointerEvent("pointerleave", 60, 70));
  flushFrame();

  assert.deepEqual(locations, []);
  assert.deepEqual(hoveredLocations, []);
});
