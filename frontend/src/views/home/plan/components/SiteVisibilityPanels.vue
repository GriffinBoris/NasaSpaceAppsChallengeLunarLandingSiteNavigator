<template>
  <div class="w-full space-y-6">
    <slot name="overview" />
    <slot name="calendar" />
    <section
      ref="mapSection"
      aria-labelledby="site-panels-heading"
      class="w-full space-y-3"
    >
      <div>
        <h2
          id="site-panels-heading"
          ref="mapHeading"
          class="text-lg font-semibold text-body outline-none"
          tabindex="-1"
        >
          Sunlight and Earth visibility
        </h2>
        <p class="text-xs text-secondary">{{ site.selection.name }}</p>
      </div>

      <div class="sticky top-0 z-10 -mx-1 flex flex-wrap items-center gap-x-3 gap-y-2 bg-background px-1 py-2">
        <AppButton
          :disabled="schedule.length < 2"
          @click="togglePlayback"
        >
          <Pause
            v-if="isPlaying"
            aria-hidden="true"
          />
          <Play
            v-else
            aria-hidden="true"
          />
          <span class="max-sm:sr-only">{{ isPlaying ? "Pause" : "Play" }}</span>
        </AppButton>
        <input
          type="range"
          min="0"
          :max="Math.max(schedule.length - 1, 0)"
          step="1"
          :value="timeIndex"
          :aria-valuetext="timeText"
          aria-label="Time shown in the panels"
          class="min-w-0 flex-1 accent-accent pointer-coarse:h-11 max-sm:order-last max-sm:basis-1/2"
          @input="scrub"
        />
        <span class="shrink-0 text-xs text-body tabular-nums">{{ timeText }}</span>
        <span class="max-sm:order-last">
          <AppMenuButton
            :label="EARTH_VIEWS.find((view) => view.value === earthView)!.label"
            :items="EARTH_VIEWS"
            :selected="earthView"
            @select="earthView = $event"
          />
        </span>
      </div>
      <div
        class="grid gap-3"
        :class="isRegion ? 'md:grid-cols-3' : 'sm:grid-cols-2'"
      >
        <figure
          v-for="panel in panels"
          :key="panel.key"
          class="min-w-0 space-y-2 rounded-md border border-line bg-surface p-3"
        >
          <figcaption class="text-sm font-semibold text-body md:h-10">{{ panel.title }}</figcaption>
          <div class="relative aspect-square overflow-hidden rounded-md bg-space">
            <canvas
              :ref="(element) => (canvases[panel.key] = element as HTMLCanvasElement | null)"
              class="absolute inset-0 h-full w-full rounded-full"
              role="img"
              :aria-label="panel.title"
            />
            <SitePanelOverlay
              :radius-meters="areaRadiusMeters"
              :azimuth-degrees="panel.azimuthDegrees"
              :body="panel.body"
              :marker-color="panel.markerColor"
            />

            <div
              v-if="status"
              class="absolute inset-0 flex flex-col items-center justify-center gap-2 p-6 text-center text-sm text-white"
            >
              <p
                class="flex flex-col items-center gap-2"
                role="status"
              >
                <LoadingSpinner v-if="!loadError" />
                {{ status }}
              </p>
              <AppButton
                v-if="loadError"
                @click="loadArea"
                >Retry terrain</AppButton
              >
            </div>
          </div>

          <ResultSummary
            class="text-sm leading-5 text-secondary md:min-h-15"
            :label="`${panel.title} results`"
          >
            <VisibilityScale
              v-if="panel.visibility"
              class="mb-1"
              :metric="panel.body"
              fill
            />
            <p>{{ panel.caption }}</p>
          </ResultSummary>
        </figure>
        <CombinedVisibilityPanel
          v-if="isRegion"
          :study="study"
          :selection="site.selection"
          :frames="frames"
          :frame="frame"
          :detail="detail"
          :terrain="terrain"
          :sun="sun"
        />
      </div>
      <p
        v-if="!isRegion"
        class="text-sm text-secondary"
      >
        {{ jointCaption }}
      </p>
      <SolarPowerEstimate
        :sunlight="centerSunlight"
        :is-loading="Boolean(frame && frame.visibleSunFraction !== null && !detail && !detailError)"
      />
      <details class="text-xs text-secondary">
        <summary class="cursor-pointer rounded text-sm hover:text-body focus-visible:outline-2 focus-visible:outline-focus-ring">Map guide</summary>
        <div class="mt-2 space-y-2">
          <p>Maps show the same area, north up, with colors interpolated between samples.</p>
          <p>Colors show calculated visibility over the terrain. A dim inspection light keeps crater shapes visible in shadow.</p>
          <p>
            Terrain orientation shows slopes facing Earth, without a visibility calculation. Across-plan maps use fixed lighting and exclude unchecked
            times.
          </p>
        </div>
      </details>
    </section>
    <slot
      name="horizon"
      :sun="sun"
      :earth="earth"
      :directions="directions"
      :time-text="timeText"
    />
  </div>
