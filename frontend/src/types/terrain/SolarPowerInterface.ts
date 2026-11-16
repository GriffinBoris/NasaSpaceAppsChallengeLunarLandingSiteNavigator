export interface SolarPanelSettingsInterface {
  areaSquareMeters: number;
  efficiencyPercent: number;
}

export interface SolarPowerInterface {
  levelIrradianceWattsPerSquareMeter: number;
  trackingIrradianceWattsPerSquareMeter: number;
  levelPowerWatts: number;
  trackingPowerWatts: number;
  levelIncidenceFraction: number;
}
