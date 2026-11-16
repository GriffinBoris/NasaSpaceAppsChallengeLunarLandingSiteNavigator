export interface HorizonBoundsInterface {
  lowerElevationDegrees: number[];
  upperElevationDegrees: number[];
}

export interface HorizonInterface {
  azimuthOffsetDegrees: number;
  bounds: HorizonBoundsInterface | null;
}
