import type { LunarFeatureInterface } from "./LunarFeatureInterface";

export interface FeatureLabelQueryInterface {
  latitude: number;
  longitude: number;
  radiusDegrees: number;
  minimumDiameterKm: number;
}

export interface ScreenBoundsInterface {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export interface FeatureLabelInterface {
  feature: LunarFeatureInterface;
  x: number;
  y: number;
  width: number;
}
