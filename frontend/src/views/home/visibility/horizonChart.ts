import type { HorizonInterface } from "@/types/terrain/HorizonInterface";
import type { BodyDirectionInterface } from "@/types/terrain/SiteTerrainInterface";

export const HORIZON_PLOT = { left: 58, right: 934, top: 24, bottom: 244 };

export function horizonChart(horizon: HorizonInterface | null, bodyElevations: number[][]) {
  const bounds = horizon?.bounds;
  let lowestElevation = 0;
  let highestElevation = 0;

  const elevationSeries = [bounds?.lowerElevationDegrees, bounds?.upperElevationDegrees, ...bodyElevations];

  for (const series of elevationSeries) {
    if (!series) {
      continue;
    }

    for (const elevation of series) {
      lowestElevation = Math.min(lowestElevation, elevation);
      highestElevation = Math.max(highestElevation, elevation);
    }
  }

  const minimumElevation = Math.max(-90, Math.floor((lowestElevation - 2) / 5) * 5);
  const maximumElevation = Math.min(90, Math.ceil((highestElevation + 2) / 5) * 5);
  const width = HORIZON_PLOT.right - HORIZON_PLOT.left;
  const height = HORIZON_PLOT.bottom - HORIZON_PLOT.top;
  const horizontal = (azimuth: number) => HORIZON_PLOT.left + (azimuth / 360) * width;
  const vertical = (elevation: number) => HORIZON_PLOT.bottom - ((elevation - minimumElevation) / (maximumElevation - minimumElevation)) * height;
  const segments: { start: number; end: number; lower: number; upper: number }[] = [];

  if (bounds) {
    const step = 360 / bounds.lowerElevationDegrees.length;

    for (let index = 0; index < bounds.lowerElevationDegrees.length; index++) {
      const start = (((index * step + horizon!.azimuthOffsetDegrees) % 360) + 360) % 360;
      const end = start + step;
      const lower = bounds.lowerElevationDegrees[index]!;
      const upper = bounds.upperElevationDegrees[index]!;

      segments.push({ start, end: Math.min(end, 360), lower, upper });

      if (end > 360) {
        segments.push({ start: 0, end: end - 360, lower, upper });
      }
    }

    segments.sort((first, second) => first.start - second.start);
  }

  const lowerCoordinates: string[] = [];
  const upperCoordinates: string[] = [];

  for (const segment of segments) {
    for (const azimuth of [segment.start, segment.end]) {
      lowerCoordinates.push(`${horizontal(azimuth).toFixed(2)},${vertical(segment.lower).toFixed(2)}`);
      upperCoordinates.push(`${horizontal(azimuth).toFixed(2)},${vertical(segment.upper).toFixed(2)}`);
    }
  }

  const lowerPath = lowerCoordinates.length ? `M ${lowerCoordinates.join(" L ")}` : "";
  const upperPath = upperCoordinates.length ? `M ${upperCoordinates.join(" L ")}` : "";
  const terrainPath = lowerPath ? `${lowerPath} L ${HORIZON_PLOT.right},${HORIZON_PLOT.bottom} L ${HORIZON_PLOT.left},${HORIZON_PLOT.bottom} Z` : "";
  const uncertaintyPath = lowerPath ? `${lowerPath} L ${upperCoordinates.reverse().join(" L ")} Z` : "";
  const tickStep = Math.max(5, Math.ceil((maximumElevation - minimumElevation) / 25) * 5);
  const elevationTicks = [];

  for (let elevation = Math.ceil(minimumElevation / tickStep) * tickStep; elevation <= maximumElevation; elevation += tickStep) {
    elevationTicks.push({ elevation, y: vertical(elevation) });
  }

  const compassTicks = [
    { azimuth: 0, label: "N" },
    { azimuth: 90, label: "E" },
    { azimuth: 180, label: "S" },
    { azimuth: 270, label: "W" },
    { azimuth: 360, label: "N" },
  ].map((tick) => ({ ...tick, x: horizontal(tick.azimuth) }));

  function position(direction: BodyDirectionInterface) {
    const azimuth = ((direction.azimuthDegrees % 360) + 360) % 360;

    return { x: horizontal(azimuth), y: vertical(direction.elevationDegrees) };
  }

  return {
    minimumElevation,
    maximumElevation,
    elevationTicks,
    compassTicks,
    referenceY: vertical(0),
    position,
    terrainPath,
    uncertaintyPath,
    upperPath,
  };
}
