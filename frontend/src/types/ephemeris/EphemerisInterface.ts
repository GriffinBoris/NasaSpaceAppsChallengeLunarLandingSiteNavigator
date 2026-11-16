export interface CelestialBodyInterface {
  positionKm: [number, number, number];
  radiusKm: number;
}

export interface EphemerisInterface {
  timestamp: string;
  frame: string;
  sun: CelestialBodyInterface;
  earth: CelestialBodyInterface;
}
