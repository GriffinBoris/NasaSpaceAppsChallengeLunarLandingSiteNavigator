import type { LunarFeatureInterface } from "@/types/terrain/LunarFeatureInterface";
import type { FeatureLabelInterface, ScreenBoundsInterface } from "@/types/terrain/FeatureLabelInterface";
import type { FeatureLabelView } from "./featureLabelView";

export function layoutFeatureLabels(
  features: LunarFeatureInterface[],
  view: Pick<FeatureLabelView, "width" | "height" | "project">,
  reserved: ScreenBoundsInterface[],
  measureText: (name: string) => number
): FeatureLabelInterface[] {
  const labels: FeatureLabelInterface[] = [];
  const occupied = [...reserved];
  const limit = Math.min(24, Math.max(1, Math.floor((view.width * view.height) / 30000)));
  const candidates = [...features].sort((first, second) => (second.diameterKm ?? 0) - (first.diameterKm ?? 0) || first.usgsId - second.usgsId);

  for (const feature of candidates) {
    const position = view.project(feature);

    if (!position) {
      continue;
    }

    const textWidth = Math.max(measureText(feature.name), feature.englishName ? measureText(feature.englishName) : 0);
    const width = Math.min(180, Math.ceil(textWidth) + 12);
    const halfHeight = feature.englishName ? 26 : 18;
    const bounds = {
      left: position.x - width / 2 - 10,
      right: position.x + width / 2 + 10,
      top: position.y - halfHeight,
      bottom: position.y + halfHeight,
    };

    if (bounds.left < 16 || bounds.top < 16 || bounds.right > view.width - 16 || bounds.bottom > view.height - 16) {
      continue;
    }

    const overlaps = occupied.some(
      (other) => bounds.left < other.right && bounds.right > other.left && bounds.top < other.bottom && bounds.bottom > other.top
    );

    if (overlaps) {
      continue;
    }

    labels.push({ feature, ...position, width });
    occupied.push(bounds);

    if (labels.length >= limit) {
      break;
    }
  }

  return labels;
}
