export function formatCoordinates(latitude: number, longitude: number, decimalPlaces = 2): string {
  const latitudeText = `${Math.abs(latitude).toFixed(decimalPlaces)}°${latitude < 0 ? "S" : "N"}`;
  const longitudeText = `${Math.abs(longitude).toFixed(decimalPlaces)}°${longitude < 0 ? "W" : "E"}`;

  return `${latitudeText} ${longitudeText}`;
}

export function formatRadius(radiusMeters: number | null): string {
  return radiusMeters === null ? "Point" : `${radiusMeters / 1000} km radius`;
}
