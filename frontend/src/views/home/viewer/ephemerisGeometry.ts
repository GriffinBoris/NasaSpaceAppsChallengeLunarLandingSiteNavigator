import { Vector3 } from "three";
import type { CelestialBodyInterface } from "@/types/ephemeris/EphemerisInterface";

export function moonFixedPosition(positionKm: [number, number, number], referenceRadiusKm: number): Vector3 {
  return new Vector3(positionKm[0], positionKm[2], -positionKm[1]).divideScalar(referenceRadiusKm);
}

export function skyBodyPlacement(body: CelestialBodyInterface, observerPosition: Vector3, referenceRadiusKm: number) {
  const relativePosition = moonFixedPosition(body.positionKm, referenceRadiusKm).sub(observerPosition);
  const distance = relativePosition.length();
  const skyDistance = 1000;

  return {
    position: relativePosition.multiplyScalar(skyDistance / distance),
    radius: (skyDistance * body.radiusKm) / (distance * referenceRadiusKm),
  };
}
