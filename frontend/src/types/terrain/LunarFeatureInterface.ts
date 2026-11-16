export interface LunarFeatureInterface {
  id: number;
  usgsId: number;
  name: string;
  englishName: string | null;
  featureType: string;
  latitude: number;
  longitude: number;
  diameterKm: number | null;
  sourceUrl: string;
}

export interface LunarFeatureSearchResponseInterface {
  features: LunarFeatureInterface[];
  catalogLoaded: boolean;
}
