import { Color } from "three";
import type { VisibilityMetric } from "@/types/terrain/VisibilityInterface";
import type { SiteTerrainInterface, BodyDirectionInterface, VisibilityGridInterface } from "@/types/terrain/SiteTerrainInterface";
import { AMBIENT_LIGHT_INTENSITY, SUN_LIGHT_INTENSITY, TERRAIN_COLOR } from "../viewer/moonLighting.ts";
import { EARTH_VISIBILITY_COLORS, SUNLIGHT_COLORS, VISIBLE_COLORS, SUNLIGHT_OVERLAY_OPACITY } from "../viewer/sunlightOverlay.ts";

type Rgb = [number, number, number];

const TERRAIN_ALBEDO = new Color(TERRAIN_COLOR).r;
const SHADOW_COLOR = linearColor(SUNLIGHT_COLORS.shadow);
const PARTIAL_COLOR = linearColor(SUNLIGHT_COLORS.partial);
const EARTH_BLOCKED_COLOR = linearColor(EARTH_VISIBILITY_COLORS.blocked);
const VISIBLE_COLOR = {
  sunlight: linearColor(VISIBLE_COLORS.sunlight),
  earth: linearColor(VISIBLE_COLORS.earth),
  joint: linearColor(VISIBLE_COLORS.joint),
};

const EXPOSURE = 12;
const RELIEF_LIGHT = lightVector({ azimuthDegrees: 315, elevationDegrees: 45 });
const RELIEF_LIGHT_INTENSITY = 0.15;

const AMBIENT_LIGHT = (TERRAIN_ALBEDO * AMBIENT_LIGHT_INTENSITY) / Math.PI;

export function sampleGrid(grid: VisibilityGridInterface, u: number, v: number): number | null {
  const last = grid.gridSize - 1;
  const x = u * last;
  const y = v * last;
  const left = Math.floor(x);
  const top = Math.floor(y);
  const right = Math.min(left + 1, last);
  const bottom = Math.min(top + 1, last);
  const horizontal = x - left;
  const vertical = y - top;
  const corners = [
    [left, top, (1 - horizontal) * (1 - vertical)],
    [right, top, horizontal * (1 - vertical)],
    [left, bottom, (1 - horizontal) * vertical],
    [right, bottom, horizontal * vertical],
  ] as const;
  let total = 0;
  let weight = 0;

  for (const [column, row, cornerWeight] of corners) {
    const value = grid.fractions[row * grid.gridSize + column];

    if (value === null || value === undefined || cornerWeight === 0) {
      continue;
    }

    total += value * cornerWeight;
    weight += cornerWeight;
  }

  return weight ? total / weight : null;
}

export function terrainNormals(terrain: SiteTerrainInterface): Float32Array {
  const size = terrain.gridSize;
  const last = size - 1;
  const center = last / 2;
  const normals = new Float32Array(size * size * 3);
  const height = (row: number, column: number) => terrain.heightsMeters[row * size + column]!;

  for (let row = 0; row < size; row++) {
    for (let column = 0; column < size; column++) {
      const west = Math.max(column - 1, 0);
      const east = Math.min(column + 1, last);
      const north = Math.max(row - 1, 0);
      const south = Math.min(row + 1, last);
      const eastSlope = (height(row, east) - height(row, west)) / ((east - west) * terrain.spacingMeters);
      const northSlope = (height(north, column) - height(south, column)) / ((south - north) * terrain.spacingMeters);

      const eastTilt = ((column - center) * terrain.spacingMeters) / terrain.referenceRadiusMeters;
      const northTilt = ((center - row) * terrain.spacingMeters) / terrain.referenceRadiusMeters;
      const normal: Rgb = [eastTilt - eastSlope, northTilt - northSlope, 1];
      const length = Math.hypot(...normal);
      const offset = (row * size + column) * 3;

      normals[offset] = normal[0] / length;
      normals[offset + 1] = normal[1] / length;
      normals[offset + 2] = normal[2] / length;
    }
  }

  return normals;
}

