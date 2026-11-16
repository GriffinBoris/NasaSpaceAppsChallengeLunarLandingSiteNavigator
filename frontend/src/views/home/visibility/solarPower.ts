import type { SolarPanelSettingsInterface, SolarPowerInterface } from "@/types/terrain/SolarPowerInterface";

export const SOLAR_IRRADIANCE_WATTS_PER_SQUARE_METER = 1361;

export function solarPanelError(panel: SolarPanelSettingsInterface): string {
  if (!Number.isFinite(panel.areaSquareMeters) || panel.areaSquareMeters <= 0) {
    return "Enter a panel area greater than zero.";
  }
  if (!Number.isFinite(panel.efficiencyPercent) || panel.efficiencyPercent <= 0 || panel.efficiencyPercent > 100) {
    return "Enter an efficiency greater than zero and no more than 100%.";
  }

  return "";
}

export function estimateSolarPower(
  sunElevationDegrees: number,
  visibleSunFraction: number,
  panel: SolarPanelSettingsInterface
): SolarPowerInterface | null {
  if (solarPanelError(panel)) {
    return null;
  }

  const levelIncidenceFraction = Math.max(0, Math.sin((sunElevationDegrees * Math.PI) / 180));
  const trackingIrradianceWattsPerSquareMeter = SOLAR_IRRADIANCE_WATTS_PER_SQUARE_METER * visibleSunFraction;
  const levelIrradianceWattsPerSquareMeter = trackingIrradianceWattsPerSquareMeter * levelIncidenceFraction;
  const conversion = (panel.areaSquareMeters * panel.efficiencyPercent) / 100;

  return {
    levelIrradianceWattsPerSquareMeter,
    trackingIrradianceWattsPerSquareMeter,
    levelPowerWatts: levelIrradianceWattsPerSquareMeter * conversion,
    trackingPowerWatts: trackingIrradianceWattsPerSquareMeter * conversion,
    levelIncidenceFraction,
  };
}
