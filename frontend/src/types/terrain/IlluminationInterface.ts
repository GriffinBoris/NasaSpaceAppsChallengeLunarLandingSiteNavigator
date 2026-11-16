export interface IlluminationInterface {
  datasetId: number;
  timestamp: string;
  latitude: number;
  longitude: number;
  frame: string;
  elevationMeters: number;
  analysisLevel: number;
  sunElevationDegrees: number;
  sunAzimuthDegrees: number;
  sunAngularRadiusDegrees: number;
  visibleSunFraction: number;
  diskSampleCount: number;
  samplingConverged: boolean;
  fractionTolerance: number;
}
