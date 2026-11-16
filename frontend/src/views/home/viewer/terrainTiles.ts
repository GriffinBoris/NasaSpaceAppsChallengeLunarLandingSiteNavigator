import { DoubleSide, Group, Mesh, MeshStandardMaterial, Vector3 } from "three";
import type { TerrainDatasetInterface } from "@/types/terrain/TerrainDatasetInterface";
import type { TerrainDetailInterface } from "@/types/terrain/TerrainDetailInterface";
import type { TerrainTileInterface } from "@/types/terrain/TerrainTileInterface";
import type { TerrainDisplayMode } from "@/types/terrain/TerrainDisplayMode";
import type { TerrainLocationInterface } from "@/types/terrain/TerrainLocationInterface";
import type { VisibilityPatchInterface } from "@/types/terrain/VisibilityInterface";
import type { IlluminationPatchInterface } from "@/types/terrain/IlluminationPatchInterface";
import { createTileGeometry, tileCenter } from "./moonGeometry.ts";
import { TERRAIN_COLOR } from "./moonLighting.ts";
import type { TerrainView } from "./terrainView.ts";
import { SunlightOverlay } from "./sunlightOverlay.ts";

interface LoadedTile {
  coordinates: TerrainTileInterface;
  mesh: Mesh;
  center: Vector3;
  angularRadius: number;
}

const MAX_CACHED_TILES = 512;
const MAX_CONCURRENT_LOADS = 4;

function tileIdentifier(tile: TerrainTileInterface): string {
  return `${tile.face}/${tile.level}/${tile.x}/${tile.y}`;
}

export type LoadTerrainHeights = (tile: TerrainTileInterface, signal: AbortSignal) => Promise<Float32Array>;

export class TerrainTiles {
  readonly group = new Group();

  private readonly tiles = new Map<string, LoadedTile>();
  private readonly refinements: Set<string>;
  private readonly controller = new AbortController();
  private readonly material = new MeshStandardMaterial({ color: TERRAIN_COLOR, roughness: 1, side: DoubleSide });
  private readonly roots: LoadedTile[] = [];
  private readonly dataset: TerrainDatasetInterface;
  private readonly loadHeights: LoadTerrainHeights;
  private readonly onChange: (detail: TerrainDetailInterface | null) => void;
  private readonly onError: (hasError: boolean) => void;
  private readonly sunlightOverlay: SunlightOverlay;

  private view?: TerrainView;
  private updating = false;
  private disposed = false;

  constructor(
    dataset: TerrainDatasetInterface,
    loadHeights: LoadTerrainHeights,
    onChange: (detail: TerrainDetailInterface | null) => void,
    onError: (hasError: boolean) => void
  ) {
    this.dataset = dataset;
    this.loadHeights = loadHeights;
    this.onChange = onChange;
    this.onError = onError;

    this.refinements = new Set(dataset.refinements);
    this.sunlightOverlay = new SunlightOverlay(this.material, dataset.referenceRadius);
  }

  async initialize() {
    const coordinates: TerrainTileInterface[] = [];

    for (let face = 0; face < 6; face++) {
      coordinates.push({ face, level: 0, x: 0, y: 0 });
    }

    const roots = await this.loadTiles(coordinates);

    for (const root of roots) {
      root.mesh.visible = true;
      this.roots.push(root);
    }

    this.notifyChange();
  }

  private async loadTiles(coordinates: TerrainTileInterface[]): Promise<LoadedTile[]> {
    const tiles: LoadedTile[] = [];

    for (let start = 0; start < coordinates.length; start += MAX_CONCURRENT_LOADS) {
      const batch = coordinates.slice(start, start + MAX_CONCURRENT_LOADS);
      const results = await Promise.allSettled(batch.map((tile) => this.loadTile(tile)));

      for (const result of results) {
        if (result.status === "rejected") {
          throw result.reason;
        }

        tiles.push(result.value);
      }
    }

    return tiles;
  }

