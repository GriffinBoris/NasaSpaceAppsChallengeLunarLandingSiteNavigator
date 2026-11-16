import { AmbientLight, DirectionalLight, MathUtils, PerspectiveCamera, Scene, Spherical, SRGBColorSpace, WebGLRenderer } from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { TerrainDatasetInterface } from "@/types/terrain/TerrainDatasetInterface";
import type { TerrainDetailInterface } from "@/types/terrain/TerrainDetailInterface";
import type { TerrainLocationInterface } from "@/types/terrain/TerrainLocationInterface";
import type { TerrainDisplayMode } from "@/types/terrain/TerrainDisplayMode";
import type { VisibilityPatchInterface } from "@/types/terrain/VisibilityInterface";
import type { IlluminationPatchInterface } from "@/types/terrain/IlluminationPatchInterface";
import type { EphemerisInterface } from "@/types/ephemeris/EphemerisInterface";
import { CelestialScene } from "@/views/home/viewer/celestialScene";
import { moonFixedPosition } from "@/views/home/viewer/ephemerisGeometry";
import { AMBIENT_LIGHT_INTENSITY, SUN_LIGHT_INTENSITY } from "@/views/home/viewer/moonLighting";
import { MoonSelection } from "@/views/home/viewer/moonSelection";
import { isValidLocation, locationDirection } from "@/views/home/viewer/moonPicking";
import { TerrainTiles, type LoadTerrainHeights } from "@/views/home/viewer/terrainTiles";
import { TerrainView } from "@/views/home/viewer/terrainView";
import { FeatureLabelView } from "@/views/home/viewer/featureLabelView";
import { AnimationFrame } from "./animationFrame.ts";

const MAXIMUM_RENDER_PIXELS = 3_500_000;
export const ZOOM_IN_FACTOR = 0.85;
export const ZOOM_OUT_FACTOR = 1.18;

export class MoonScene {
  private readonly renderer = new WebGLRenderer({ antialias: true, alpha: true });
  private readonly camera = new PerspectiveCamera(42, 1, 0.00005, 20);
  private readonly scene = new Scene();
  private readonly controls: OrbitControls;
  private readonly tiles: TerrainTiles;
  private readonly selection: MoonSelection;
  private readonly resizeObserver: ResizeObserver;
  private readonly light = new DirectionalLight(0xffffff, SUN_LIGHT_INTENSITY);
  private readonly inspectionLight = new DirectionalLight(0xffffff, 0);
  private readonly ambientLight = new AmbientLight(0xffffff, AMBIENT_LIGHT_INTENSITY);
  private readonly celestialScene: CelestialScene;
  private readonly referenceRadiusKm: number;
  private readonly renderFrame: AnimationFrame;
  private selectionNeedsRefresh = false;
  private viewNeedsUpdate = true;
  private updateTimer: ReturnType<typeof setTimeout> | undefined;

  constructor(
    private readonly container: HTMLElement,
    dataset: TerrainDatasetInterface,
    loadHeights: LoadTerrainHeights,
    onError: (hasError: boolean) => void,
    onDetailChange: (detail: TerrainDetailInterface | null) => void,
    onSelect: (location: TerrainLocationInterface) => void,
    private readonly onViewChange: () => void
  ) {
    this.renderFrame = new AnimationFrame(this.render);
    this.renderer.outputColorSpace = SRGBColorSpace;
    this.renderer.autoClear = false;
    this.renderer.domElement.tabIndex = 0;
    this.renderer.domElement.setAttribute("role", "application");
    this.renderer.domElement.setAttribute(
      "aria-label",
      "3D Moon. Arrow keys rotate, plus and minus zoom, and Enter selects the location at the center. You can also drag, scroll, pinch, and click."
    );
    this.renderer.domElement.style.touchAction = "none";
    this.renderer.domElement.addEventListener("keydown", this.onKeyDown);
    container.appendChild(this.renderer.domElement);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enablePan = false;
    this.controls.minDistance = 1.008;
    this.controls.maxDistance = 6;
    this.controls.minPolarAngle = 0.001;
    this.controls.maxPolarAngle = Math.PI - 0.001;
    this.controls.zoomSpeed = 0.65;
    this.controls.rotateSpeed = 0.45;

    this.referenceRadiusKm = dataset.referenceRadius / 1000;
    this.celestialScene = new CelestialScene(dataset.referenceRadius);
    this.tiles = new TerrainTiles(
      dataset,
      loadHeights,
      (detail) => {
        this.selectionNeedsRefresh = true;
        this.viewNeedsUpdate = true;

        onDetailChange(detail);
        this.renderFrame.request();
      },
      onError
    );
    this.selection = new MoonSelection(this.renderer.domElement, this.camera, this.tiles.group, dataset.tileSize, onSelect, (location) => {
      this.tiles.setHoverLocation(location);

      this.renderFrame.request();
    });
    this.inspectionLight.visible = false;
    this.scene.add(this.tiles.group, this.light, this.inspectionLight, this.ambientLight);

    this.resizeObserver = new ResizeObserver(this.resize);
    this.resizeObserver.observe(container);

    this.reset();
    this.resize();
    this.controls.addEventListener("change", this.onCameraChange);
  }

