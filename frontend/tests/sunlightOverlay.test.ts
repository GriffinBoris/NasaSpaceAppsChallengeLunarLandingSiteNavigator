import assert from "node:assert/strict";
import test from "node:test";
import { Color, DataTexture, LinearFilter, MeshStandardMaterial, ShaderLib, Vector3, type IUniform } from "three";
import type { IlluminationPatchInterface } from "../src/types/terrain/IlluminationPatchInterface.ts";
import type { EarthVisibilityPatchInterface } from "../src/types/terrain/EarthVisibilityInterface.ts";
import {
  createSunlightTexture,
  EARTH_VISIBILITY_COLORS,
  SELECTION_COLOR,
  SUNLIGHT_COLORS,
  SunlightOverlay,
  visibilityFractionColor,
} from "../src/views/home/viewer/sunlightOverlay.ts";

const patch: IlluminationPatchInterface = {
  center: {
    datasetId: 2,
    timestamp: "2026-11-11T12:00:00Z",
    latitude: 0,
    longitude: 0,
    frame: "MOON_ME_DE421",
    elevationMeters: 0,
    analysisLevel: 7,
    sunElevationDegrees: 1,
    sunAzimuthDegrees: 90,
    sunAngularRadiusDegrees: 0.27,
    visibleSunFraction: 0.5,
    diskSampleCount: 1024,
    samplingConverged: true,
    fractionTolerance: 0.005,
  },
  gridSize: 3,
  radiusMeters: 5000,
  spacingMeters: 5000,
  points: [0, 0.25, 0.5, 0.75, 1, 0.01, 0.99, 0, 1].map((fraction) => ({ visibleSunFraction: fraction, samplingConverged: true })),
};

function compileMaterial(material: MeshStandardMaterial) {
  const uniforms: Record<string, IUniform<number | Vector3 | Color | DataTexture | null>> = {};
  const shader = {
    uniforms,
    vertexShader: ShaderLib.standard.vertexShader,
    fragmentShader: ShaderLib.standard.fragmentShader,
  };

  Reflect.apply(material.onBeforeCompile, material, [shader]);

  return shader;
}

test("Earth colors use the shared slate for blocked views and light blue for visible views", () => {
  const blocked = new Color(visibilityFractionColor(0, "earth"));
  const visible = new Color(visibilityFractionColor(1, "earth"));

  assert.equal(blocked.getHexString(), "3b4559");
  assert.equal(visible.getHexString(), "62c4ee");

  const luminance = (color: Color) => 0.2126 * color.r + 0.7152 * color.g + 0.0722 * color.b;

  assert.ok((luminance(visible) + 0.05) / (luminance(blocked) + 0.05) > 2.5);
  assert.equal(visibilityFractionColor(0, "sunlight"), new Color(SUNLIGHT_COLORS.shadow).getStyle());
});

test("switching from Earth visibility restores sunlight colors and keeps the selection color", () => {
  const material = new MeshStandardMaterial();
  const overlay = new SunlightOverlay(material, 1737400);
  const shader = compileMaterial(material);
  const earthPatch: EarthVisibilityPatchInterface = {
    ...patch,
    center: {
      ...patch.center,
      earthElevationDegrees: 1,
      earthAzimuthDegrees: 90,
      earthAngularRadiusDegrees: 1,
      visibleEarthFraction: 0.5,
      earthCenterVisible: true,
    },
    points: patch.points.map((point) =>
      point === null ? null : { visibleEarthFraction: point.visibleSunFraction, earthCenterVisible: true, samplingConverged: true }
    ),
  };

  overlay.setPatch(earthPatch);
  assert.equal(shader.uniforms.sunlightShadows!.value, 0);
  assert.equal((shader.uniforms.shadowColor!.value as Color).getHexString(), new Color(EARTH_VISIBILITY_COLORS.blocked).getHexString());
  assert.equal((shader.uniforms.sunlightColor!.value as Color).getHexString(), new Color(EARTH_VISIBILITY_COLORS.visible).getHexString());
  assert.equal((shader.uniforms.selectionColor!.value as Color).getHexString(), new Color(SELECTION_COLOR).getHexString());

  overlay.setPatch(patch);
  assert.equal(shader.uniforms.sunlightShadows!.value, 1);
  assert.equal((shader.uniforms.shadowColor!.value as Color).getHexString(), new Color(SUNLIGHT_COLORS.shadow).getHexString());
  overlay.dispose();
  material.dispose();
});

