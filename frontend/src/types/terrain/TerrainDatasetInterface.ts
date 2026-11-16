export interface TerrainDatasetInterface {
  id: number;
  name: string;
  storageKey: string;
  frame: string;
  referenceRadius: number;
  tileSize: number;
  maxLevel: number;
  tileCount: number;
  refinements: string[];
  sources: {
    filename: string;
    url: string;
  }[];
  tileUrlTemplate: string;
}
