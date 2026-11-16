import { Color, DataTexture, LinearFilter, MathUtils, RGBAFormat, Uniform, Vector3, type MeshStandardMaterial } from "three";
import { patchFraction, patchMetric } from "../visibility/visibilityView.ts";
import type { VisibilityMetric, VisibilityPatchInterface } from "@/types/terrain/VisibilityInterface";
import type { IlluminationPatchInterface } from "@/types/terrain/IlluminationPatchInterface";
import type { TerrainLocationInterface } from "@/types/terrain/TerrainLocationInterface";
import { isValidLocation } from "./moonPicking.ts";
import type { TerrainDisplayMode } from "@/types/terrain/TerrainDisplayMode";
import { locationDirection } from "./moonPicking.ts";

const NONE_COLOR = "#3b4559";

export const SUNLIGHT_COLORS = { sunlight: "#f2c14e", shadow: NONE_COLOR, partial: "#b8863b" };

export const NOT_CALCULATED_COLOR = "repeating-linear-gradient(135deg, rgb(149 161 180 / 0.45) 0 2px, transparent 2px 4px)";

export const OUTSIDE_PLAN_COLOR = "rgb(149 161 180 / 0.06)";
export const SUNLIGHT_OVERLAY_OPACITY = 0.7;

export const SELECTION_COLOR = "#e9edf3";

export function belowMinimumColor(color: string): string {
  return `color-mix(in srgb, ${color} 40%, var(--background))`;
}
export const EARTH_VISIBILITY_COLORS = { blocked: NONE_COLOR, visible: "#62c4ee" };
export const VISIBLE_COLORS = { sunlight: SUNLIGHT_COLORS.sunlight, earth: EARTH_VISIBILITY_COLORS.visible, joint: "#a3d977" };

const visibleColors = {
  sunlight: new Color(VISIBLE_COLORS.sunlight),
  earth: new Color(VISIBLE_COLORS.earth),
  joint: new Color(VISIBLE_COLORS.joint),
};
const shadowColor = new Color(SUNLIGHT_COLORS.shadow);
const partialColor = new Color(SUNLIGHT_COLORS.partial);
const earthBlockedColor = new Color(EARTH_VISIBILITY_COLORS.blocked);
const earthPartialColor = earthBlockedColor.clone().lerp(visibleColors.earth, 0.5);

export function visibilityGradient(metric: VisibilityMetric): string {
  return `linear-gradient(to right, ${[0, 0.25, 0.5, 0.75, 1].map((fraction) => visibilityFractionColor(fraction, metric)).join(", ")})`;
}

export function visibilityFractionColor(visibleFraction: number, metric: VisibilityMetric = "sunlight"): string {
  if (metric === "earth") {
    return earthBlockedColor.clone().lerp(visibleColors.earth, visibleFraction).getStyle();
  }

  if (visibleFraction <= 0.5) {
    return shadowColor
      .clone()
      .lerp(partialColor, visibleFraction * 2)
      .getStyle();
  }

  return partialColor
    .clone()
    .lerp(visibleColors[metric], (visibleFraction - 0.5) * 2)
    .getStyle();
}

const DISPLAY_MODES = { terrain: 0, elevation: 0, illumination: 1, sunlight: 2, shadow: 3 };

