import assert from "node:assert/strict";
import test from "node:test";
import { PerspectiveCamera, Vector3 } from "three";
import { moonFixedPosition, skyBodyPlacement } from "../src/views/home/viewer/ephemerisGeometry.ts";
import { CelestialScene } from "../src/views/home/viewer/celestialScene.ts";

const referenceRadiusKm = 1737.4;

test("SPICE axes become the viewer's lunar north and east axes", () => {
  assert(moonFixedPosition([referenceRadiusKm, 0, 0], referenceRadiusKm).equals(new Vector3(1, 0, 0)));
  assert(moonFixedPosition([0, referenceRadiusKm, 0], referenceRadiusKm).equals(new Vector3(0, 0, -1)));
  assert(moonFixedPosition([0, 0, referenceRadiusKm], referenceRadiusKm).equals(new Vector3(0, 1, 0)));
});

test("sky placement preserves observer-relative direction and angular size", () => {
  const body = { positionKm: [400000, 0, 0] as [number, number, number], radiusKm: 6371 };
  const observer = new Vector3(2, 0, 0);
  const placement = skyBodyPlacement(body, observer, referenceRadiusKm);

  assert(placement.position.distanceTo(new Vector3(1000, 0, 0)) < 1e-9);
  assert(Math.abs(placement.radius / 1000 - 6371 / (400000 - 2 * referenceRadiusKm)) < 1e-12);

  const sidewaysObserver = new Vector3(0, 1, 0);
  const shifted = skyBodyPlacement(body, sidewaysObserver, referenceRadiusKm);

  assert(shifted.position.y < 0);
});

test("camera rotation changes the sky view without moving physical body directions", () => {
  const sky = new CelestialScene(referenceRadiusKm * 1000);
  const camera = new PerspectiveCamera(42, 1, 0.01, 20);

  sky.setEphemeris({
    timestamp: "2026-11-11T12:00:00Z",
    frame: "MOON_ME_DE421",
    sun: { positionKm: [0, 150000000, 0], radiusKm: 695700 },
    earth: { positionKm: [400000, 0, 0], radiusKm: 6371 },
  });
  camera.position.set(3, 0, 0);
  camera.lookAt(0, 0, 0);
  sky.updateCamera(camera);

  const sunPosition = sky.scene.children[0]!.position.clone();
  const earthPosition = sky.scene.children[1]!.position.clone();

  camera.lookAt(0, 1, 0);
  sky.updateCamera(camera);

  assert(sky.camera.quaternion.equals(camera.quaternion));
  assert(sky.scene.children[0]!.position.equals(sunPosition));
  assert(sky.scene.children[1]!.position.equals(earthPosition));

  sky.dispose();
  assert.equal(sky.scene.children.length, 0);
});
