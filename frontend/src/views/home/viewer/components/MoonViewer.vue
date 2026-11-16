<template>
  <section
    class="overflow-hidden bg-space"
    aria-label="Moon explorer"
  >
    <div
      ref="viewport"
      class="absolute inset-0 cursor-grab active:cursor-grabbing [&>canvas]:outline-none"
      @focusin="trackCanvasFocus"
      @focusout="isCanvasFocused = false"
    />
    <div
      v-if="isCanvasFocused"
      class="pointer-events-none absolute inset-0 flex items-center justify-center ring-2 ring-focus-ring ring-inset"
      aria-hidden="true"
    >
      <span class="size-6 rounded-full border-2 border-white/80 shadow-[0_0_0_1px_black]" />
    </div>
    <div
      ref="controlsPanel"
      class="absolute top-3 left-3 z-10 flex max-w-[calc(100%-1.5rem)] flex-col items-start gap-2"
    >
      <div class="flex max-w-full flex-wrap gap-2">
        <AppMenuButton
          label="View"
          :items="viewItems"
          :disabled="!isReady"
          @select="changeView"
        />
        <AppMenuButton
          label="Layers"
          :items="layerItems"
          :selected="displayMode"
          :disabled="!isReady"
          @select="displayMode = $event as TerrainDisplayMode"
        />
        <AppButton
          square
          aria-label="Feature names"
          title="Feature names: show or hide crater and mare labels"
          :aria-pressed="showFeatureNames"
          :disabled="!isReady"
          :class="showFeatureNames ? 'border-accent bg-surface-muted' : ''"
          @click="showFeatureNames = !showFeatureNames"
        >
          <Tags aria-hidden="true" />
        </AppButton>
        <AppButton
          square
          aria-label="Full lighting"
          title="Full lighting: light all terrain for inspection. Sunlight calculations still use the selected UTC time."
          :aria-pressed="isFullyIlluminated"
          :disabled="!isReady"
          :class="isFullyIlluminated ? 'border-accent bg-surface-muted' : ''"
          @click="isFullyIlluminated = !isFullyIlluminated"
        >
          <Lightbulb aria-hidden="true" />
        </AppButton>
        <AppButton
          square
          aria-label="Zoom out"
          title="Zoom out"
          :disabled="!isReady"
          @click="zoom(ZOOM_OUT_FACTOR)"
        >
          <Minus aria-hidden="true" />
        </AppButton>
        <AppButton
          square
          aria-label="Zoom in"
          title="Zoom in"
          :disabled="!isReady"
          @click="zoom(ZOOM_IN_FACTOR)"
        >
          <Plus aria-hidden="true" />
        </AppButton>
        <AppButton
          v-if="!hasCard"
          square
          aria-label="Getting started"
          title="Getting started"
          @click="emit('help')"
        >
          <CircleHelp aria-hidden="true" />
        </AppButton>
      </div>
      <label
        v-if="isFullyIlluminated"
        class="block w-52 max-w-full space-y-1 rounded-md bg-surface shadow-md px-3 py-2 text-xs text-secondary"
      >
        <span class="flex items-center justify-between gap-3">
          <span>Brightness</span>
          <span class="font-mono tabular-nums">{{ fullLightingBrightness }}%</span>
        </span>
        <input
          v-model.number="fullLightingBrightness"
          type="range"
          min="0"
          max="100"
          step="1"
          aria-label="Full lighting brightness"
          :aria-valuetext="`${fullLightingBrightness}%`"
          :disabled="!isReady"
          class="block w-full accent-accent"
        />
      </label>
      <div
        v-if="displayMode === 'elevation'"
        class="w-36 space-y-1 rounded-md bg-surface shadow-md px-3 py-2 text-xs text-secondary"
        role="group"
        aria-label="Elevation relative to the lunar reference sphere"
        :class="{ 'max-sm:hidden': hasCard }"
      >
        <div
          class="h-1.5 rounded"
          :style="{ background: ELEVATION_SCALE.gradient }"
          aria-hidden="true"
        />
        <div class="flex justify-between">
          <span>{{ ELEVATION_SCALE.minimum / 1000 }} km</span>
          <span>+{{ ELEVATION_SCALE.maximum / 1000 }} km</span>
        </div>
      </div>
      <div
        v-if="showSunlightOverlay && sunlightPatch"
        class="space-y-1 rounded-md bg-surface shadow-md px-3 py-2 text-xs text-secondary"
        role="group"
        aria-label="Visibility map legend"
        :class="{ 'max-sm:hidden': hasCard }"
      >
        <p class="flex flex-wrap gap-3 text-body">
          <span
            v-for="item in legendItems"
            :key="item.label"
            class="flex items-center gap-1.5"
          >
            <span
              class="h-2 w-2.5 rounded-sm"
              :style="{ background: item.color }"
              aria-hidden="true"
            />
            {{ item.label }}
          </span>
        </p>
        <p>{{ sunlightPatch.radiusMeters / 1000 }} km radius, {{ Math.round(sunlightPatch.spacingMeters) }} m between samples</p>
      </div>
      <p
        v-if="isNightSide && !isFullyIlluminated && isReady"
        class="max-w-64 space-y-1 rounded-md bg-surface px-3 py-2 text-xs text-secondary shadow-md"
        :class="{ 'max-sm:hidden': hasCard }"
      >
        <span class="block">This side of the Moon is in darkness at the selected time.</span>
        <QuietButton
          class="-ml-2"
          @click="isFullyIlluminated = true"
          >Turn on full lighting</QuietButton
        >
      </p>
      <AlertBanner
        v-if="timeError"
        :message="timeError"
        class="max-w-sm"
      />
    </div>
    <FeatureLabels
      v-if="showFeatureNames"
      ref="featureLabels"
      :get-view="featureLabelView"
      :reserved-bounds="reservedLabelBounds"
      @pick="emit('feature', $event)"
    />
    <SiteMarkers
      ref="siteMarkers"
      :project="projectLocation"
    />
    <div
      ref="statusPanel"
      class="pointer-events-none absolute bottom-3 left-3 space-y-0.5 text-xs text-white/85 [text-shadow:0_1px_3px_black]"
      :class="{ 'max-sm:hidden': hasCard }"
    >
      <LoadingSpinner
        v-if="terrainDetail?.isLoading"
        label="Loading finer terrain detail…"
        class="flex"
      />
      <p v-if="isCanvasFocused">Arrow keys rotate (Shift for larger steps). Plus and minus zoom. Enter selects the center.</p>
    </div>
    <p
      class="sr-only"
      aria-live="polite"
    >
      {{ selectionAnnouncement }}
    </p>
    <div
      v-if="isLoading"
      class="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-white"
    >
      <LoadingSpinner
        size="large"
        label="Loading lunar terrain"
        class="flex-col gap-3"
      />
    </div>
    <div
      v-if="errorMessage"
      class="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6"
    >
      <AlertBanner :message="errorMessage" />
      <AppButton @click="reloadPage">Reload</AppButton>
    </div>
    <p
      v-if="hasDetailError"
      class="absolute right-3 bottom-3 rounded-md bg-surface shadow-md px-3 py-1.5 text-xs text-secondary"
      role="status"
    >
      Unable to load finer terrain. Move the view to retry.
    </p>
  </section>