const FRAGMENT_PARAMETERS = `
uniform sampler2D sunlightTexture;
uniform int sunlightMode;
uniform int sunlightShadows;
uniform int inspectionLighting;
uniform float sunlightRadius;
uniform float selectionRadius;
uniform vec3 selectionCenter;
uniform vec3 hoverCenter;
uniform int hoverVisible;
uniform vec3 hoverColor;
uniform float sunlightGridSize;
uniform vec3 sunlightCenter;
uniform vec3 sunlightEast;
uniform vec3 sunlightNorth;
uniform vec3 sunlightColor;
uniform vec3 shadowColor;
uniform vec3 partialColor;
uniform vec3 selectionColor;
varying vec3 moonSurfacePosition;

float circleOutline(vec3 direction, vec3 center) {
  if (selectionRadius < 0.0) {
    return 0.0;
  }

  float angle = atan(length(cross(direction, center)), dot(direction, center));
  float lineWidth = max(fwidth(angle), 0.0000001);

  return 1.0 - smoothstep(lineWidth, lineWidth * 2.0, abs(angle - max(selectionRadius, lineWidth * 4.0)));
}

vec3 sampleSunlightVisibility(vec3 position) {
  if (sunlightMode == 0) {
    return vec3(0.0);
  }

  vec3 direction = normalize(position);
  float centerCosine = clamp(dot(direction, sunlightCenter), -1.0, 1.0);
  vec3 tangent = direction - sunlightCenter * centerCosine;
  float tangentLength = length(tangent);
  vec2 offset = vec2(0.0);

  if (tangentLength > 0.0000001) {
    float angle = atan(tangentLength, centerCosine);
    offset = angle / tangentLength * vec2(dot(tangent, sunlightEast), dot(tangent, sunlightNorth));
  }

  if (centerCosine <= 0.0 || length(offset) > sunlightRadius) {
    return vec3(0.0);
  }

  vec2 coordinates = vec2(0.5) + vec2(offset.x, -offset.y) / (2.0 * sunlightRadius);

  if (coordinates.x < 0.0 || coordinates.x > 1.0 || coordinates.y < 0.0 || coordinates.y > 1.0) {
    return vec3(0.0);
  }

  vec2 textureCoordinates = (coordinates * (sunlightGridSize - 1.0) + 0.5) / sunlightGridSize;
  vec4 sampleValue = texture2D(sunlightTexture, textureCoordinates);

  if (sampleValue.a == 0.0) {
    return vec3(0.0);
  }

  float visibleFraction = clamp(sampleValue.r / sampleValue.a, 0.0, 1.0);
  float visibleSunFraction = sampleValue.b > 0.0 ? clamp(sampleValue.g / sampleValue.b, 0.0, 1.0) : 1.0;

  return vec3(visibleFraction, visibleSunFraction, 1.0);
}

vec4 sunlightOverlayColor(vec3 visibility) {
  if (visibility.z == 0.0) {
    return vec4(0.0);
  }

  float visibleFraction = visibility.x;
  vec3 color;
  float opacity = ${SUNLIGHT_OVERLAY_OPACITY.toFixed(2)};

  if (sunlightMode == 2) {
    color = sunlightColor;
    opacity *= visibleFraction;
  } else if (sunlightMode == 3) {
    color = shadowColor;
    opacity *= 1.0 - visibleFraction;
  } else if (visibleFraction <= 0.5) {
    color = mix(shadowColor, partialColor, visibleFraction * 2.0);
  } else {
    color = mix(partialColor, sunlightColor, (visibleFraction - 0.5) * 2.0);
  }

  return vec4(color, opacity);
}
`;

export function createSunlightTexture(patch: VisibilityPatchInterface, sunlight: IlluminationPatchInterface | null = null): DataTexture {
  const pixels = new Uint8Array(patch.points.length * 4);

  for (let index = 0; index < patch.points.length; index++) {
    const point = patch.points[index];

    if (!point) {
      continue;
    }

    pixels[index * 4] = Math.round(patchFraction(point) * 255);
    pixels[index * 4 + 3] = 255;

    const sunlightPoint = "visibleSunFraction" in point ? point : sunlight?.points[index];

    if (sunlightPoint) {
      pixels[index * 4 + 1] = Math.round(sunlightPoint.visibleSunFraction * 255);
      pixels[index * 4 + 2] = 255;
    }
  }

  const texture = new DataTexture(pixels, patch.gridSize, patch.gridSize, RGBAFormat);

  texture.minFilter = LinearFilter;
  texture.magFilter = LinearFilter;
  texture.needsUpdate = true;

  return texture;
}

export class SunlightOverlay {
  private readonly referenceRadius: number;
  private readonly uniforms = {
    sunlightTexture: new Uniform<DataTexture | null>(null),
    sunlightMode: new Uniform(0),
    sunlightShadows: new Uniform(0),
    inspectionLighting: new Uniform(0),
    sunlightRadius: new Uniform(1),
    selectionRadius: new Uniform(-1),
    selectionCenter: new Uniform(new Vector3(1, 0, 0)),
    hoverCenter: new Uniform(new Vector3(1, 0, 0)),
    hoverVisible: new Uniform(0),
    hoverColor: new Uniform(new Color(0xe9edf3)),
    sunlightGridSize: new Uniform(1),
    sunlightCenter: new Uniform(new Vector3()),
    sunlightEast: new Uniform(new Vector3()),
    sunlightNorth: new Uniform(new Vector3()),
    sunlightColor: new Uniform(new Color(SUNLIGHT_COLORS.sunlight)),
    shadowColor: new Uniform(new Color(SUNLIGHT_COLORS.shadow)),
    partialColor: new Uniform(new Color(SUNLIGHT_COLORS.partial)),
    selectionColor: new Uniform(new Color(SELECTION_COLOR)),
  };
  private mode: TerrainDisplayMode = "terrain";

