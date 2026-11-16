import type { HorizonInterface } from "./HorizonInterface";
import type { TerrainLocationInterface } from "./TerrainLocationInterface";
import type { BodyDirectionInterface } from "./SiteTerrainInterface";

export interface LocationHorizonInterface extends HorizonInterface, TerrainLocationInterface {
  datasetId: number;
  timestamp: string;
  sun: BodyDirectionInterface;
  earth: BodyDirectionInterface;
}
