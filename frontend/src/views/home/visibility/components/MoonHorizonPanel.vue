<template>
  <div class="space-y-2">
    <div class="flex items-center justify-between gap-3">
      <span class="text-xs text-secondary tabular-nums">{{ timeText }}</span>
      <QuietButton
        :disabled="isLoading"
        @click="load"
        >Refresh skyline</QuietButton
      >
    </div>
    <LoadingSpinner
      v-if="isLoading"
      label="Updating Sun and Earth positions…"
      class="text-sm text-secondary"
    />
    <p
      v-if="loadError"
      class="text-sm text-error"
      role="alert"
    >
      {{ loadError }}
    </p>
    <template v-if="result">
      <HorizonChart
        :horizon="result"
        :sun="result.sun"
        :earth="result.earth"
        :elevation-series="elevationSeries"
        :time-text="timeText"
        compact
      />
      <p class="text-sm text-secondary">
        {{
          result.bounds
            ? "Shading shows terrain bounds. Markers show body centers."
            : "No resolved terrain skyline is saved here. Markers use the reference horizon."
        }}
      </p>
    </template>
  </div>
</template>

<script setup lang="ts">
  import LoadingSpinner from "@/components/ui/LoadingSpinner.vue";
  import { computed, onUnmounted, ref, shallowRef, watch } from "vue";
  import QuietButton from "@/components/ui/QuietButton.vue";
  import type { LocationHorizonInterface } from "@/types/terrain/LocationHorizonInterface";
  import type { TerrainLocationInterface } from "@/types/terrain/TerrainLocationInterface";
  import { api } from "@/utils/api";
  import { getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { formatUtc } from "@/views/home/plan/planTimeline";
  import HorizonChart from "./HorizonChart.vue";

  const props = defineProps<{ datasetId: number; location: TerrainLocationInterface; timestamp: string }>();
  const result = shallowRef<LocationHorizonInterface | null>(null);
  const isLoading = ref(false);
  const loadError = ref("");
  const timeText = computed(() => formatUtc(Date.parse(result.value?.timestamp ?? props.timestamp)));
  const elevationSeries = computed(() => (result.value ? [[result.value.sun.elevationDegrees], [result.value.earth.elevationDegrees]] : []));
  let request = new AbortController();

  async function load() {
    request.abort();
    request = new AbortController();

    const current = request;
    const previous = result.value;

    if (
      previous &&
      (previous.datasetId !== props.datasetId || previous.latitude !== props.location.latitude || previous.longitude !== props.location.longitude)
    ) {
      result.value = null;
    }

    isLoading.value = true;
    loadError.value = "";

    try {
      const horizon = await api.terrain.horizon(props.datasetId, props.location, props.timestamp, current.signal);

      if (!current.signal.aborted) {
        result.value = horizon;
      }
    } catch (error) {
      if (!current.signal.aborted) {
        loadError.value = getFirstApiErrorMessage(error, "Unable to load the horizon at this location.");
      }
    } finally {
      if (request === current) {
        isLoading.value = false;
      }
    }
  }

  watch([() => props.datasetId, () => props.location.latitude, () => props.location.longitude, () => props.timestamp], load, { immediate: true });
  onUnmounted(() => request.abort());
</script>
