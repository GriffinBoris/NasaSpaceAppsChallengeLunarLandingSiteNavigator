import { Raycaster, Vector2, Vector3, type Group, type PerspectiveCamera } from "three";
import type { TerrainLocationInterface } from "@/types/terrain/TerrainLocationInterface";
import { intersectTerrain, isValidLocation, locationDirection, terrainLocation } from "./moonPicking.ts";
import { AnimationFrame } from "./animationFrame.ts";

export class MoonSelection {
  readonly position = new Vector3(1, 0, 0);

  private readonly canvas: HTMLCanvasElement;
  private readonly camera: PerspectiveCamera;
  private readonly terrain: Group;
  private readonly tileSize: number;
  private readonly onSelect: (location: TerrainLocationInterface) => void;
  private readonly onHover: (location: TerrainLocationInterface | null) => void;
  private readonly raycaster = new Raycaster();
  private readonly hoverFrame: AnimationFrame;
  private hoverPointer?: PointerEvent;
  private isHovering = false;
  private location?: TerrainLocationInterface;
  private pointerStart?: { pointerId: number; position: Vector2 };

  constructor(
    canvas: HTMLCanvasElement,
    camera: PerspectiveCamera,
    terrain: Group,
    tileSize: number,
    onSelect: (location: TerrainLocationInterface) => void,
    onHover: (location: TerrainLocationInterface | null) => void
  ) {
    this.canvas = canvas;
    this.camera = camera;
    this.terrain = terrain;
    this.tileSize = tileSize;
    this.onSelect = onSelect;
    this.onHover = onHover;
    this.hoverFrame = new AnimationFrame(this.updateHover);

    canvas.addEventListener("pointerdown", this.onPointerDown);
    canvas.addEventListener("pointermove", this.onPointerMove);
    canvas.addEventListener("pointerup", this.onPointerUp);
    canvas.addEventListener("pointercancel", this.onPointerCancel);
    canvas.addEventListener("pointerleave", this.onPointerCancel);
  }

  setLocation(location: TerrainLocationInterface) {
    this.location = location;

    this.refresh();
  }

  refresh() {
    const location = this.location;

    if (!location || !isValidLocation(location)) {
      return;
    }

    const direction = locationDirection(location);

    this.raycaster.set(direction.clone().multiplyScalar(2), direction.clone().negate());

    const point = intersectTerrain(this.raycaster, this.terrain, this.tileSize);

    this.position.copy(point ?? direction);
  }

  clearHover() {
    this.hoverFrame.cancel();
    this.hoverPointer = undefined;

    if (!this.isHovering) {
      return;
    }

    this.isHovering = false;
    this.onHover(null);
  }

  selectCenter() {
    const location = this.pickAt(new Vector2(0, 0));

    if (location) {
      this.select(location);
    }
  }

  private pickLocation(event: PointerEvent): TerrainLocationInterface | null {
    const bounds = this.canvas.getBoundingClientRect();

    return this.pickAt(new Vector2(((event.clientX - bounds.left) / bounds.width) * 2 - 1, 1 - ((event.clientY - bounds.top) / bounds.height) * 2));
  }

  private pickAt(pointer: Vector2): TerrainLocationInterface | null {
    this.raycaster.setFromCamera(pointer, this.camera);

    const point = intersectTerrain(this.raycaster, this.terrain, this.tileSize);

    return point ? terrainLocation(point) : null;
  }

  private onPointerDown = (event: PointerEvent) => {
    this.pointerStart = undefined;
    this.clearHover();

    if (event.button === 0 && event.isPrimary) {
      this.pointerStart = { pointerId: event.pointerId, position: new Vector2(event.clientX, event.clientY) };
    }
  };

  private onPointerMove = (event: PointerEvent) => {
    if (this.pointerStart && this.pointerStart.position.distanceTo(new Vector2(event.clientX, event.clientY)) > 5) {
      this.pointerStart = undefined;
    }

    if (event.pointerType === "touch" || !event.isPrimary || event.buttons !== 0) {
      this.clearHover();
      return;
    }

    this.hoverPointer = event;
    this.hoverFrame.request();
  };

  private updateHover = () => {
    const location = this.pickLocation(this.hoverPointer!);

    this.hoverPointer = undefined;

    if (!location) {
      this.clearHover();
      return;
    }

    this.isHovering = true;
    this.onHover(location);
  };

  private onPointerUp = (event: PointerEvent) => {
    const start = this.pointerStart;

    this.pointerStart = undefined;

    if (!start || event.pointerId !== start.pointerId || start.position.distanceTo(new Vector2(event.clientX, event.clientY)) > 5) {
      return;
    }

    const location = this.pickLocation(event);

    if (location) {
      this.select(location);
    }
  };

  private select(location: TerrainLocationInterface) {
    this.onSelect({ latitude: Number(location.latitude.toFixed(6)), longitude: Number(location.longitude.toFixed(6)) });
  }

  private onPointerCancel = () => {
    this.pointerStart = undefined;
    this.clearHover();
  };

  dispose() {
    this.hoverFrame.dispose();

    this.canvas.removeEventListener("pointerdown", this.onPointerDown);
    this.canvas.removeEventListener("pointermove", this.onPointerMove);
    this.canvas.removeEventListener("pointerup", this.onPointerUp);
    this.canvas.removeEventListener("pointercancel", this.onPointerCancel);
    this.canvas.removeEventListener("pointerleave", this.onPointerCancel);
  }
}
