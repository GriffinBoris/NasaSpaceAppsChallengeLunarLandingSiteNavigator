import { MathUtils, PerspectiveCamera, Vector3 } from "three";
import type { LunarFeatureInterface } from "@/types/terrain/LunarFeatureInterface";
import type { FeatureLabelQueryInterface } from "@/types/terrain/FeatureLabelInterface";
import { locationDirection, terrainLocation } from "./moonPicking.ts";

const MINIMUM_FEATURE_PIXELS = 48;

export class FeatureLabelView {
  readonly query: FeatureLabelQueryInterface;
  readonly width: number;
  readonly height: number;
  private readonly camera: PerspectiveCamera;
  private readonly cameraPosition: Vector3;
  private readonly screenScale: number;
  private readonly referenceRadiusKm: number;

  constructor(camera: PerspectiveCamera, width: number, height: number, referenceRadiusKm: number) {
    camera.updateMatrixWorld();

    this.width = width;
    this.height = height;
    this.referenceRadiusKm = referenceRadiusKm;
    this.camera = camera.clone();
    this.cameraPosition = camera.position.clone();

    const distance = this.cameraPosition.length();
    const halfFieldOfView = MathUtils.degToRad(camera.fov / 2);
    const cornerAngle = Math.atan(Math.tan(halfFieldOfView) * Math.hypot(1, camera.aspect));
    let radius = Math.acos(1 / distance);

    if (Math.sin(cornerAngle) * distance < 1) {
      const rayDistance = distance * Math.cos(cornerAngle) - Math.sqrt(1 - (distance * Math.sin(cornerAngle)) ** 2);

      radius = Math.atan2(rayDistance * Math.sin(cornerAngle), distance - rayDistance * Math.cos(cornerAngle));
    }

    this.screenScale = height / (2 * Math.tan(halfFieldOfView));
    this.query = {
      ...terrainLocation(this.cameraPosition),
      radiusDegrees: Math.min(90, MathUtils.radToDeg(radius) * 1.25),
      minimumDiameterKm: (MINIMUM_FEATURE_PIXELS * (distance - 1) * referenceRadiusKm) / this.screenScale,
    };
  }

  project(feature: LunarFeatureInterface): { x: number; y: number } | null {
    if (!feature.diameterKm) {
      return null;
    }

    const surface = locationDirection(feature);
    const toCamera = this.cameraPosition.clone().sub(surface);
    const distance = toCamera.length();

    if (toCamera.divideScalar(distance).dot(surface) < 0.15) {
      return null;
    }

    const diameterPixels = (feature.diameterKm * this.screenScale) / (this.referenceRadiusKm * distance);

    if (diameterPixels < MINIMUM_FEATURE_PIXELS) {
      return null;
    }

    const projected = surface.project(this.camera);

    if (Math.abs(projected.x) > 1 || Math.abs(projected.y) > 1 || projected.z < -1 || projected.z > 1) {
      return null;
    }

    return { x: ((projected.x + 1) * this.width) / 2, y: ((1 - projected.y) * this.height) / 2 };
  }
}