  async initialize() {
    await this.tiles.initialize();

    this.onCameraChange();
  }

  private render = () => {
    if (this.inspectionLight.visible) {
      this.inspectionLight.position.copy(this.camera.position).setLength(10);
    }

    if (this.selectionNeedsRefresh) {
      this.selectionNeedsRefresh = false;
      this.selection.refresh();
    }

    this.celestialScene.updateCamera(this.camera);

    this.renderer.clear();
    this.renderer.render(this.celestialScene.scene, this.celestialScene.camera);
    this.renderer.clearDepth();

    this.renderer.render(this.scene, this.camera);

    if (this.viewNeedsUpdate) {
      this.viewNeedsUpdate = false;
      this.onViewChange();
    }
  };

  private onCameraChange = () => {
    this.viewNeedsUpdate = true;
    this.camera.near = Math.max(0.00005, (this.camera.position.length() - 1.007) * 0.1);
    this.camera.updateProjectionMatrix();

    this.tiles.coarsen(new TerrainView(this.camera, this.container.clientHeight));
    this.selection.clearHover();
    this.renderFrame.request();

    clearTimeout(this.updateTimer);

    this.updateTimer = setTimeout(() => {
      const view = new TerrainView(this.camera, this.container.clientHeight);

      void this.tiles.requestUpdate(view);
    }, 100);
  };