</template>

<script setup lang="ts">
  import LoadingSpinner from "@/components/ui/LoadingSpinner.vue";
  import { Pause, Play } from "@lucide/vue";
  import { computed, onUnmounted, reactive, ref, shallowRef, watch } from "vue";
  import { frameFraction, frameResultKey, frameVisibilityGrid } from "@/views/home/visibility/visibilityView";
  import AppButton from "@/components/ui/AppButton.vue";
  import AppMenuButton from "@/components/ui/AppMenuButton.vue";
  import ResultSummary from "@/components/ui/ResultSummary.vue";
  import type { PlanSiteInterface } from "@/types/terrain/PlanAnalysisInterface";
  import type { SunlightStudyInterface } from "@/types/terrain/SunlightStudyInterface";
  import type {
    SiteDirectionsInterface,
    SiteTerrainInterface,
    BodyDirectionInterface,
    VisibilityGridInterface,
  } from "@/types/terrain/SiteTerrainInterface";
  import type { SunlightFrameDetailInterface, SunlightFrameInterface } from "@/types/terrain/SunlightFrameInterface";
  import { api } from "@/utils/api";
  import { getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { describeState, formatUtc, isFullSun } from "@/views/home/plan/planTimeline";
  import { visibilityFractionColor } from "@/views/home/viewer/sunlightOverlay";
  import { terrainNormals, terrainPixels } from "../terrainShading";
  import SitePanelOverlay from "./SitePanelOverlay.vue";
  import CombinedVisibilityPanel from "./CombinedVisibilityPanel.vue";
  import VisibilityScale from "./VisibilityScale.vue";
  import SolarPowerEstimate from "@/views/home/visibility/components/SolarPowerEstimate.vue";

  type PanelKey = "sunlight" | "earth";
  type MapMetric = "sunlight" | "earth";

  const PLAYBACK_DELAY_MS = 700;
  const DETAIL_DELAY_MS = 150;
  const POINT_AREA_RADIUS_METERS = 5000;
  const EARTH_VIEWS = [
    { label: "Earth visibility", value: "visibility" },
    { label: "Terrain orientation", value: "orientation" },
  ];

  const props = defineProps<{
    study: SunlightStudyInterface;
    site: PlanSiteInterface;
    frames: SunlightFrameInterface[];
    schedule: number[];
  }>();
  const timeIndex = defineModel<number>("timeIndex", { required: true });
  const mapSection = ref<HTMLElement>();
  const mapHeading = ref<HTMLHeadingElement>();
  const canvases = reactive<Record<PanelKey, HTMLCanvasElement | null>>({ sunlight: null, earth: null });
  const terrain = shallowRef<SiteTerrainInterface | null>(null);
  const directions = shallowRef<SiteDirectionsInterface | null>(null);
  const loadError = ref("");
  const detail = shallowRef<SunlightFrameDetailInterface | null>(null);
  const detailError = ref("");
  const isPlaying = ref(false);
  const earthView = ref("visibility");
  const isEarthOrientation = computed(() => earthView.value === "orientation");

  const isRegion = computed(() => props.site.selection.radiusMeters !== null);
  const areaRadiusMeters = computed(() => props.site.selection.radiusMeters ?? POINT_AREA_RADIUS_METERS);
  const timeText = computed(() => (props.schedule.length ? formatUtc(props.schedule[timeIndex.value]!) : ""));
  const normals = computed(() => (terrain.value ? terrainNormals(terrain.value) : null));

  function direction(body: "sun" | "earth"): BodyDirectionInterface | null {
    if (!directions.value) {
      return null;
    }

    const series = directions.value[body];

    return { azimuthDegrees: series.azimuthDegrees[timeIndex.value]!, elevationDegrees: series.elevationDegrees[timeIndex.value]! };
  }

  const sun = computed(() => direction("sun"));
  const earth = computed(() => direction("earth"));

  const siteFrames = computed(() => {
    const byTime = new Map<number, SunlightFrameInterface>();

    for (const frame of props.frames) {
      if (frame.selectionId === props.site.selection.id) {
        byTime.set(Date.parse(frame.timestamp), frame);
      }
    }

    return byTime;
  });
  const frame = computed(() => siteFrames.value.get(props.schedule[timeIndex.value]!) ?? null);
  const centerSunlight = computed(() => {
    if (!frame.value || !detail.value || frameResultKey(frame.value) !== frameResultKey(detail.value)) {
      return null;
    }

    return detail.value.result?.center ?? null;
  });

  function visibility(metric: MapMetric): VisibilityGridInterface | null {
    if (!isRegion.value) {
      return null;
    }

    return frameVisibilityGrid(frame.value, detail.value, metric);
  }

  function pointMarkerColor(metric: MapMetric) {
    const fraction = frame.value ? frameFraction(frame.value, metric) : null;

    if (isRegion.value || fraction === null) {
      return undefined;
    }

    return visibilityFractionColor(fraction, metric);
  }

  const sunlightCaption = computed(() => {
    if (detailError.value) {
      return detailError.value;
    }

    const fraction = frame.value?.visibleSunFraction;

    if (fraction === null || fraction === undefined) {
      return "Not calculated at this time.";
    }
    if (!isRegion.value) {
      return `${describeState(fraction)} at the point.`;
    }

    const grid = visibility("sunlight");

    if (!grid) {
      return "Loading the calculated map.";
    }

    const fractions = grid.fractions.filter((value) => value !== null);
    const litShare = fractions.filter(isFullSun).length / fractions.length;

    return `${Math.round(litShare * 100)}% of the area is fully lit. ${Math.round(fraction * 100)}% average visible Sun.`;
  });
  const earthCaption = computed(() => {
    if (detailError.value) {
      return detailError.value;
    }

    const fraction = frame.value?.visibleEarthFraction;

    if (fraction === null || fraction === undefined) {
      return "Not calculated at this time.";
    }

    const center = detail.value?.earthResult?.center;
    const fractionText = `${Math.round(fraction * 100)}% ${isRegion.value ? "average " : ""}visible Earth disk.`;

    if (!center) {
      return fractionText;
    }

    return `${fractionText} Center ${center.earthCenterVisible ? "visible" : "blocked"}. Elevation ${center.earthElevationDegrees.toFixed(1)}°, azimuth ${center.earthAzimuthDegrees.toFixed(1)}°.`;
  });
  const jointCaption = computed(() => {
    const fraction = frame.value?.jointVisibleShare;

    if (fraction === null || fraction === undefined) {
      return "Sun and Earth together: not calculated at this time.";
    }

    return `${Math.round(fraction * 100)}% of samples have sunlight and an unobstructed Earth-center direction.`;
  });
  const panels = computed(() => [
    {
      key: "sunlight" as const,
      title: "Sunlight and shadow",
      caption: sunlightCaption.value,
      direction: sun.value,
      visibility: visibility("sunlight"),
      sunlight: visibility("sunlight"),
      body: "sunlight" as const,
      azimuthDegrees: sun.value?.azimuthDegrees,
      markerColor: pointMarkerColor("sunlight"),
    },
    {
      key: "earth" as const,
      title: isEarthOrientation.value ? "Terrain facing Earth" : "Where Earth is visible",
      caption: isEarthOrientation.value ? "Slopes facing Earth. This shading does not show visibility." : earthCaption.value,
      direction: isEarthOrientation.value ? earth.value : sun.value,
      visibility: isEarthOrientation.value ? null : visibility("earth"),
      sunlight: isEarthOrientation.value ? null : visibility("sunlight"),
      body: "earth" as const,
      azimuthDegrees: earth.value?.azimuthDegrees,
      markerColor: isEarthOrientation.value ? undefined : pointMarkerColor("earth"),
    },
  ]);
  const status = computed(() => {
    if (loadError.value) {
      return loadError.value;
    }

    return terrain.value && directions.value ? "" : "Loading terrain";
  });

  let areaRequest = new AbortController();
  let detailRequest = new AbortController();
  let detailTimer: ReturnType<typeof setTimeout> | undefined;
  let playbackTimer: ReturnType<typeof setTimeout> | undefined;
  const detailCache = new Map<string, SunlightFrameDetailInterface>();

  async function loadArea() {
    areaRequest.abort();
    areaRequest = new AbortController();

    const request = areaRequest;

    terrain.value = null;
    directions.value = null;
    loadError.value = "";

    try {
      const [terrainResult, directionsResult] = await Promise.all([
        api.studies.siteTerrain(props.study.id, props.site.selection.id, request.signal),
        api.studies.siteDirections(props.study.id, props.site.selection.id, request.signal),
      ]);

      if (request.signal.aborted) {
        return;
      }

      terrain.value = terrainResult;
      directions.value = directionsResult;
    } catch (error) {
      if (!request.signal.aborted) {
        loadError.value = getFirstApiErrorMessage(error, "Unable to load the terrain for this site.");
      }
    }
  }

  function loadDetail() {
    clearTimeout(detailTimer);
    detailRequest.abort();
    detailError.value = "";

    const current = frame.value;

    detail.value = null;

    if (!current) {
      return;
    }

    const cached = detailCache.get(frameResultKey(current));

    if (cached) {
      detail.value = cached;
      return;
    }

    detailTimer = setTimeout(async () => {
      detailRequest = new AbortController();

      const request = detailRequest;

      try {
        const result = await api.studies.frame(props.study.id, current.id, request.signal);

        detailCache.set(frameResultKey(result), result);

        if (!request.signal.aborted) {
          detail.value = result;
        }
      } catch (error) {
        if (!request.signal.aborted) {
          detailError.value = getFirstApiErrorMessage(error, "Unable to load the full map for this time.");
        }
      }
    }, DETAIL_DELAY_MS);
  }

  function draw() {
    if (!terrain.value || !normals.value) {
      return;
    }

    const size = terrain.value.gridSize;

    for (const panel of panels.value) {
      const canvas = canvases[panel.key];

      if (!canvas || !panel.direction) {
        continue;
      }

      const pixels = terrainPixels(terrain.value, normals.value, panel.direction, panel.visibility, panel.body, panel.sunlight);

      canvas.width = size;
      canvas.height = size;
      canvas.getContext("2d")!.putImageData(new ImageData(pixels, size, size), 0, 0);
    }
  }

  function stopPlayback() {
    isPlaying.value = false;
    clearTimeout(playbackTimer);
  }

  function advance() {
    timeIndex.value = (timeIndex.value + 1) % props.schedule.length;
    playbackTimer = setTimeout(advance, PLAYBACK_DELAY_MS);
  }

  function togglePlayback() {
    if (isPlaying.value) {
      stopPlayback();
      return;
    }

    isPlaying.value = true;
    advance();
  }

  function scrub(event: Event) {
    stopPlayback();
    timeIndex.value = Number((event.target as HTMLInputElement).value);
  }

  function scrollToMaps(behavior: ScrollBehavior) {
    mapSection.value?.scrollIntoView({ behavior, block: "start" });
    mapHeading.value?.focus({ preventScroll: true });
  }

  defineExpose({ scrollToMaps });

  watch([() => props.study.id, () => props.site.selection.id, () => props.schedule[0], () => props.schedule.length], loadArea, { immediate: true });
  watch(
    () => props.study.id,
    () => detailCache.clear()
  );
  watch(() => (frame.value ? frameResultKey(frame.value) : null), loadDetail, { immediate: true });
  watch([normals, panels, () => canvases.sunlight, () => canvases.earth], draw, { flush: "post" });

  onUnmounted(() => {
    stopPlayback();
    clearTimeout(detailTimer);
    areaRequest.abort();
    detailRequest.abort();
  });
</script>