export function terrainPixels(
  terrain: SiteTerrainInterface,
  normals: Float32Array,
  direction: BodyDirectionInterface,
  visibility: VisibilityGridInterface | null,
  metric: VisibilityMetric = "sunlight",
  sunlightVisibility: VisibilityGridInterface | null = metric === "sunlight" ? visibility : null
): Uint8ClampedArray<ArrayBuffer> {
  const size = terrain.gridSize;
  const center = (size - 1) / 2;
  const light = lightVector(direction);
  const pixels = new Uint8ClampedArray(size * size * 4);

  for (let row = 0; row < size; row++) {
    for (let column = 0; column < size; column++) {
      if (Math.hypot(column - center, row - center) > center) {
        continue;
      }

      const index = row * size + column;
      const facing = Math.max(0, normals[index * 3]! * light[0] + normals[index * 3 + 1]! * light[1] + normals[index * 3 + 2]! * light[2]);
      const fraction = visibility ? sampleGrid(visibility, column / (size - 1), row / (size - 1)) : null;
      const sunlight = sunlightVisibility ? (sampleGrid(sunlightVisibility, column / (size - 1), row / (size - 1)) ?? 1) : 1;
      const relief =
        fraction === null
          ? 0
          : Math.max(
              0,
              normals[index * 3]! * RELIEF_LIGHT[0] + normals[index * 3 + 1]! * RELIEF_LIGHT[1] + normals[index * 3 + 2]! * RELIEF_LIGHT[2]
            );
      const lighting = SUN_LIGHT_INTENSITY * facing * sunlight + RELIEF_LIGHT_INTENSITY * relief;
      const lit = exposed((TERRAIN_ALBEDO * lighting) / Math.PI) + AMBIENT_LIGHT;
      let color: Rgb = [lit, lit, lit];

      if (fraction !== null) {
        color = mix(color, overlayColor(fraction, metric), SUNLIGHT_OVERLAY_OPACITY);
      }

      pixels[index * 4] = encodeSrgb(color[0]);
      pixels[index * 4 + 1] = encodeSrgb(color[1]);
      pixels[index * 4 + 2] = encodeSrgb(color[2]);
      pixels[index * 4 + 3] = 255;
    }
  }

  return pixels;
}

function exposed(value: number) {
  const scaled = value * EXPOSURE;

  return scaled / (1 + scaled);
}

function overlayColor(fraction: number, metric: VisibilityMetric): Rgb {
  if (metric === "earth") {
    return mix(EARTH_BLOCKED_COLOR, VISIBLE_COLOR.earth, fraction);
  }

  return fraction <= 0.5 ? mix(SHADOW_COLOR, PARTIAL_COLOR, fraction * 2) : mix(PARTIAL_COLOR, VISIBLE_COLOR[metric], (fraction - 0.5) * 2);
}

function mix(first: Rgb, second: Rgb, amount: number): Rgb {
  return [first[0] + (second[0] - first[0]) * amount, first[1] + (second[1] - first[1]) * amount, first[2] + (second[2] - first[2]) * amount];
}

function lightVector(direction: BodyDirectionInterface): Rgb {
  const azimuth = (direction.azimuthDegrees * Math.PI) / 180;
  const elevation = (direction.elevationDegrees * Math.PI) / 180;

  return [Math.sin(azimuth) * Math.cos(elevation), Math.cos(azimuth) * Math.cos(elevation), Math.sin(elevation)];
}

function linearColor(hex: string): Rgb {
  const color = new Color(hex);

  return [color.r, color.g, color.b];
}

function encodeSrgb(value: number) {
  const clamped = Math.min(Math.max(value, 0), 1);
  const encoded = clamped <= 0.0031308 ? clamped * 12.92 : 1.055 * clamped ** (1 / 2.4) - 0.055;

  return Math.round(encoded * 255);
}
