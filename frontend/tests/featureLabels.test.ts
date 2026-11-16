import assert from "node:assert/strict";
import { register } from "node:module";
import test from "node:test";
import { MathUtils, PerspectiveCamera, Raycaster, Sphere, Vector2, Vector3 } from "three";
import { effectScope } from "vue";
import type { LunarFeatureInterface } from "../src/types/terrain/LunarFeatureInterface.ts";

register(new URL("./support/aliases.mjs", import.meta.url), import.meta.url);

const { FeatureLabelView } = await import("../src/views/home/viewer/featureLabelView.ts");
const { layoutFeatureLabels } = await import("../src/views/home/viewer/featureLabelLayout.ts");
const { useFeatureLabels } = await import("../src/views/home/viewer/useFeatureLabels.ts");
const { api } = await import("../src/utils/api.ts");

const feature: LunarFeatureInterface = {
  id: 1,
  usgsId: 1,
  name: "Crater",
  englishName: null,
  featureType: "Crater",
  latitude: 0,
  longitude: 0,
  diameterKm: 20,
  sourceUrl: "https://planetarynames.wr.usgs.gov/Feature/1",
};

function cameraAt(distance: number, width = 1000, height = 800) {
  const camera = new PerspectiveCamera(42, width / height, 0.00005, 20);
  camera.position.set(distance, 0, 0);
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld();
  return camera;
}

function view(distance: number, width = 1000, height = 800) {
  return new FeatureLabelView(cameraAt(distance, width, height), width, height, 1737.4);
}

test("small features appear when zoomed in, while far-side and limb labels stay hidden", () => {
  assert.equal(view(3).project(feature), null);
  const projected = view(1.05).project(feature)!;
  assert.ok(Math.abs(projected.x - 500) < 1e-8);
  assert.ok(Math.abs(projected.y - 400) < 1e-8);
  assert.equal(view(1.05).project({ ...feature, longitude: 180 }), null);
  assert.equal(view(3).project({ ...feature, diameterKm: 1000, longitude: 69 }), null);
  assert.equal(view(1.05).project({ ...feature, diameterKm: null }), null);
});

test("label requests shrink with zoom and include viewport corners", () => {
  const globe = view(3);
  const close = view(1.05);
  assert.ok(close.query.radiusDegrees < globe.query.radiusDegrees);
  assert.ok(close.query.minimumDiameterKm < globe.query.minimumDiameterKm);
  assert.ok(Math.abs(close.query.latitude) < 1e-8);
  assert.ok(Math.abs(close.query.longitude) < 1e-8);
  const camera = cameraAt(1.05);
  const raycaster = new Raycaster();
  raycaster.setFromCamera(new Vector2(1, 1), camera);
  const corner = raycaster.ray.intersectSphere(new Sphere(new Vector3(), 1), new Vector3())!;
  const cornerDistance = MathUtils.radToDeg(new Vector3(1, 0, 0).angleTo(corner));
  assert.ok(cornerDistance <= close.query.radiusDegrees);
  assert.ok(close.query.radiusDegrees < cornerDistance * 1.5);
});

test("labels favor larger features, keep spacing, and leave saved sites and edges clear", () => {
  const features = [feature, { ...feature, id: 2, usgsId: 2, diameterKm: 100 }];
  const screen = { width: 1000, height: 800, project: () => ({ x: 500, y: 400 }) };
  assert.equal(layoutFeatureLabels(features, screen, [], () => 80)[0]!.feature.id, 2);
  assert.equal(layoutFeatureLabels(features, screen, [], () => 80).length, 1);
  assert.deepEqual(
    layoutFeatureLabels(features, screen, [{ left: 450, right: 550, top: 380, bottom: 420 }], () => 80),
    []
  );
  assert.deepEqual(
    layoutFeatureLabels(features, { ...screen, project: () => ({ x: 5, y: 5 }) }, [], () => 80),
    []
  );
});