  private async loadTile(coordinates: TerrainTileInterface): Promise<LoadedTile> {
    const identifier = tileIdentifier(coordinates);
    const cachedTile = this.tiles.get(identifier);

    if (cachedTile) {
      this.tiles.delete(identifier);
      this.tiles.set(identifier, cachedTile);

      return cachedTile;
    }

    const heights = await this.loadHeights(coordinates, this.controller.signal);

    if (this.disposed) {
      throw new Error("The terrain viewer was closed.");
    }

    const geometry = createTileGeometry(coordinates, heights, this.dataset.tileSize, this.dataset.referenceRadius);
    const mesh = new Mesh(geometry, this.material);

    const center = tileCenter(coordinates);
    const corner = tileCenter({ ...coordinates, level: coordinates.level + 1, x: coordinates.x * 2, y: coordinates.y * 2 });
    const angularRadius = Math.min(Math.PI, center.angleTo(corner) * 2.2);
    const tile = { coordinates, mesh, center, angularRadius };

    mesh.visible = false;
    this.tiles.set(identifier, tile);
    this.group.add(mesh);

    return tile;
  }

  requestUpdate(view: TerrainView) {
    this.view = view;

    if (!this.updating && !this.disposed) {
      return this.update();
    }
  }

  coarsen(view: TerrainView) {
    let changed = false;

    for (const root of this.roots) {
      changed = this.coarsenTile(root, view) || changed;
    }

    if (changed) {
      this.notifyChange();
    }
  }

  private coarsenTile(tile: LoadedTile, view: TerrainView): boolean {
    if (tile.mesh.visible) {
      return false;
    }

    const boundingSphere = tile.mesh.geometry.boundingSphere!;
    const needsDetail =
      view.isVisible(boundingSphere, tile.center, tile.angularRadius) &&
      this.refinements.has(tileIdentifier(tile.coordinates)) &&
      view.needsDetail(boundingSphere);

    if (!needsDetail) {
      tile.mesh.visible = true;
      this.hideDescendants(tile);
      return true;
    }

    let changed = false;

    for (const coordinates of this.children(tile.coordinates)) {
      const child = this.tiles.get(tileIdentifier(coordinates));

      if (child) {
        changed = this.coarsenTile(child, view) || changed;
      }
    }

    return changed;
  }

  setDisplayMode(mode: TerrainDisplayMode) {
    this.sunlightOverlay.setDisplayMode(mode);
    this.material.vertexColors = mode === "elevation";
    this.material.color.set(mode === "elevation" ? 0xffffff : TERRAIN_COLOR);
    this.material.needsUpdate = true;

    this.notifyChange();
  }

  setSelection(location: TerrainLocationInterface, radiusMeters: number) {
    this.sunlightOverlay.setSelection(location, radiusMeters);

    this.notifyChange();
  }

  setHoverLocation(location: TerrainLocationInterface | null) {
    this.sunlightOverlay.setHoverLocation(location);
  }

  setSunlightPatch(patch: VisibilityPatchInterface | null, sunlight: IlluminationPatchInterface | null = null) {
    this.sunlightOverlay.setPatch(patch, sunlight);

    this.notifyChange();
  }

  setFullIllumination(enabled: boolean) {
    this.sunlightOverlay.setFullIllumination(enabled);
  }

  private async update() {
    this.updating = true;

    try {
      this.notifyChange();

      let completedView: TerrainView;

      do {
        completedView = this.view!;

        for (const root of this.roots) {
          await this.select(root, completedView);
        }
      } while (completedView !== this.view && !this.disposed);

      if (this.disposed) {
        return;
      }

      this.evictUnused();
      this.onError(false);
    } catch {
      if (!this.disposed) {
        this.onError(true);
      }
    } finally {
      this.updating = false;

      if (!this.disposed) {
        this.notifyChange();
      }
    }
  }

