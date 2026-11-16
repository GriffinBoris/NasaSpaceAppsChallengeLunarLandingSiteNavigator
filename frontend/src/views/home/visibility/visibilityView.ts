import type { SunlightFrameDetailInterface, SunlightFrameInterface } from "@/types/terrain/SunlightFrameInterface";
import type { JointVisibilityPatchInterface, VisibilityMetric, VisibilityPatchInterface } from "@/types/terrain/VisibilityInterface";
import type { IlluminationPatchInterface } from "@/types/terrain/IlluminationPatchInterface";
import type { EarthVisibilityPatchInterface } from "@/types/terrain/EarthVisibilityInterface";
import type { VisibilityGridInterface } from "@/types/terrain/SiteTerrainInterface";

const METRIC_LABELS: Record<VisibilityMetric, string> = { sunlight: "Sunlight", earth: "Earth visibility", joint: "Sun and Earth" };

export function frameFraction(frame: SunlightFrameInterface, metric: VisibilityMetric): number | null {
  if (metric === "earth") {
    return frame.visibleEarthFraction;
  }
  if (metric === "joint") {
    return frame.jointVisibleShare;
  }

  return frame.visibleSunFraction;
}

export function frameResultKey(frame: SunlightFrameInterface): string {
  return `${frame.id}:${frame.resultRevision}`;
}

export function patchFraction(point: NonNullable<VisibilityPatchInterface["points"][number]>): number {
  if ("visibleEarthFraction" in point) {
    return point.visibleEarthFraction;
  }
  if ("visibleJointFraction" in point) {
    return point.visibleJointFraction;
  }

  return point.visibleSunFraction;
}

export function frameVisibilityGrid(
  frame: SunlightFrameInterface | null,
  detail: SunlightFrameDetailInterface | null,
  metric: VisibilityMetric
): VisibilityGridInterface | null {
  if (!frame) {
    return null;
  }

  const patch = detail && frameResultKey(detail) === frameResultKey(frame) ? framePatch(detail, metric) : null;

  if (patch) {
    return { gridSize: patch.gridSize, fractions: patch.points.map((point) => (point === null ? null : patchFraction(point))) };
  }

  if (metric === "joint") {
    return null;
  }

  return metric === "earth" ? frame.earthThumbnail : frame.thumbnail;
}

export function framePatch(frame: SunlightFrameDetailInterface, metric: VisibilityMetric): VisibilityPatchInterface | null {
  if (metric === "earth") {
    return frame.earthResult?.patch ?? null;
  }
  if (metric === "sunlight") {
    return frame.result?.patch ?? null;
  }

  const sunlight = frame.result?.patch;
  const earth = frame.earthResult?.patch;

  if (!sunlight || !earth || frame.jointVisibleShare === null) {
    return null;
  }

  return jointPatch(sunlight, earth);
}

export function jointPatch(sunlight: IlluminationPatchInterface, earth: EarthVisibilityPatchInterface): JointVisibilityPatchInterface {
  const points: JointVisibilityPatchInterface["points"] = [];

  for (const [index, sunlightPoint] of sunlight.points.entries()) {
    if (sunlightPoint === null) {
      points.push(null);
      continue;
    }

    const isVisible = sunlightPoint.visibleSunFraction > 0.005 && earth.points[index]!.earthCenterVisible;

    points.push({ visibleJointFraction: isVisible ? 1 : 0 });
  }

  return {
    center: sunlight.center,
    gridSize: sunlight.gridSize,
    radiusMeters: sunlight.radiusMeters,
    spacingMeters: sunlight.spacingMeters,
    points,
  };
}

export function metricLabel(metric: VisibilityMetric) {
  return METRIC_LABELS[metric];
}

export function patchMetric(patch: VisibilityPatchInterface): VisibilityMetric {
  if ("earthElevationDegrees" in patch.center) {
    return "earth";
  }

  const firstPoint = patch.points.find((point) => point !== null)!;

  return "visibleJointFraction" in firstPoint ? "joint" : "sunlight";
}