  private resize = () => {
    const viewportWidth = this.container.clientWidth;
    const viewportHeight = this.container.clientHeight;

    if (!viewportWidth || !viewportHeight) {
      return;
    }

    const budgetRatio = Math.sqrt(MAXIMUM_RENDER_PIXELS / (viewportWidth * viewportHeight));

    this.camera.aspect = viewportWidth / viewportHeight;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, Math.max(1, Math.min(2, budgetRatio))));
    this.renderer.setSize(viewportWidth, viewportHeight);

    this.onCameraChange();
  };

  private onKeyDown = (event: KeyboardEvent) => {
    const step = MathUtils.clamp((this.camera.position.length() - 1) * 0.15, 0.0005, 0.2) * (event.shiftKey ? 4 : 1);

    switch (event.key) {
      case "ArrowLeft":
        this.orbit(-step, 0);
        break;
      case "ArrowRight":
        this.orbit(step, 0);
        break;
      case "ArrowUp":
        this.orbit(0, -step);
        break;
      case "ArrowDown":
        this.orbit(0, step);
        break;
      case "+":
      case "=":
        this.zoom(ZOOM_IN_FACTOR);
        break;
      case "-":
      case "_":
        this.zoom(ZOOM_OUT_FACTOR);
        break;
      case "Enter":
      case " ":
        this.selection.selectCenter();
        break;
      default:
        return;
    }

    event.preventDefault();
  };

  private orbit(azimuthRadians: number, polarRadians: number) {
    const spherical = new Spherical().setFromVector3(this.camera.position);

    spherical.theta += azimuthRadians;
    spherical.phi = MathUtils.clamp(spherical.phi + polarRadians, this.controls.minPolarAngle, this.controls.maxPolarAngle);
    this.camera.position.setFromSpherical(spherical);
    this.controls.update();
  }

  reset() {
    const aspect = this.container.clientWidth / this.container.clientHeight || 1;
    const halfFieldOfView = Math.atan(Math.tan((this.camera.fov * Math.PI) / 360) * Math.min(1, aspect));
    const distance = Math.min(this.controls.maxDistance, Math.max(2.94, 1.12 / Math.sin(halfFieldOfView)));

    this.camera.position.set(2.8, -0.8, 0.4).setLength(distance);
    this.controls.update();
  }

  focusSouthPole() {
    this.camera.position.set(0, -1.02, 0.0015);
    this.controls.update();
  }

  focusLocation(location: TerrainLocationInterface, radiusMeters: number) {
    if (!isValidLocation(location) || !Number.isFinite(radiusMeters) || radiusMeters < 0) {
      return;
    }

    const radius = Math.max(radiusMeters, 2500) / (this.referenceRadiusKm * 1000);
    const halfFieldOfView = Math.atan(Math.tan((this.camera.fov * Math.PI) / 360) * Math.min(1, this.camera.aspect));
    const surfaceRadius = this.selection.position.length();
    const distance = surfaceRadius + (radius / Math.tan(halfFieldOfView)) * 1.4;
    const clampedDistance = Math.max(this.controls.minDistance, Math.min(this.controls.maxDistance, distance));

    this.camera.position.copy(locationDirection(location)).multiplyScalar(clampedDistance);
    this.controls.update();
  }

  featureLabelView(): FeatureLabelView {
    return new FeatureLabelView(this.camera, this.container.clientWidth, this.container.clientHeight, this.referenceRadiusKm);
  }

  screenPosition(location: TerrainLocationInterface): { x: number; y: number } | null {
    const surface = locationDirection(location);

    if (surface.dot(this.camera.position) <= 1) {
      return null;
    }

    const projected = surface.project(this.camera);

    if (Math.abs(projected.x) > 1 || Math.abs(projected.y) > 1) {
      return null;
    }

    return {
      x: ((projected.x + 1) / 2) * this.container.clientWidth,
      y: ((1 - projected.y) / 2) * this.container.clientHeight,
    };
  }

  focusBody(body: "sun" | "earth") {
    this.camera.position.copy(this.celestialScene.viewingPosition(body));
    this.controls.update();
  }

  facesNightSide(): boolean {
    return this.camera.position.clone().normalize().dot(this.light.position.clone().normalize()) < -0.2;
  }

  setEphemeris(ephemeris: EphemerisInterface) {
    const sunDirection = moonFixedPosition(ephemeris.sun.positionKm, this.referenceRadiusKm).normalize();

    this.celestialScene.setEphemeris(ephemeris);
    this.light.position.copy(sunDirection).multiplyScalar(10);
    this.viewNeedsUpdate = true;

    this.renderFrame.request();
  }

  setDisplayMode(mode: TerrainDisplayMode) {
    this.tiles.setDisplayMode(mode);
  }

  setFullIllumination(enabled: boolean, brightnessPercent: number) {
    const brightnessRatio = brightnessPercent / 100;

    this.tiles.setFullIllumination(enabled);
    this.light.visible = !enabled;
    this.inspectionLight.visible = enabled;
    this.inspectionLight.intensity = 2.8 * brightnessRatio;
    this.ambientLight.intensity = enabled ? 0.2 * brightnessRatio : AMBIENT_LIGHT_INTENSITY;

    this.renderFrame.request();
  }

  setSunlightPatch(patch: VisibilityPatchInterface | null, sunlight: IlluminationPatchInterface | null = null) {
    this.tiles.setSunlightPatch(patch, sunlight);
  }

  setSelectedLocation(location: TerrainLocationInterface, radiusMeters: number) {
    this.selection.setLocation(location);
    this.tiles.setSelection(location, radiusMeters);

    this.renderFrame.request();
  }

  zoom(zoomFactor: number) {
    const nextDistance = this.camera.position.length() * zoomFactor;
    const minimumDistance = this.controls.minDistance;
    const maximumDistance = this.controls.maxDistance;
    const clampedDistance = Math.max(minimumDistance, Math.min(maximumDistance, nextDistance));

    this.camera.position.setLength(clampedDistance);
    this.controls.update();
  }

  dispose() {
    clearTimeout(this.updateTimer);
    this.renderFrame.dispose();

    this.resizeObserver.disconnect();

    this.renderer.domElement.removeEventListener("keydown", this.onKeyDown);
    this.controls.removeEventListener("change", this.onCameraChange);
    this.controls.dispose();

    this.tiles.dispose();
    this.selection.dispose();
    this.celestialScene.dispose();

    this.renderer.dispose();
    this.renderer.domElement.remove();
  }
}
