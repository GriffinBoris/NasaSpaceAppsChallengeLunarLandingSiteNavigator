export interface EarthVisibilityInterface {
  datasetId: number;
  timestamp: string;
  latitude: number;
  longitude: number;
  frame: string;
  elevationMeters: number;
  analysisLevel: number;
  earthElevationDegrees: number;
  earthAzimuthDegrees: number;
  earthAngularRadiusDegrees: number;
  visibleEarthFraction: number;
  earthCenterVisible: boolean;
  diskSampleCount: number;
  samplingConverged: boolean;
  fractionTolerance: number;
}

export interface EarthVisibilityPatchInterface {
  center: EarthVisibilityInterface;
  gridSize: number;
  radiusMeters: number;
  spacingMeters: number;
  points: ({ visibleEarthFraction: number; earthCenterVisible: boolean; samplingConverged: boolean } | null)[];
}
