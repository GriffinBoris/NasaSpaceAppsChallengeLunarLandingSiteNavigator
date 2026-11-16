import type { EarthVisibilityPatchInterface } from "./EarthVisibilityInterface";
import type { IlluminationPatchInterface } from "./IlluminationPatchInterface";

export type VisibilityMetric = "sunlight" | "earth" | "joint";

export interface JointVisibilityPatchInterface {
  center: IlluminationPatchInterface["center"];
  gridSize: number;
  radiusMeters: number;
  spacingMeters: number;
  points: ({ visibleJointFraction: number } | null)[];
}

export type VisibilityPatchInterface = IlluminationPatchInterface | EarthVisibilityPatchInterface | JointVisibilityPatchInterface;
