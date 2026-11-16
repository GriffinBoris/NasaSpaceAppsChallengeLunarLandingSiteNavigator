import type { LocationQuery } from "vue-router";
import type { TerrainLocationInterface } from "@/types/terrain/TerrainLocationInterface";

export interface MoonViewQueryInterface {
  siteId: number | null;
  point: { location: TerrainLocationInterface; radiusKm: number } | null;
  time: string | null;
}

const MAXIMUM_RADIUS_KM = 50;

function queryNumber(value: LocationQuery[string] | undefined): number | null {
  if (typeof value !== "string" || !value.trim()) {
    return null;
  }

  const number = Number(value);

  return Number.isFinite(number) ? number : null;
}

function queryId(value: LocationQuery[string] | undefined): number | null {
  const number = queryNumber(value);

  return number !== null && Number.isInteger(number) && number > 0 ? number : null;
}

export function parseMoonViewQuery(query: LocationQuery): MoonViewQueryInterface {
  const latitude = queryNumber(query.lat);
  const longitude = queryNumber(query.lon);
  const radiusKm = queryNumber(query.r) ?? 0;
  const timestamp = typeof query.t === "string" ? Date.parse(query.t) : Number.NaN;
  const hasPoint =
    latitude !== null &&
    longitude !== null &&
    Math.abs(latitude) <= 90 &&
    Math.abs(longitude) <= 180 &&
    radiusKm >= 0 &&
    radiusKm <= MAXIMUM_RADIUS_KM;

  return {
    siteId: queryId(query.site),
    point: hasPoint ? { location: { latitude, longitude }, radiusKm } : null,
    time: Number.isNaN(timestamp) ? null : new Date(timestamp).toISOString(),
  };
}

export function moonViewQuery(view: MoonViewQueryInterface): Record<string, string> {
  const query: Record<string, string> = {};

  if (view.siteId !== null) {
    query.site = String(view.siteId);
  } else if (view.point) {
    query.lat = view.point.location.latitude.toFixed(4);
    query.lon = view.point.location.longitude.toFixed(4);

    if (view.point.radiusKm) {
      query.r = String(view.point.radiusKm);
    }
  }

  if (view.time) {
    query.t = new Date(view.time).toISOString().replace(":00.000Z", "Z");
  }

  return query;
}
