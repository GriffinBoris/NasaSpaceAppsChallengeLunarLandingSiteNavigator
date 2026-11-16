<template>
  <section
    class="space-y-3 rounded-md border border-line bg-surface p-3"
    aria-label="Horizon at the site center"
  >
    <div class="flex items-start justify-between gap-3">
      <div class="space-y-1">
        <h2 class="text-lg font-semibold text-body">Horizon at the site center</h2>
        <p class="text-xs text-secondary">{{ timeText }}</p>
      </div>
      <AppButton
        v-if="!horizon?.bounds"
        :loading="isLoading"
        @click="load"
        >Refresh skyline</AppButton
      >
    </div>
    <p
      v-if="loadError"
      class="text-sm text-error"
      role="alert"
    >
      {{ loadError }}
    </p>
    <LoadingSpinner
      v-else-if="isLoading"
      label="Loading the saved terrain skyline…"
      class="text-sm text-secondary"
    />
    <p
      v-else-if="!horizon?.bounds"
      class="text-sm text-secondary"
    >
      Terrain skyline unavailable. Markers use the reference horizon.
    </p>
    <HorizonChart
      :horizon="horizon"
      :sun="sun"
      :earth="earth"
      :elevation-series="elevationSeries"
      :time-text="timeText"
    />
    <p class="text-xs text-secondary">Markers show the Sun and Earth centers.</p>
  </section>
</template>

<script setup lang="ts">
  import LoadingSpinner from "@/components/ui/LoadingSpinner.vue";
  import { computed, onUnmounted, ref, shallowRef, watch } from "vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import HorizonChart from "@/views/home/visibility/components/HorizonChart.vue";
  import type { SiteHorizonInterface } from "@/types/terrain/SiteHorizonInterface";
  import type { BodyDirectionInterface, SiteDirectionsInterface } from "@/types/terrain/SiteTerrainInterface";
  import { api } from "@/utils/api";
  import { getFirstApiErrorMessage } from "@/utils/errorHandling";

  const props = defineProps<{
    studyId: number;
    selectionId: number;
    resultRevision: number;
    sun: BodyDirectionInterface | null;
    earth: BodyDirectionInterface | null;
    directions: SiteDirectionsInterface | null;
    timeText: string;
  }>();
  const horizon = shallowRef<SiteHorizonInterface | null>(null);
  const isLoading = ref(false);
  const loadError = ref("");
  const elevationSeries = computed(() => (props.directions ? [props.directions.sun.elevationDegrees, props.directions.earth.elevationDegrees] : []));
  let request = new AbortController();

  async function load() {
    request.abort();
    request = new AbortController();

    const current = request;

    horizon.value = null;
    isLoading.value = true;
    loadError.value = "";

    try {
      const result = await api.studies.siteHorizon(props.studyId, props.selectionId, current.signal);

      if (!current.signal.aborted) {
        horizon.value = result;
      }
    } catch (error) {
      if (!current.signal.aborted) {
        loadError.value = getFirstApiErrorMessage(error, "Unable to load the saved terrain skyline.");
      }
    } finally {
      if (request === current) {
        isLoading.value = false;
      }
    }
  }

  watch([() => props.studyId, () => props.selectionId], load, { immediate: true });
  watch(
    () => props.resultRevision,
    () => {
      if (!horizon.value?.bounds && !isLoading.value) {
        void load();
      }
    }
  );
  onUnmounted(() => request.abort());
</script>
