import type { EarthVisibilityInterface, EarthVisibilityPatchInterface } from "@/types/terrain/EarthVisibilityInterface";
import type { SiteCombinedVisibilityInterface } from "@/types/terrain/SiteCombinedVisibilityInterface";
import axios, { AxiosError, type AxiosInstance } from "axios";
import type { ErrorResponseInterface } from "@/types/api/ErrorResponseInterface";
import type { TerrainDatasetInterface } from "@/types/terrain/TerrainDatasetInterface";
import type { EphemerisInterface } from "@/types/ephemeris/EphemerisInterface";
import type { TerrainTileInterface } from "@/types/terrain/TerrainTileInterface";
import type { IlluminationProgressInterface } from "@/types/terrain/IlluminationProgressInterface";
import type { IlluminationInterface } from "@/types/terrain/IlluminationInterface";
import type { IlluminationPatchInterface } from "@/types/terrain/IlluminationPatchInterface";
import type { TerrainLocationInterface } from "@/types/terrain/TerrainLocationInterface";
import type { LunarFeatureInterface, LunarFeatureSearchResponseInterface } from "@/types/terrain/LunarFeatureInterface";
import type { FeatureLabelQueryInterface } from "@/types/terrain/FeatureLabelInterface";
import { readIlluminationStream } from "@/utils/illuminationStream";
import { camelToSnake, snakeToCamel } from "@/utils/caseConversion";

import type { SunlightSelectionInterface, SunlightSelectionListInterface } from "@/types/terrain/SunlightSelectionInterface";
import type { SunlightSelectionRequestInterface } from "@/types/terrain/SunlightSelectionRequestInterface";
import type { SunlightStudyInterface } from "@/types/terrain/SunlightStudyInterface";
import type { SiteDirectionsInterface, SiteTerrainInterface } from "@/types/terrain/SiteTerrainInterface";
import type { SiteHorizonInterface } from "@/types/terrain/SiteHorizonInterface";
import type { LocationHorizonInterface } from "@/types/terrain/LocationHorizonInterface";
import type { SunlightStudyRequestInterface } from "@/types/terrain/SunlightStudyRequestInterface";
import type { SunlightStudyUpdateRequestInterface } from "@/types/terrain/SunlightStudyUpdateRequestInterface";
import type { SunlightFrameDetailInterface, SunlightStudyDetailInterface } from "@/types/terrain/SunlightFrameInterface";

class ApiClient {
  private readonly transport: AxiosInstance;

  constructor() {
    this.transport = axios.create({
      baseURL: "/api/",
      timeout: 15000,
      withCredentials: true,
      withXSRFToken: true,
      xsrfCookieName: "csrftoken",
      xsrfHeaderName: "X-CSRFToken",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
    });
    this.transport.interceptors.response.use(
      (response) => {
        if (!(response.data instanceof ArrayBuffer) && !(response.data instanceof ReadableStream)) {
          response.data = snakeToCamel(response.data);
        }

        return response;
      },
      (error: AxiosError<ErrorResponseInterface>) => {
        if (error.response && !(error.response.data instanceof ArrayBuffer)) {
          error.response.data = snakeToCamel(error.response.data) as ErrorResponseInterface;
        }

        return Promise.reject(error);
      }
    );
  }

  async get<T>(url: string, params?: Record<string, string>, signal?: AbortSignal): Promise<T> {
    const response = await this.transport.get<T>(url, { params: camelToSnake(params), signal });

    return response.data;
  }

  async getBinary(url: string, signal: AbortSignal): Promise<ArrayBuffer> {
    const response = await this.transport.get<ArrayBuffer>(url, {
      responseType: "arraybuffer",
      signal,
    });

    return response.data;
  }

  async getStream(url: string, params: Record<string, string>, signal: AbortSignal): Promise<ReadableStream<Uint8Array>> {
    const response = await this.transport.get<ReadableStream<Uint8Array>>(url, {
      params: camelToSnake(params),
      adapter: "fetch",
      responseType: "stream",
      timeout: 0,
      signal,
      headers: { Accept: "application/x-ndjson, application/json" },
      validateStatus: () => true,
    });

    if (response.status >= 400) {
      const data = snakeToCamel(await new Response(response.data).json()) as ErrorResponseInterface;

      throw new AxiosError<ErrorResponseInterface>("Request failed", undefined, response.config, response.request, { ...response, data });
    }

    return response.data;
  }

  async patch<T>(url: string, data: object): Promise<T> {
    const response = await this.transport.patch<T>(url, camelToSnake(data));

    return response.data;
  }

  async put<T>(url: string, data: object): Promise<T> {
    const response = await this.transport.put<T>(url, camelToSnake(data));

    return response.data;
  }

  async delete(url: string): Promise<void> {
    await this.transport.delete(url);
  }

  async post<T>(url: string, data?: object): Promise<T> {
    const response = await this.transport.post<T>(url, camelToSnake(data));

    return response.data;
  }
}

export const apiClient = new ApiClient();