  constructor(material: MeshStandardMaterial, referenceRadius: number) {
    this.referenceRadius = referenceRadius;

    material.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, this.uniforms);

      shader.vertexShader = `varying vec3 moonSurfacePosition;\n${shader.vertexShader}`;
      shader.vertexShader = shader.vertexShader.replace("#include <begin_vertex>", "#include <begin_vertex>\nmoonSurfacePosition = position;");
      shader.fragmentShader = FRAGMENT_PARAMETERS + shader.fragmentShader;
      shader.fragmentShader = shader.fragmentShader.replace(
        "#include <lights_fragment_end>",
        `#include <lights_fragment_end>
         vec3 sunlightVisibility = sampleSunlightVisibility(moonSurfacePosition);

         if (sunlightShadows == 1 && inspectionLighting == 0 && sunlightVisibility.z > 0.0) {
           reflectedLight.directDiffuse *= sunlightVisibility.y;
           reflectedLight.directSpecular *= sunlightVisibility.y;
         }`
      );
      shader.fragmentShader = shader.fragmentShader.replace(
        "#include <opaque_fragment>",
        `vec4 sunlightOverlay = sunlightOverlayColor(sunlightVisibility);
         outgoingLight = mix(outgoingLight, sunlightOverlay.rgb, sunlightOverlay.a);
         vec3 selectionDirection = normalize(moonSurfacePosition);
         float selectionOutline = circleOutline(selectionDirection, selectionCenter);
         float hoverOutline = hoverVisible == 1 ? circleOutline(selectionDirection, hoverCenter) * 0.85 : 0.0;
         outgoingLight = mix(outgoingLight, hoverColor, hoverOutline);
         outgoingLight = mix(outgoingLight, selectionColor, selectionOutline);
         #include <opaque_fragment>`
      );
    };
    material.customProgramCacheKey = () => "lola-sunlight-overlay";
    material.needsUpdate = true;
  }

  setPatch(patch: VisibilityPatchInterface | null, sunlight: IlluminationPatchInterface | null = null) {
    this.uniforms.sunlightTexture.value?.dispose();
    this.uniforms.sunlightTexture.value = patch ? createSunlightTexture(patch, sunlight) : null;
    this.uniforms.sunlightShadows.value = patch && (patchMetric(patch) === "sunlight" || sunlight) ? 1 : 0;

    if (patch) {
      const metric = patchMetric(patch);

      this.uniforms.sunlightColor.value.copy(visibleColors[metric]);
      this.uniforms.shadowColor.value.copy(metric === "earth" ? earthBlockedColor : shadowColor);
      this.uniforms.partialColor.value.copy(metric === "earth" ? earthPartialColor : partialColor);

      const center = locationDirection(patch.center);
      const longitude = MathUtils.degToRad(patch.center.longitude);
      const east = new Vector3(-Math.sin(longitude), 0, -Math.cos(longitude));

      this.uniforms.sunlightCenter.value.copy(center);
      this.uniforms.sunlightEast.value.copy(east);
      this.uniforms.sunlightNorth.value.copy(center).cross(east);
      this.uniforms.sunlightRadius.value = patch.radiusMeters / this.referenceRadius;
      this.uniforms.sunlightGridSize.value = patch.gridSize;
    }

    this.setDisplayMode(this.mode);
  }

  setSelection(location: TerrainLocationInterface, radiusMeters: number) {
    const isValid = isValidLocation(location) && Number.isFinite(radiusMeters) && radiusMeters >= 0;

    this.uniforms.selectionRadius.value = isValid ? radiusMeters / this.referenceRadius : -1;

    if (isValid) {
      this.uniforms.selectionCenter.value.copy(locationDirection(location));
    }
  }

  setHoverLocation(location: TerrainLocationInterface | null) {
    this.uniforms.hoverVisible.value = location ? 1 : 0;

    if (location) {
      this.uniforms.hoverCenter.value.copy(locationDirection(location));
    }
  }

  setDisplayMode(mode: TerrainDisplayMode) {
    this.mode = mode;
    this.uniforms.sunlightMode.value = this.uniforms.sunlightTexture.value ? DISPLAY_MODES[mode] : 0;
  }

  setFullIllumination(enabled: boolean) {
    this.uniforms.inspectionLighting.value = enabled ? 1 : 0;
  }

  dispose() {
    this.uniforms.sunlightTexture.value?.dispose();
  }
}