</template>

<script setup lang="ts">
  import LoadingSpinner from "@/components/ui/LoadingSpinner.vue";
  import { CircleHelp, Lightbulb, Minus, Plus, Tags } from "@lucide/vue";
  import { computed, onMounted, onUnmounted, ref, watch } from "vue";
  import AlertBanner from "@/components/ui/AlertBanner.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import AppMenuButton from "@/components/ui/AppMenuButton.vue";
  import QuietButton from "@/components/ui/QuietButton.vue";
  import type { TerrainDetailInterface } from "@/types/terrain/TerrainDetailInterface";
  import type { TerrainLocationInterface } from "@/types/terrain/TerrainLocationInterface";
  import type { TerrainDisplayMode } from "@/types/terrain/TerrainDisplayMode";
  import { patchMetric } from "@/views/home/visibility/visibilityView";
  import type { VisibilityPatchInterface } from "@/types/terrain/VisibilityInterface";
  import type { IlluminationPatchInterface } from "@/types/terrain/IlluminationPatchInterface";
  import type { TerrainDatasetInterface } from "@/types/terrain/TerrainDatasetInterface";
  import type { EphemerisInterface } from "@/types/ephemeris/EphemerisInterface";
  import type { LunarFeatureInterface } from "@/types/terrain/LunarFeatureInterface";
  import { api } from "@/utils/api";
  import { getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { ELEVATION_SCALE } from "@/views/home/viewer/elevationColors";
  import { useSunlightStore } from "@/views/home/sunlightStore";
  import { MoonScene, ZOOM_IN_FACTOR, ZOOM_OUT_FACTOR } from "@/views/home/viewer/moonScene";
  import { formatCoordinates } from "@/views/home/sites/coordinateFormat";
  import { EARTH_VISIBILITY_COLORS, SUNLIGHT_COLORS, VISIBLE_COLORS, visibilityFractionColor } from "@/views/home/viewer/sunlightOverlay";
  import SiteMarkers from "./SiteMarkers.vue";
  import FeatureLabels from "./FeatureLabels.vue";

  const VIEW_ITEMS = [
    { label: "Full Moon", value: "globe" },
    { label: "South pole", value: "south-pole" },
    { label: "Selected location", value: "selected" },
    { label: "From Earth", value: "earth" },
    { label: "From the Sun", value: "sun" },
  ];

  const location = defineModel<TerrainLocationInterface>("location", { required: true });
  const radiusKm = defineModel<number>("radiusKm", { required: true });

  const props = defineProps<{ hasSelection: boolean; hasCard: boolean; labelBounds: () => DOMRect[] }>();
  const emit = defineEmits<{
    ready: [datasetId: number];
    time: [timestamp: string];
    pick: [];
    feature: [feature: LunarFeatureInterface];
    help: [];
  }>();
  const store = useSunlightStore();
  const viewport = ref<HTMLDivElement>();
  const isLoading = ref(true);
  const isReady = ref(false);
  const errorMessage = ref("");
  const hasDetailError = ref(false);
  const displayMode = ref<TerrainDisplayMode>("terrain");
  const isFullyIlluminated = ref(false);
  const isCanvasFocused = ref(false);
  const isNightSide = ref(false);
  const selectionAnnouncement = ref("");
  const fullLightingBrightness = ref(25);
  const sunlightPatch = ref<VisibilityPatchInterface | null>(null);
  const visibleMetric = computed(() => (sunlightPatch.value ? patchMetric(sunlightPatch.value) : "sunlight"));
  const visibleLabel = computed(() => ({ sunlight: "Sunlight", earth: "Earth visible", joint: "Sun and Earth" })[visibleMetric.value]);
  const blockedLabel = computed(() => ({ sunlight: "Shadow", earth: "Obstructed", joint: "Sun or Earth hidden" })[visibleMetric.value]);
  const layerItems = computed<{ label: string; value: TerrainDisplayMode }[]>(() => [
    { label: "Terrain", value: "terrain" },
    { label: "Elevation", value: "elevation" },
    { label: "Visibility map", value: "illumination" },
    { label: `${visibleLabel.value} only`, value: "sunlight" },
    { label: `${blockedLabel.value} only`, value: "shadow" },
  ]);
  const viewItems = computed(() => VIEW_ITEMS.filter((item) => item.value !== "selected" || props.hasSelection));
  const showSunlightOverlay = computed(() => displayMode.value !== "terrain" && displayMode.value !== "elevation");
  const terrainDetail = ref<TerrainDetailInterface | null>(null);
  const siteMarkers = ref<InstanceType<typeof SiteMarkers>>();
  const featureLabels = ref<InstanceType<typeof FeatureLabels>>();
  const controlsPanel = ref<HTMLDivElement>();
  const statusPanel = ref<HTMLDivElement>();
  const labelObstacles = new ResizeObserver(() => featureLabels.value?.update());
  const showFeatureNames = ref(true);
  const appliedTime = ref("");
  const timeError = ref("");
  const legendItems = computed(() => {
    const items = [
      { label: visibleLabel.value, color: VISIBLE_COLORS[visibleMetric.value], modes: ["illumination", "sunlight"] },
      {
        label: "Partial",
        color: visibilityFractionColor(0.5, visibleMetric.value),
        modes: ["illumination"],
      },
      {
        label: blockedLabel.value,
        color: visibleMetric.value === "earth" ? EARTH_VISIBILITY_COLORS.blocked : SUNLIGHT_COLORS.shadow,
        modes: ["illumination", "shadow"],
      },
    ];

    return items.filter((item) => item.modes.includes(displayMode.value));
  });

  let scene: MoonScene | undefined;
  let isDisposed = false;
  let ephemerisRequest = new AbortController();

  function projectLocation(location: TerrainLocationInterface) {
    return scene?.screenPosition(location) ?? null;
  }

  function featureLabelView() {
    return scene?.featureLabelView() ?? null;
  }

  function reservedLabelBounds(): DOMRect[] {
    const bounds = [...props.labelBounds(), ...(siteMarkers.value?.bounds() ?? [])];

    for (const panel of [controlsPanel.value, statusPanel.value]) {
      if (panel) {
        bounds.push(panel.getBoundingClientRect());
      }
    }

    return bounds;
  }

  function updateMarkers() {
    isNightSide.value = scene?.facesNightSide() ?? false;
    siteMarkers.value?.update();
    featureLabels.value?.update();
  }

  async function applyTime(timestamp: string) {
    ephemerisRequest.abort();
    ephemerisRequest = new AbortController();

    const request = ephemerisRequest;

    timeError.value = "";

    try {
      const ephemeris = await api.ephemeris.detail(timestamp, request.signal);

      if (isDisposed || request.signal.aborted) {
        return;
      }

      scene?.setEphemeris(ephemeris);
      appliedTime.value = ephemeris.timestamp;
    } catch (error) {
      if (!isDisposed && !request.signal.aborted) {
        timeError.value = getFirstApiErrorMessage(error, "Unable to update the Sun and Earth positions.");
      }
    }
  }

  function showPatch(patch: VisibilityPatchInterface | null, sunlight: IlluminationPatchInterface | null = null) {
    sunlightPatch.value = patch;
    scene?.setSunlightPatch(patch, sunlight);

    if (patch && !showSunlightOverlay.value) {
      displayMode.value = "illumination";
    }
  }

  function changeView(view: string) {
    switch (view) {
      case "globe":
        scene?.reset();
        break;
      case "south-pole":
        scene?.focusSouthPole();
        break;
      case "selected":
        scene?.focusLocation(location.value, radiusKm.value * 1000);
        break;
      case "earth":
      case "sun":
        scene?.focusBody(view);
        break;
    }
  }

  function zoom(factor: number) {
    scene?.zoom(factor);
  }

  async function loadScene(dataset: TerrainDatasetInterface, ephemeris: EphemerisInterface, signal: AbortSignal) {
    if (!viewport.value) {
      return;
    }

    const nextScene = new MoonScene(
      viewport.value,
      dataset,
      (tile, signal) => api.terrain.tile(dataset, tile, signal),
      (hasError) => {
        hasDetailError.value = hasError;
      },
      (detail) => {
        terrainDetail.value = detail;
      },
      (pickedLocation) => {
        location.value = pickedLocation;
        selectionAnnouncement.value = `Selected ${formatCoordinates(pickedLocation.latitude, pickedLocation.longitude)}`;
        emit("pick");
      },
      updateMarkers
    );

    try {
      nextScene.setEphemeris(ephemeris);
      await nextScene.initialize();

      if (isDisposed || signal.aborted) {
        nextScene.dispose();
        return;
      }

      scene?.dispose();
      scene = nextScene;
      scene.setSelectedLocation(location.value, radiusKm.value * 1000);
      scene.setDisplayMode(displayMode.value);
      scene.setFullIllumination(isFullyIlluminated.value, fullLightingBrightness.value);
      isReady.value = true;
      emit("ready", dataset.id);
      updateMarkers();
    } catch (error) {
      nextScene.dispose();
      throw error;
    }
  }

  watch(displayMode, (mode) => scene?.setDisplayMode(mode));
  watch([isFullyIlluminated, fullLightingBrightness], ([enabled, brightness]) => scene?.setFullIllumination(enabled, brightness));

  watch(appliedTime, (timestamp) => emit("time", timestamp));

  watch(
    () => store.focusedSelectionId,
    () => {
      const selection = store.focusedSelection;

      if (!selection) {
        return;
      }

      location.value = { latitude: selection.latitude, longitude: selection.longitude };
      radiusKm.value = (selection.radiusMeters ?? 0) / 1000;
      scene?.focusLocation(selection, selection.radiusMeters ?? 0);
    }
  );

  watch(
    () => [location.value.latitude, location.value.longitude, radiusKm.value],
    () => scene?.setSelectedLocation(location.value, radiusKm.value * 1000)
  );

  function reloadPage() {
    window.location.reload();
  }

  onMounted(async () => {
    labelObstacles.observe(controlsPanel.value!);
    labelObstacles.observe(statusPanel.value!);

    try {
      const timestamp = `${new Date().toISOString().slice(0, 16)}:00Z`;
      const [dataset, ephemeris] = await Promise.all([api.terrain.detail(), api.ephemeris.detail(timestamp, ephemerisRequest.signal)]);

      if (isDisposed || !viewport.value) {
        return;
      }

      appliedTime.value = ephemeris.timestamp;
      await loadScene(dataset, ephemeris, ephemerisRequest.signal);
    } catch (error) {
      if (isDisposed) {
        return;
      }

      scene?.dispose();
      scene = undefined;
      terrainDetail.value = null;
      errorMessage.value = getFirstApiErrorMessage(error, "Moon terrain is unavailable right now.");
    } finally {
      isLoading.value = false;
    }
  });

  onUnmounted(() => {
    isDisposed = true;
    labelObstacles.disconnect();
    ephemerisRequest.abort();
    scene?.dispose();
  });

  function focusLocation(target: TerrainLocationInterface, radiusMeters: number) {
    scene?.focusLocation(target, radiusMeters);
  }

  function refreshLabels() {
    featureLabels.value?.update();
  }

  function trackCanvasFocus(event: FocusEvent) {
    isCanvasFocused.value = event.target instanceof HTMLCanvasElement && event.target.matches(":focus-visible");
  }

  function focus() {
    viewport.value?.querySelector("canvas")?.focus();
  }

  defineExpose({ applyTime, showPatch, focusLocation, refreshLabels, focus });
</script>