const terrain = {
  detail: () => apiClient.get<TerrainDatasetInterface>("terrain/"),
  horizon: (datasetId: number, location: TerrainLocationInterface, timestamp: string, signal: AbortSignal) =>
    apiClient.get<LocationHorizonInterface>(
      `terrain/${datasetId}/horizon/`,
      { timestamp, latitude: String(location.latitude), longitude: String(location.longitude) },
      signal
    ),
  tile: async (dataset: TerrainDatasetInterface, tile: TerrainTileInterface, signal: AbortSignal): Promise<Float32Array> => {
    const url = dataset.tileUrlTemplate
      .replace("{face}", String(tile.face))
      .replace("{level}", String(tile.level))
      .replace("{x}", String(tile.x))
      .replace("{y}", String(tile.y));
    const buffer = await apiClient.getBinary(url, signal);

    return new Float32Array(buffer);
  },
  illumination: (datasetId: number, location: TerrainLocationInterface, timestamp: string, signal: AbortSignal) =>
    apiClient.get<IlluminationInterface>(
      `terrain/${datasetId}/illumination/`,
      { timestamp, latitude: String(location.latitude), longitude: String(location.longitude) },
      signal
    ),
  illuminationPatch: async (
    datasetId: number,
    location: TerrainLocationInterface,
    timestamp: string,
    radiusMeters: number,
    signal: AbortSignal,
    onProgress: (progress: IlluminationProgressInterface) => void
  ) => {
    const stream = await apiClient.getStream(
      `terrain/${datasetId}/illumination/patch/`,
      { timestamp, latitude: String(location.latitude), longitude: String(location.longitude), radiusMeters: String(radiusMeters) },
      signal
    );

    return readIlluminationStream<IlluminationPatchInterface>(stream, onProgress);
  },
  earth: (datasetId: number, location: TerrainLocationInterface, timestamp: string, signal: AbortSignal) =>
    apiClient.get<EarthVisibilityInterface>(
      `terrain/${datasetId}/earth/`,
      { timestamp, latitude: String(location.latitude), longitude: String(location.longitude) },
      signal
    ),
  earthPatch: async (
    datasetId: number,
    location: TerrainLocationInterface,
    timestamp: string,
    radiusMeters: number,
    signal: AbortSignal,
    onProgress: (progress: IlluminationProgressInterface) => void
  ) => {
    const stream = await apiClient.getStream(
      `terrain/${datasetId}/earth/patch/`,
      { timestamp, latitude: String(location.latitude), longitude: String(location.longitude), radiusMeters: String(radiusMeters) },
      signal
    );

    return readIlluminationStream<EarthVisibilityPatchInterface>(stream, onProgress);
  },
};

const ephemeris = {
  detail: (timestamp: string, signal: AbortSignal) => apiClient.get<EphemerisInterface>("ephemeris/", { timestamp }, signal),
};

const selections = {
  list: () => apiClient.get<SunlightSelectionListInterface>("terrain/selections/"),
  create: (data: SunlightSelectionRequestInterface) => apiClient.post<SunlightSelectionInterface>("terrain/selections/", data),
  rename: (selectionId: number, name: string) => apiClient.patch<SunlightSelectionInterface>(`terrain/selections/${selectionId}/`, { name }),
  remove: (selectionId: number) => apiClient.delete(`terrain/selections/${selectionId}/`),
};

const studies = {
  list: (signal?: AbortSignal) => apiClient.get<SunlightStudyInterface[]>("terrain/studies/", undefined, signal),
  create: (data: SunlightStudyRequestInterface) => apiClient.post<SunlightStudyInterface>("terrain/studies/", data),
  detail: (studyId: number, signal?: AbortSignal, afterRevision?: number) =>
    apiClient.get<SunlightStudyDetailInterface>(
      `terrain/studies/${studyId}/`,
      afterRevision === undefined ? undefined : { afterRevision: String(afterRevision) },
      signal
    ),
  siteTerrain: (studyId: number, selectionId: number, signal: AbortSignal) =>
    apiClient.get<SiteTerrainInterface>(`terrain/studies/${studyId}/selections/${selectionId}/terrain/`, undefined, signal),
  siteDirections: (studyId: number, selectionId: number, signal: AbortSignal) =>
    apiClient.get<SiteDirectionsInterface>(`terrain/studies/${studyId}/selections/${selectionId}/directions/`, undefined, signal),
  siteHorizon: (studyId: number, selectionId: number, signal: AbortSignal) =>
    apiClient.get<SiteHorizonInterface>(`terrain/studies/${studyId}/selections/${selectionId}/horizon/`, undefined, signal),
  siteCombinedVisibility: (studyId: number, selectionId: number, signal: AbortSignal, afterRevision?: number) =>
    apiClient.get<SiteCombinedVisibilityInterface>(
      `terrain/studies/${studyId}/selections/${selectionId}/combined/`,
      afterRevision === undefined ? undefined : { afterRevision: String(afterRevision) },
      signal
    ),
  update: (studyId: number, data: SunlightStudyUpdateRequestInterface) => apiClient.put<SunlightStudyInterface>(`terrain/studies/${studyId}/`, data),
  frame: (studyId: number, frameId: number, signal: AbortSignal) =>
    apiClient.get<SunlightFrameDetailInterface>(`terrain/studies/${studyId}/frames/${frameId}/`, undefined, signal),
  remove: (studyId: number) => apiClient.delete(`terrain/studies/${studyId}/`),
  calculate: (studyId: number, workerCount?: number) =>
    apiClient.post<SunlightStudyInterface>(`terrain/studies/${studyId}/calculate/`, { workerCount }),
  stop: (studyId: number) => apiClient.post<SunlightStudyInterface>(`terrain/studies/${studyId}/stop/`),
};

const features = {
  search: (query: string, signal: AbortSignal) => apiClient.get<LunarFeatureSearchResponseInterface>("terrain/features/", { q: query }, signal),
  labels: (query: FeatureLabelQueryInterface, signal: AbortSignal) =>
    apiClient.get<LunarFeatureInterface[]>(
      "terrain/features/labels/",
      {
        latitude: String(query.latitude),
        longitude: String(query.longitude),
        radiusDegrees: String(query.radiusDegrees),
        minimumDiameterKm: String(query.minimumDiameterKm),
      },
      signal
    ),
};

export const api = { terrain, ephemeris, selections, studies, features };
