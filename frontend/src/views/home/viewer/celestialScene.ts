import {
  AmbientLight,
  DirectionalLight,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  PerspectiveCamera,
  Scene,
  SphereGeometry,
  Vector3,
} from "three";
import type { EphemerisInterface } from "@/types/ephemeris/EphemerisInterface";
import { moonFixedPosition, skyBodyPlacement } from "./ephemerisGeometry.ts";

export class CelestialScene {
  readonly scene = new Scene();
  readonly camera = new PerspectiveCamera(42, 1, 1, 2000);

  private readonly geometry = new SphereGeometry(1, 48, 24);
  private readonly sunMaterial = new MeshBasicMaterial({ color: 0xfff3cf, toneMapped: false });
  private readonly earthMaterial = new MeshStandardMaterial({ color: 0x3c86bb, roughness: 1 });
  private readonly sun = new Mesh(this.geometry, this.sunMaterial);
  private readonly earth = new Mesh(this.geometry, this.earthMaterial);
  private readonly earthLight = new DirectionalLight(0xffffff, 2.5);
  private readonly referenceRadiusKm: number;
  private ephemeris?: EphemerisInterface;

  constructor(referenceRadiusMeters: number) {
    this.referenceRadiusKm = referenceRadiusMeters / 1000;
    this.scene.add(this.sun, this.earth, this.earthLight, this.earthLight.target, new AmbientLight(0xffffff, 0.03));
    this.scene.visible = false;
  }

  setEphemeris(ephemeris: EphemerisInterface) {
    this.ephemeris = ephemeris;
    this.scene.visible = true;
  }

  viewingPosition(body: "sun" | "earth"): Vector3 {
    const direction = moonFixedPosition(this.ephemeris![body].positionKm, this.referenceRadiusKm).normalize();

    direction.negate();
    direction.applyAxisAngle(new Vector3(0, 1, 0), Math.PI / 12);

    return direction.multiplyScalar(5);
  }

  updateCamera(observer: PerspectiveCamera) {
    if (!this.ephemeris) {
      return;
    }

    this.camera.quaternion.copy(observer.quaternion);
    this.camera.aspect = observer.aspect;
    this.camera.fov = observer.fov;
    this.camera.updateProjectionMatrix();

    const sunPlacement = skyBodyPlacement(this.ephemeris.sun, observer.position, this.referenceRadiusKm);
    const earthPlacement = skyBodyPlacement(this.ephemeris.earth, observer.position, this.referenceRadiusKm);

    this.sun.position.copy(sunPlacement.position);
    this.sun.scale.setScalar(sunPlacement.radius);
    this.earth.position.copy(earthPlacement.position);
    this.earth.scale.setScalar(earthPlacement.radius);

    const sunPosition = moonFixedPosition(this.ephemeris.sun.positionKm, this.referenceRadiusKm);
    const earthPosition = moonFixedPosition(this.ephemeris.earth.positionKm, this.referenceRadiusKm);
    const lightDirection = sunPosition.sub(earthPosition).normalize();

    this.earthLight.target.position.copy(this.earth.position);
    this.earthLight.position.copy(this.earth.position).addScaledVector(lightDirection, 100);
  }

  dispose() {
    this.geometry.dispose();
    this.sunMaterial.dispose();
    this.earthMaterial.dispose();
    this.scene.clear();
  }
}