test("large screens still have a fixed label cap", () => {
  const features = Array.from({ length: 80 }, (_, index) => ({ ...feature, id: index, usgsId: index }));
  const screen = {
    width: 2400,
    height: 1600,
    project: (candidate: LunarFeatureInterface) => ({ x: 100 + (candidate.id % 10) * 210, y: 100 + Math.floor(candidate.id / 10) * 170 }),
  };
  assert.equal(layoutFeatureLabels(features, screen, [], () => 80).length, 24);
});

test("translated labels fit both names and leave room for their second line", () => {
  const translated = { ...feature, name: "Mare", englishName: "Sea of Tranquility", diameterKm: 100 };
  const nearby = { ...feature, id: 2, usgsId: 2 };
  const screen = {
    width: 1000,
    height: 800,
    project: (candidate: LunarFeatureInterface) => ({ x: 500, y: candidate.id === 1 ? 400 : 440 }),
  };
  const labels = layoutFeatureLabels([translated, nearby], screen, [], (name) => name.length * 8);

  assert.equal(labels.length, 1);
  assert.equal(labels[0]!.feature.englishName, "Sea of Tranquility");
  assert(labels[0]!.width >= "Sea of Tranquility".length * 8);
  assert.deepEqual(
    layoutFeatureLabels([translated], screen, [{ left: 450, right: 550, top: 420, bottom: 450 }], () => 80),
    []
  );
  assert.equal(layoutFeatureLabels([{ ...translated, englishName: null }, nearby], screen, [], () => 80).length, 2);
});

test("label requests are debounced and stale responses cannot replace the current view", async (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  const originalRequest = Object.getOwnPropertyDescriptor(globalThis, "requestAnimationFrame");
  const originalCancel = Object.getOwnPropertyDescriptor(globalThis, "cancelAnimationFrame");
  let nextFrame = 0;
  const frames = new Map<number, FrameRequestCallback>();
  Object.defineProperty(globalThis, "requestAnimationFrame", {
    configurable: true,
    value: (callback: FrameRequestCallback) => {
      frames.set(++nextFrame, callback);
      return nextFrame;
    },
  });
  Object.defineProperty(globalThis, "cancelAnimationFrame", { configurable: true, value: (frame: number) => frames.delete(frame) });
  context.after(() => {
    if (originalRequest) Object.defineProperty(globalThis, "requestAnimationFrame", originalRequest);
    else Reflect.deleteProperty(globalThis, "requestAnimationFrame");
    if (originalCancel) Object.defineProperty(globalThis, "cancelAnimationFrame", originalCancel);
    else Reflect.deleteProperty(globalThis, "cancelAnimationFrame");
  });
  function render() {
    const callbacks = [...frames.values()];
    frames.clear();
    for (const callback of callbacks) callback(0);
  }
  const first = Promise.withResolvers<LunarFeatureInterface[]>();
  const second = Promise.withResolvers<LunarFeatureInterface[]>();
  const requests: AbortSignal[] = [];
  context.mock.method(api.features, "labels", (query, signal: AbortSignal) => {
    assert.ok(query.radiusDegrees > 0);
    requests.push(signal);
    return requests.length === 1 ? first.promise : second.promise;
  });
  let currentView = view(1.05);
  const scope = effectScope();
  const labels = scope.run(() =>
    useFeatureLabels(
      () => currentView,
      () => [],
      () => 80
    )
  )!;
  labels.update();
  render();
  context.mock.timers.tick(199);
  assert.equal(requests.length, 0);
  context.mock.timers.tick(1);
  currentView = view(1.06);
  labels.update();
  render();
  assert.equal(requests[0]!.aborted, true);
  context.mock.timers.tick(200);
  second.resolve([feature]);
  await Promise.resolve();
  render();
  assert.equal(labels.labels.value.length, 1);
  first.resolve([{ ...feature, name: "Old response" }]);
  await Promise.resolve();
  render();
  assert.equal(labels.labels.value[0]!.feature.name, "Crater");
  currentView = view(1.07);
  labels.update();
  render();
  scope.stop();
  context.mock.timers.tick(200);
  assert.equal(requests.length, 2);
  assert.equal(frames.size, 0);
});