test("inspection lighting bypasses Sun shadows without replacing the visibility map", () => {
  const material = new MeshStandardMaterial();
  const overlay = new SunlightOverlay(material, 1737400);
  const shader = compileMaterial(material);

  overlay.setPatch(patch);
  overlay.setDisplayMode("illumination");

  const texture = shader.uniforms.sunlightTexture!.value;

  overlay.setFullIllumination(true);

  assert.equal(shader.uniforms.inspectionLighting!.value, 1);
  assert.equal(shader.uniforms.sunlightTexture!.value, texture);
  assert.equal(shader.uniforms.sunlightMode!.value, 1);

  overlay.setPatch({ ...patch, points: patch.points.map(() => ({ visibleJointFraction: 0 })) });

  assert.equal(shader.uniforms.sunlightShadows!.value, 0);
  assert.equal(shader.uniforms.inspectionLighting!.value, 1);

  overlay.setPatch(patch);
  overlay.setFullIllumination(false);

  assert.equal(shader.uniforms.inspectionLighting!.value, 0);
  assert.equal(shader.uniforms.sunlightShadows!.value, 1);

  overlay.setPatch(null);

  assert.equal(shader.uniforms.sunlightShadows!.value, 0);

  overlay.dispose();
  material.dispose();
});

test("the visibility raster preserves sample order and fractions within byte precision", () => {
  const texture = createSunlightTexture(patch);

  assert.equal(texture.image.width, 3);
  assert.equal(texture.image.height, 3);
  assert.equal(texture.minFilter, LinearFilter);
  assert.equal(texture.magFilter, LinearFilter);

  for (let index = 0; index < patch.points.length; index++) {
    const fraction = texture.image.data[index * 4]! / 255;

    assert(Math.abs(fraction - patch.points[index]!.visibleSunFraction) <= 0.5 / 255);
    assert.equal(texture.image.data[index * 4 + 1], texture.image.data[index * 4]);
    assert.equal(texture.image.data[index * 4 + 2], 255);
    assert.equal(texture.image.data[index * 4 + 3], 255);
  }

  texture.dispose();
});

test("Earth overlays retain their visibility colors and carry the paired Sun shadow mask", () => {
  const earthPatch: EarthVisibilityPatchInterface = {
    ...patch,
    center: {
      ...patch.center,
      earthElevationDegrees: 1,
      earthAzimuthDegrees: 90,
      earthAngularRadiusDegrees: 1,
      visibleEarthFraction: 1,
      earthCenterVisible: true,
    },
    points: patch.points.map(() => ({ visibleEarthFraction: 1, earthCenterVisible: true, samplingConverged: true })),
  };
  const material = new MeshStandardMaterial();
  const overlay = new SunlightOverlay(material, 1737400);
  const shader = compileMaterial(material);

  overlay.setPatch(earthPatch, patch);

  const texture = shader.uniforms.sunlightTexture!.value;

  assert(texture instanceof DataTexture);
  assert.equal(shader.uniforms.sunlightShadows!.value, 1);

  for (let index = 0; index < patch.points.length; index++) {
    assert.equal(texture.image.data[index * 4], 255);
    assert.equal(texture.image.data[index * 4 + 1], Math.round(patch.points[index]!.visibleSunFraction * 255));
    assert.equal(texture.image.data[index * 4 + 2], 255);
  }

  overlay.dispose();
  material.dispose();
});

test("display modes reuse the computed raster and disable it for terrain or elevation", () => {
  const material = new MeshStandardMaterial();
  const overlay = new SunlightOverlay(material, 1737400);
  const shader = compileMaterial(material);

  overlay.setDisplayMode("illumination");

  assert.equal(shader.uniforms.sunlightMode!.value, 0);

  overlay.setPatch(patch);

  const texture = shader.uniforms.sunlightTexture!.value;

  assert(texture instanceof DataTexture);
  assert.equal(shader.uniforms.sunlightMode!.value, 1);

  for (const [mode, expected] of [
    ["sunlight", 2],
    ["shadow", 3],
    ["terrain", 0],
    ["elevation", 0],
    ["illumination", 1],
  ] as const) {
    overlay.setDisplayMode(mode);

    assert.equal(shader.uniforms.sunlightMode!.value, expected);
    assert.equal(shader.uniforms.sunlightTexture!.value, texture);
  }

  overlay.dispose();
  material.dispose();
});

