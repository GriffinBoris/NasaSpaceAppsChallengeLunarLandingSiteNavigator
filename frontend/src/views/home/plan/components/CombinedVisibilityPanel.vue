<template>
  <figure class="min-w-0 space-y-2 rounded-md border border-line bg-surface p-3">
    <figcaption class="flex items-start justify-between gap-2 text-sm font-semibold text-body md:h-10">
      <span class="min-w-0">Sun and Earth</span>
      <AppMenuButton
        :label="mode === 'time' ? 'Selected time' : 'Across plan'"
        :items="MODE_OPTIONS"
        :selected="mode"
        @select="mode = $event"
      />
    </figcaption>
    <div class="relative aspect-square overflow-hidden rounded-md bg-space">
      <canvas
        ref="canvas"
        class="absolute inset-0 h-full w-full rounded-full"
        role="img"
        aria-label="Sunlight and Earth together"
      />
      <SitePanelOverlay
        :radius-meters="selection.radiusMeters!"
        body="sunlight"
      />
      <svg
        v-if="bestSample && !status"
        viewBox="0 0 100 100"
        class="pointer-events-none absolute inset-0 h-full w-full"
        aria-hidden="true"
      >
        <circle
          :cx="bestSample.x"
          :cy="bestSample.y"
          r="3"
          fill="none"
          stroke="black"
          stroke-width="1.5"
        />
        <circle
          :cx="bestSample.x"
          :cy="bestSample.y"
          r="3"
          fill="none"
          stroke="white"
          stroke-width="0.7"
        />
      </svg>
      <p
        v-if="status"
        class="absolute inset-0 flex flex-col items-center justify-center gap-2 p-6 text-center text-sm text-white"
        role="status"
      >
        <LoadingSpinner v-if="isStatusLoading" />
        {{ status }}
      </p>
    </div>

    <ResultSummary
      class="text-sm leading-5 md:min-h-15"
      label="Combined visibility results"
    >
      <VisibilityScale
        class="mb-1"
        metric="joint"
        fill
        :labels="mode === 'time' ? undefined : ['Never', 'Always']"
      />
      <p class="text-secondary">{{ caption }}</p>
      <p
        v-if="mode === 'plan' && bestSample && !status"
        class="text-body"
      >
        Best sample: {{ percentage(bestSample.fraction) }} of checked time at
        <span class="font-mono">{{ formatCoordinates(bestSample.latitude, bestSample.longitude, 3) }}</span
        >.
        <template v-if="bestSample.matchingSamples > 1">{{ bestSample.matchingSamples }} tied samples.</template>
      </p>
      <p
        v-if="combined && mode === 'plan'"
        class="text-secondary"
      >
        {{ formatOptimalDuration(combined.checkedSeconds * 1000) }}
        <template v-if="combined.checkedSeconds < combined.totalSeconds">of {{ formatOptimalDuration(combined.totalSeconds * 1000) }}</template>
        checked.
        <LoadingSpinner
          v-if="isLoading"
          label="Updating saved results…"
          class="ml-1 align-middle"
        />
      </p>
      <div
        v-if="loadError"
        class="space-y-2"
      >
        <p
          class="text-error"
          role="alert"
        >
          {{ loadError }}
        </p>
        <AppButton @click="load">Retry combined map</AppButton>
      </div>
    </ResultSummary>
  </figure>
</template>

