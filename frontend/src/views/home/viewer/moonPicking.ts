import { MathUtils, Raycaster, Vector3, type Group } from "three";
import type { TerrainLocationInterface } from "@/types/terrain/TerrainLocationInterface";

export function isValidLocation(location: TerrainLocationInterface): boolean {
  return (
    Number.isFinite(location.latitude) &&
    Number.isFinite(location.longitude) &&
    Math.abs(location.latitude) <= 90 &&
    Math.abs(location.longitude) <= 180
  );
}

export function terrainLocation(position: Vector3): TerrainLocationInterface {
  const direction = position.clone().normalize();

  return {
    latitude: MathUtils.radToDeg(Math.asin(MathUtils.clamp(direction.y, -1, 1))),
    longitude: MathUtils.radToDeg(Math.atan2(-direction.z, direction.x)),
  };
}

export function locationDirection(location: TerrainLocationInterface): Vector3 {
  const latitude = MathUtils.degToRad(location.latitude);
  const longitude = MathUtils.degToRad(location.longitude);

  return new Vector3(Math.cos(latitude) * Math.cos(longitude), Math.sin(latitude), -Math.cos(latitude) * Math.sin(longitude));
}

export function intersectTerrain(raycaster: Raycaster, terrain: Group, tileSize: number): Vector3 | undefined {
  const visibleMeshes = terrain.children.filter((mesh) => mesh.visible);
  const intersections = raycaster.intersectObjects(visibleMeshes, false);
  const surfaceTriangleCount = (tileSize - 1) ** 2 * 2;

  for (const intersection of intersections) {
    if (intersection.faceIndex! < surfaceTriangleCount) {
      return intersection.point;
    }
  }
}
