import type { EarthVisibilityInterface, EarthVisibilityPatchInterface } from "./EarthVisibilityInterface";
import type { IlluminationInterface } from "./IlluminationInterface";
import type { IlluminationPatchInterface } from "./IlluminationPatchInterface";
import type { SunlightStudyInterface } from "./SunlightStudyInterface";
import type { VisibilityGridInterface } from "./SiteTerrainInterface";

export interface SunlightFrameInterface {
  id: number;
  studyId: number;
  selectionId: number;
  timestamp: string;
  visibleSunFraction: number | null;
  visibleEarthFraction: number | null;
  earthCenterVisible: boolean | null;
  jointVisibleShare: number | null;
  resultRevision: number;
  thumbnail: VisibilityGridInterface | null;
  earthThumbnail: VisibilityGridInterface | null;
}

export interface SunlightFrameDetailInterface extends SunlightFrameInterface {
  result: { center: IlluminationInterface; patch: IlluminationPatchInterface | null } | null;
  earthResult: { center: EarthVisibilityInterface; patch: EarthVisibilityPatchInterface | null } | null;
}

export interface SunlightStudyDetailInterface {
  reset: boolean;
  study: SunlightStudyInterface;
  frames: SunlightFrameInterface[];
}