  private notifyChange() {
    let minimumLevel = this.dataset.maxLevel;
    let maximumLevel = 0;
    let hasVisibleTile = false;

    for (const tile of this.tiles.values()) {
      if (!tile.mesh.visible) {
        continue;
      }

      const boundingSphere = tile.mesh.geometry.boundingSphere!;

      if (this.view && !this.view.isVisible(boundingSphere, tile.center, tile.angularRadius)) {
        continue;
      }

      hasVisibleTile = true;
      minimumLevel = Math.min(minimumLevel, tile.coordinates.level);
      maximumLevel = Math.max(maximumLevel, tile.coordinates.level);
    }

    if (!hasVisibleTile) {
      this.onChange(null);
      return;
    }

    this.onChange({ minimumLevel, maximumLevel, maximumAvailableLevel: this.dataset.maxLevel, isLoading: this.updating });
  }

  private children(coordinates: TerrainTileInterface): TerrainTileInterface[] {
    const children: TerrainTileInterface[] = [];

    for (let childRow = 0; childRow < 2; childRow++) {
      for (let childColumn = 0; childColumn < 2; childColumn++) {
        children.push({
          face: coordinates.face,
          level: coordinates.level + 1,
          x: coordinates.x * 2 + childColumn,
          y: coordinates.y * 2 + childRow,
        });
      }
    }

    return children;
  }

  private hideDescendants(tile: LoadedTile) {
    for (const coordinates of this.children(tile.coordinates)) {
      const child = this.tiles.get(tileIdentifier(coordinates));

      if (child) {
        child.mesh.visible = false;
        this.hideDescendants(child);
      }
    }
  }

  private async select(tile: LoadedTile, view: TerrainView) {
    if (view !== this.view || this.disposed) {
      return;
    }

    const boundingSphere = tile.mesh.geometry.boundingSphere!;
    const isVisible = view.isVisible(boundingSphere, tile.center, tile.angularRadius);

    if (!isVisible) {
      tile.mesh.visible = true;
      this.hideDescendants(tile);
      return;
    }

    const identifier = tileIdentifier(tile.coordinates);

    this.tiles.delete(identifier);
    this.tiles.set(identifier, tile);

    const shouldRefine = this.refinements.has(identifier) && view.needsDetail(boundingSphere);

    if (!shouldRefine) {
      tile.mesh.visible = true;
      this.hideDescendants(tile);
      return;
    }

    const children = await this.loadTiles(this.children(tile.coordinates));

    if (view !== this.view || this.disposed) {
      return;
    }

    tile.mesh.visible = false;

    for (const child of children) {
      child.mesh.visible = true;
    }

    this.notifyChange();

    for (const child of children) {
      await this.select(child, view);
    }
  }

  private evictUnused() {
    const retainedTileIdentifiers = new Set<string>();

    for (const tile of this.tiles.values()) {
      if (!tile.mesh.visible && tile.coordinates.level > 0) {
        continue;
      }

      const coordinates = { ...tile.coordinates };

      while (coordinates.level >= 0) {
        retainedTileIdentifiers.add(tileIdentifier(coordinates));
        coordinates.level -= 1;
        coordinates.x = Math.floor(coordinates.x / 2);
        coordinates.y = Math.floor(coordinates.y / 2);
      }
    }

    for (const [identifier, tile] of this.tiles) {
      if (this.tiles.size <= MAX_CACHED_TILES) {
        break;
      }

      if (!retainedTileIdentifiers.has(identifier)) {
        this.group.remove(tile.mesh);
        tile.mesh.geometry.dispose();
        this.tiles.delete(identifier);
      }
    }
  }

  dispose() {
    this.disposed = true;
    this.controller.abort();

    for (const tile of this.tiles.values()) {
      this.group.remove(tile.mesh);
      tile.mesh.geometry.dispose();
    }

    this.tiles.clear();
    this.roots.length = 0;
    this.sunlightOverlay.dispose();
    this.material.dispose();
  }
}
