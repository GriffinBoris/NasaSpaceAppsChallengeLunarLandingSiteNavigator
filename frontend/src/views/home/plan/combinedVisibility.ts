import type {
  BestCombinedSampleInterface,
  CombinedGridInterface,
  SiteCombinedVisibilityInterface,
} from "@/types/terrain/SiteCombinedVisibilityInterface";
import type { VisibilityGridInterface } from "@/types/terrain/SiteTerrainInterface";

export function mergeCombinedVisibility(
  currentVisibility: SiteCombinedVisibilityInterface | null,
  changedVisibility: SiteCombinedVisibilityInterface
): SiteCombinedVisibilityInterface {
  if (!currentVisibility || changedVisibility.reset) {
    return changedVisibility;
  }

  const previewsByFrameId = new Map<number, SiteCombinedVisibilityInterface["previews"][number]>();

  for (const preview of currentVisibility.previews) {
    previewsByFrameId.set(preview.frameId, preview);
  }

  for (const preview of changedVisibility.previews) {
    previewsByFrameId.set(preview.frameId, preview);
  }

  return { ...changedVisibility, previews: [...previewsByFrameId.values()] };
}

export function combinedPlanGrid(combinedVisibility: SiteCombinedVisibilityInterface): VisibilityGridInterface | null {
  if (!combinedVisibility.grid || combinedVisibility.checkedSeconds === 0) {
    return null;
  }

  const visibleFractions = [];

  for (const sample of combinedVisibility.grid.samples) {
    if (sample === null) {
      visibleFractions.push(null);
      continue;
    }

    visibleFractions.push(sample.visibleSeconds / combinedVisibility.checkedSeconds);
  }

  return { gridSize: combinedVisibility.grid.gridSize, fractions: visibleFractions };
}

export function bestCombinedSample(grid: VisibilityGridInterface, geometry: CombinedGridInterface): BestCombinedSampleInterface | null {
  let best: BestCombinedSampleInterface | null = null;
  let nearestDistance = Infinity;
  let matchingSamples = 0;
  const lastGridIndex = grid.gridSize - 1;
  const sampleStride = (geometry.gridSize - 1) / lastGridIndex;

  for (let index = 0; index < grid.fractions.length; index++) {
    const fraction = grid.fractions[index];

    if (fraction === null || fraction === undefined || fraction <= 0) {
      continue;
    }

    if (best && fraction < best.fraction) {
      continue;
    }

    const column = index % grid.gridSize;
    const row = Math.floor(index / grid.gridSize);
    const sample = geometry.samples[row * sampleStride * geometry.gridSize + column * sampleStride]!;
    const distance = Math.hypot(column - lastGridIndex / 2, row - lastGridIndex / 2);

    if (!best || fraction > best.fraction) {
      matchingSamples = 0;
      nearestDistance = Infinity;
    }

    matchingSamples += 1;

    if (distance >= nearestDistance) {
      continue;
    }

    nearestDistance = distance;
    best = {
      latitude: sample.latitude,
      longitude: sample.longitude,
      x: (column / lastGridIndex) * 100,
      y: (row / lastGridIndex) * 100,
      fraction,
      matchingSamples,
    };
  }

  if (best) {
    best.matchingSamples = matchingSamples;
  }

  return best;
}
