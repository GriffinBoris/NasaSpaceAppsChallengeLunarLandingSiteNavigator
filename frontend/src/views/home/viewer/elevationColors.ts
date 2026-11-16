import { Color } from "three";

const palette = ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"];
const colors = palette.map((color) => new Color(color));

export const ELEVATION_SCALE = {
  minimum: -10000,
  maximum: 12000,
  gradient: `linear-gradient(to right, ${palette.join(", ")})`,
};

export function elevationColor(height: number): Color {
  const heightRange = ELEVATION_SCALE.maximum - ELEVATION_SCALE.minimum;
  const normalizedHeight = Math.max(0, Math.min(1, (height - ELEVATION_SCALE.minimum) / heightRange));
  const palettePosition = normalizedHeight * (colors.length - 1);
  const lowerIndex = Math.min(Math.floor(palettePosition), colors.length - 2);
  const blend = palettePosition - lowerIndex;

  return colors[lowerIndex]!.clone().lerp(colors[lowerIndex + 1]!, blend);
}
