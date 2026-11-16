export interface SiteTerrainInterface {
  selectionId: number;
  radiusMeters: number;
  gridSize: number;
  spacingMeters: number;
  referenceRadiusMeters: number;
  heightsMeters: number[];
}

export interface BodyDirectionsInterface {
  elevationDegrees: number[];
  azimuthDegrees: number[];
}

export interface SiteDirectionsInterface {
  selectionId: number;
  sun: BodyDirectionsInterface;
  earth: BodyDirectionsInterface;
}

export interface BodyDirectionInterface {
  azimuthDegrees: number;
  elevationDegrees: number;
}

export interface VisibilityGridInterface {
  gridSize: number;
  fractions: (number | null)[];
}