<script setup lang="ts">
  import LoadingSpinner from "@/components/ui/LoadingSpinner.vue";
  import { computed, onUnmounted, ref, shallowRef, watch } from "vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import AppMenuButton from "@/components/ui/AppMenuButton.vue";
  import ResultSummary from "@/components/ui/ResultSummary.vue";
  import type { SiteCombinedVisibilityInterface } from "@/types/terrain/SiteCombinedVisibilityInterface";
  import type { BodyDirectionInterface, SiteTerrainInterface, VisibilityGridInterface } from "@/types/terrain/SiteTerrainInterface";
  import type { SunlightFrameDetailInterface, SunlightFrameInterface } from "@/types/terrain/SunlightFrameInterface";
  import type { SunlightSelectionSnapshotInterface } from "@/types/terrain/SunlightSelectionInterface";
  import type { SunlightStudyInterface } from "@/types/terrain/SunlightStudyInterface";
  import { api } from "@/utils/api";
  import { getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { formatCoordinates } from "@/views/home/sites/coordinateFormat";
  import { frameResultKey, frameVisibilityGrid } from "@/views/home/visibility/visibilityView";
  import { bestCombinedSample, combinedPlanGrid, mergeCombinedVisibility } from "../combinedVisibility";
  import { formatOptimalDuration } from "../optimalTimes";
  import { terrainNormals, terrainPixels } from "../terrainShading";
  import SitePanelOverlay from "./SitePanelOverlay.vue";
  import VisibilityScale from "./VisibilityScale.vue";

  const MODE_OPTIONS = [
    { label: "Selected time", value: "time" },
    { label: "Across plan", value: "plan" },
  ];
  const INSPECTION_DIRECTION = { azimuthDegrees: 0, elevationDegrees: 90 };

  const props = defineProps<{
    study: SunlightStudyInterface;
    selection: SunlightSelectionSnapshotInterface;
    frames: SunlightFrameInterface[];
    frame: SunlightFrameInterface | null;
    detail: SunlightFrameDetailInterface | null;
    terrain: SiteTerrainInterface | null;
    sun: BodyDirectionInterface | null;
  }>();

  const mode = ref("time");
  const canvas = ref<HTMLCanvasElement>();
  const combined = shallowRef<SiteCombinedVisibilityInterface | null>(null);
  const isLoading = ref(false);
  const loadError = ref("");
  const resourceKey = computed(() =>
    [props.study.id, props.selection.id, props.study.startTime, props.study.endTime, props.study.stepSeconds].join(":")
  );
  const sourceKey = computed(() => {
    const frameKeys = [];

    for (const frame of props.frames) {
      if (frame.selectionId !== props.selection.id || frame.jointVisibleShare === null) {
        continue;
      }

      frameKeys.push(frameResultKey(frame));
    }

    return frameKeys.join(";");
  });

  const normals = computed(() => {
    if (!props.terrain) {
      return null;
    }

    return terrainNormals(props.terrain);
  });

  const previews = computed(() => {
    const previewsByFrameId = new Map<number, VisibilityGridInterface>();

    if (combined.value) {
      for (const preview of combined.value.previews) {
        previewsByFrameId.set(preview.frameId, preview);
      }
    }

    return previewsByFrameId;
  });

  const planGrid = computed(() => (combined.value ? combinedPlanGrid(combined.value) : null));
  const selectedGrid = computed(() => {
    if (!props.frame || props.frame.jointVisibleShare === null) {
      return null;
    }

    return frameVisibilityGrid(props.frame, props.detail, "joint") ?? previews.value.get(props.frame.id) ?? null;
  });
  const grid = computed(() => (mode.value === "time" ? selectedGrid.value : planGrid.value));
  const direction = computed(() => (mode.value === "time" ? props.sun : INSPECTION_DIRECTION));
  const sunlight = computed(() => (mode.value === "time" ? frameVisibilityGrid(props.frame, props.detail, "sunlight") : null));
  const bestSample = computed(() =>
    mode.value === "plan" && grid.value && combined.value?.grid ? bestCombinedSample(grid.value, combined.value.grid) : null
  );

  const isStatusLoading = computed(() => !props.terrain || !direction.value || (!grid.value && !loadError.value && isLoading.value));
  const status = computed(() => {
    if (!props.terrain || !direction.value) {
      return "Loading terrain";
    }
    if (grid.value) {
      return "";
    }
    if (loadError.value) {
      return "Combined map unavailable";
    }
    if (isLoading.value) {
      return "Reading saved results";
    }

    return mode.value === "time" ? "Both results are needed at this time" : "No paired results saved yet";
  });
  const caption = computed(() => {
    if (!grid.value) {
      return status.value;
    }

    if (mode.value === "time") {
      return `${percentage(props.frame!.jointVisibleShare!)} of the area has both.`;
    }

    return "Time with both Sun and Earth.";
  });

  let controller: AbortController | null = null;

  function percentage(fraction: number) {
    return `${Math.round(fraction * 100)}%`;
  }

  async function load() {
    if (isLoading.value) {
      return;
    }

    const request = new AbortController();
    const requestedSource = sourceKey.value;

    controller = request;
    isLoading.value = true;
    loadError.value = "";

    try {
      const result = await api.studies.siteCombinedVisibility(props.study.id, props.selection.id, request.signal, combined.value?.resultRevision);

      if (!request.signal.aborted) {
        combined.value = mergeCombinedVisibility(combined.value, result);
      }
    } catch (error) {
      if (!request.signal.aborted) {
        loadError.value = getFirstApiErrorMessage(error, "Unable to read the saved combined maps.");
      }
    } finally {
      if (controller === request) {
        isLoading.value = false;

        if (!loadError.value && requestedSource !== sourceKey.value) {
          void load();
        }
      }
    }
  }

  function reset() {
    controller?.abort();
    controller = null;
    isLoading.value = false;
    combined.value = null;
    loadError.value = "";
    void load();
  }

  function draw() {
    const element = canvas.value;

    if (!element || !props.terrain || !normals.value || !direction.value) {
      return;
    }

    const size = props.terrain.gridSize;
    const pixels = terrainPixels(props.terrain, normals.value, direction.value, grid.value, "joint", sunlight.value);

    element.width = size;
    element.height = size;
    element.getContext("2d")!.putImageData(new ImageData(pixels, size, size), 0, 0);
  }

  watch(resourceKey, reset, { immediate: true });
  watch(sourceKey, () => void load());
  watch([canvas, normals, direction, grid, sunlight], draw, { flush: "post" });
  onUnmounted(() => {
    controller?.abort();
    controller = null;
  });
</script>
