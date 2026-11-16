import { Frustum, Matrix4, PerspectiveCamera, Sphere, Vector3 } from "three";

export class TerrainView {
  private readonly frustum: Frustum;
  private readonly cameraPosition: Vector3;
  private readonly cameraDirection: Vector3;
  private readonly horizonAngle: number;
  private readonly screenScale: number;

  constructor(camera: PerspectiveCamera, viewportHeight: number) {
    camera.updateMatrixWorld();

    const projectionMatrix = new Matrix4().multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    const fieldOfView = Math.tan((camera.fov * Math.PI) / 360);

    this.frustum = new Frustum().setFromProjectionMatrix(projectionMatrix);
    this.cameraPosition = camera.position.clone();
    this.cameraDirection = camera.position.clone().normalize();
    this.horizonAngle = Math.acos(1 / camera.position.length());
    this.screenScale = viewportHeight / fieldOfView;
  }

  isVisible(boundingSphere: Sphere, center: Vector3, angularRadius: number): boolean {
    const angleToTile = this.cameraDirection.angleTo(center);
    const aboveHorizon = angleToTile < this.horizonAngle + angularRadius + 0.03;

    return aboveHorizon && this.frustum.intersectsSphere(boundingSphere);
  }

  needsDetail(boundingSphere: Sphere): boolean {
    const distanceToTile = Math.max(0.001, this.cameraPosition.distanceTo(boundingSphere.center) - boundingSphere.radius);
    const screenSize = (boundingSphere.radius * this.screenScale) / distanceToTile;

    return screenSize > 220;
  }
}