test("the raster uses the selected point's lunar frame and physical radius", () => {
  const material = new MeshStandardMaterial();
  const overlay = new SunlightOverlay(material, 1737400);
  const shader = compileMaterial(material);

  overlay.setPatch({ ...patch, center: { ...patch.center, latitude: 90, longitude: 90 } });

  const center = shader.uniforms.sunlightCenter!.value;
  const east = shader.uniforms.sunlightEast!.value;
  const north = shader.uniforms.sunlightNorth!.value;

  assert(center instanceof Vector3);
  assert(east instanceof Vector3);
  assert(north instanceof Vector3);
  assert(center.distanceTo(new Vector3(0, 1, 0)) < 1e-12);
  assert(east.distanceTo(new Vector3(-1, 0, 0)) < 1e-12);
  assert(north.distanceTo(new Vector3(0, 0, 1)) < 1e-12);
  assert.equal(shader.uniforms.sunlightRadius!.value, 5000 / 1737400);
  assert.equal(shader.uniforms.sunlightGridSize!.value, 3);

  overlay.dispose();
  material.dispose();
});

test("terrain material recompilation keeps the same live overlay uniforms", () => {
  const material = new MeshStandardMaterial();
  const overlay = new SunlightOverlay(material, 1737400);
  const firstShader = compileMaterial(material);

  overlay.setPatch(patch);
  overlay.setDisplayMode("shadow");

  const secondShader = compileMaterial(material);

  assert.equal(secondShader.uniforms.sunlightTexture, firstShader.uniforms.sunlightTexture);
  assert.equal(secondShader.uniforms.sunlightMode!.value, 3);

  overlay.dispose();
  material.dispose();
});

test("replacing, clearing, and disposing overlays releases their textures", () => {
  const material = new MeshStandardMaterial();
  const overlay = new SunlightOverlay(material, 1737400);
  const shader = compileMaterial(material);
  let disposedTextures = 0;

  for (let index = 0; index < 3; index++) {
    overlay.setPatch(patch);

    const texture = shader.uniforms.sunlightTexture!.value;

    assert(texture instanceof DataTexture);
    texture.addEventListener("dispose", () => disposedTextures++);

    if (index === 1) {
      overlay.setPatch(null);

      assert.equal(shader.uniforms.sunlightTexture!.value, null);
      assert.equal(shader.uniforms.sunlightMode!.value, 0);
    }
  }

  overlay.dispose();

  assert.equal(disposedTextures, 3);

  material.dispose();
});

test("circular rasters leave uncomputed exterior samples transparent", () => {
  const texture = createSunlightTexture({ ...patch, points: patch.points.map((point, index) => (index % 2 === 0 ? null : point)) });

  for (let index = 0; index < patch.points.length; index++) {
    assert.equal(texture.image.data[index * 4 + 3], index % 2 === 0 ? 0 : 255);
  }

  texture.dispose();
});

test("the selection circle updates independently of the computed map", () => {
  const material = new MeshStandardMaterial();
  const overlay = new SunlightOverlay(material, 1737400);
  const shader = compileMaterial(material);

  overlay.setSelection({ latitude: 0, longitude: 0 }, 1250);

  assert.equal(shader.uniforms.selectionRadius!.value, 1250 / 1737400);
  assert.deepEqual(shader.uniforms.selectionCenter!.value, new Vector3(1, 0, -0));
  assert.equal(shader.uniforms.sunlightTexture!.value, null);

  overlay.setSelection({ latitude: 91, longitude: 0 }, 1250);

  assert.equal(shader.uniforms.selectionRadius!.value, -1);

  overlay.dispose();
  material.dispose();
});

test("hover previews share the radius without moving the selected circle", () => {
  const material = new MeshStandardMaterial();
  const overlay = new SunlightOverlay(material, 1737400);
  const shader = compileMaterial(material);

  overlay.setSelection({ latitude: 0, longitude: 0 }, 1250);
  overlay.setHoverLocation({ latitude: 90, longitude: 0 });

  assert.deepEqual(shader.uniforms.selectionCenter!.value, new Vector3(1, 0, -0));
  assert.equal(shader.uniforms.hoverVisible!.value, 1);

  const hoverCenter = shader.uniforms.hoverCenter!.value;

  assert(hoverCenter instanceof Vector3);
  assert(hoverCenter.distanceTo(new Vector3(0, 1, 0)) < 1e-12);

  overlay.setSelection({ latitude: 0, longitude: 0 }, 2500);

  assert.equal(shader.uniforms.selectionRadius!.value, 2500 / 1737400);

  overlay.setHoverLocation(null);

  assert.equal(shader.uniforms.hoverVisible!.value, 0);
  assert.deepEqual(shader.uniforms.selectionCenter!.value, new Vector3(1, 0, -0));

  overlay.dispose();
  material.dispose();
});
