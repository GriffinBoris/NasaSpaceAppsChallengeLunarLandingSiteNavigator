<template>
  <div class="space-y-3">
    <AppTabs :tabs="TABS">
      <template #now>
        <div class="space-y-3">
          <dl
            v-if="readouts"
            class="grid grid-cols-2 gap-2"
            role="status"
          >
            <StatTile
              v-for="readout in readouts"
              :key="readout.label"
              v-bind="readout"
              size="large"
            />
          </dl>
          <div
            v-if="mapPatch"
            class="flex flex-wrap items-center justify-between gap-2"
          >
            <span
              class="text-xs text-secondary"
              aria-hidden="true"
              >Map on the Moon</span
            >
            <div
              class="flex rounded-md border border-control-border p-0.5"
              role="group"
              aria-label="Map on the Moon"
            >
              <button
                v-for="option in MAP_OPTIONS"
                :key="option.value"
                type="button"
                class="rounded px-3 py-1 text-sm focus-visible:outline-2 focus-visible:outline-focus-ring pointer-coarse:min-h-11"
                :class="
                  mapMetric === option.value
                    ? 'bg-surface-muted font-medium text-body active:bg-line'
                    : 'text-secondary hover:text-body active:bg-line'
                "
                :aria-pressed="mapMetric === option.value"
                @click="mapMetric = option.value"
              >
                {{ option.label }}
              </button>
            </div>
          </div>

          <p
            v-if="!sunlightResult && !errorMessage"
            class="text-sm text-secondary"
          >
            {{ calculateHint }}
          </p>
          <p
            v-if="isCalculating"
            class="sr-only"
            role="status"
          >
            Calculating sunlight and Earth visibility…
          </p>
          <p
            v-if="errorMessage"
            class="text-sm text-error"
            role="alert"
          >
            {{ errorMessage }}
          </p>
          <div class="flex gap-2">
            <AppButton
              :class="sunlightResult ? '' : 'flex-1'"
              :tone="sunlightResult ? 'secondary' : 'primary'"
              :loading="isCalculating"
              :disabled="datasetId === null || !timestamp"
              @click="calculate"
            >
              {{ calculateLabel }}
            </AppButton>
            <AppButton
              v-if="isCalculating"
              @click="clear"
              >Cancel</AppButton
            >
          </div>
        </div>
      </template>
      <template #power>
        <SolarPowerEstimate
          v-if="sunlightResult"
          :sunlight="sunlightResult.center"
          :framed="false"
        />
        <div
          v-else
          class="space-y-3"
        >
          <p
            v-if="!errorMessage"
            class="text-sm text-secondary"
          >
            {{ calculateHint }}
          </p>
          <p
            v-if="isCalculating"
            class="sr-only"
            role="status"
          >
            Calculating power estimate…
          </p>
          <p
            v-if="errorMessage"
            class="text-sm text-error"
            role="alert"
          >
            {{ errorMessage }}
          </p>
          <div class="flex gap-2">
            <AppButton
              class="flex-1"
              tone="primary"
              :loading="isCalculating"
              :disabled="datasetId === null || !timestamp"
              @click="calculate"
              >{{ isCalculating ? buttonProgress : "Calculate power estimate" }}</AppButton
            >
            <AppButton
              v-if="isCalculating"
              @click="clear"
              >Cancel</AppButton
            >
          </div>
        </div>
      </template>
      <template #horizon>
        <MoonHorizonPanel
          v-if="datasetId !== null && timestamp"
          :dataset-id="datasetId"
          :location="location"
          :timestamp="timestamp"
        />
      </template>
    </AppTabs>

    <div
      v-if="$slots.actions"
      class="sticky -bottom-4 -mx-4 -mb-4 flex flex-wrap gap-2 rounded-b-xl border-t border-line bg-surface px-4 py-3 shadow-[0_-12px_12px_-8px_rgb(0_0_0/0.5)] [&_button]:flex-auto [&_button]:whitespace-nowrap"
    >
      <slot
        name="actions"
        :has-result="Boolean(sunlightResult)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch } from "vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import AppTabs from "@/components/ui/AppTabs.vue";
  import MoonHorizonPanel from "./MoonHorizonPanel.vue";
  import SolarPowerEstimate from "./SolarPowerEstimate.vue";
  import type { EarthVisibilityInterface, EarthVisibilityPatchInterface } from "@/types/terrain/EarthVisibilityInterface";
  import type { IlluminationInterface } from "@/types/terrain/IlluminationInterface";
  import type { IlluminationPatchInterface } from "@/types/terrain/IlluminationPatchInterface";
  import type { TerrainLocationInterface } from "@/types/terrain/TerrainLocationInterface";
  import type { VisibilityMetric, VisibilityPatchInterface } from "@/types/terrain/VisibilityInterface";
  import { api } from "@/utils/api";
  import { getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { sunlightLabel } from "@/views/home/plan/planTimeline";
  import StatTile from "@/components/ui/StatTile.vue";
  import { jointPatch, patchFraction } from "@/views/home/visibility/visibilityView";

  const MAP_OPTIONS: { value: VisibilityMetric; label: string }[] = [
    { value: "sunlight", label: "Sun" },
    { value: "earth", label: "Earth" },
    { value: "joint", label: "Both" },
  ];
  const TABS = [
    { value: "now", label: "Selected time" },
    { value: "power", label: "Power" },
    { value: "horizon", label: "Horizon" },
  ];

  const props = defineProps<{ location: TerrainLocationInterface; radiusMeters: number; datasetId: number | null; timestamp: string }>();
  const emit = defineEmits<{ patch: [patch: VisibilityPatchInterface | null, sunlight: IlluminationPatchInterface | null] }>();
  const sunlightResult = ref<{ center: IlluminationInterface; patch: IlluminationPatchInterface | null } | null>(null);
  const earthResult = ref<{ center: EarthVisibilityInterface; patch: EarthVisibilityPatchInterface | null } | null>(null);
  const isCalculating = ref(false);
  const sunlightProgress = ref(0);
  const earthProgress = ref(0);
  const errorMessage = ref("");
  const calculateHint = computed(() =>
    props.radiusMeters
      ? `Traces sunlight and the line of sight to Earth across this ${props.radiusMeters / 1000} km-radius area at the selected time. Areas take up to about 30 seconds.`
      : "Traces sunlight and the line of sight to Earth at this point at the selected time."
  );

  const progressPercent = computed(() => Math.floor((sunlightProgress.value + earthProgress.value) / 2));
  const buttonProgress = computed(() => (props.radiusMeters ? `Calculating… ${progressPercent.value}%` : "Calculating…"));
  const calculateLabel = computed(() => {
    if (isCalculating.value) {
      return buttonProgress.value;
    }

    return sunlightResult.value ? "Recalculate" : "Calculate visibility";
  });

  const sunlightAverage = computed(() => regionAverage(sunlightResult.value?.patch ?? null));
  const earthAverage = computed(() => regionAverage(earthResult.value?.patch ?? null));

  const readouts = computed(() => {
    if (!sunlightResult.value || !earthResult.value) {
      return null;
    }

    const sun = sunlightResult.value.center;
    const earth = earthResult.value.center;
    const sunCenter = sunlightLabel(sun.visibleSunFraction);
    const earthCenter = earth.earthCenterVisible ? "Visible" : "Blocked";
    const sunPosition = `elevation ${sun.sunElevationDegrees.toFixed(1)}°`;
    const earthPosition = `elevation ${earth.earthElevationDegrees.toFixed(1)}°`;

    if (sunlightAverage.value !== null && earthAverage.value !== null) {
      return [
        { label: "Sun, region average", value: `${sunlightAverage.value}%`, note: `Center: ${sunCenter}, ${sunPosition}` },
        { label: "Earth, region average", value: `${earthAverage.value}%`, note: `Center: ${earthCenter}, ${earthPosition}` },
      ];
    }

    return [
      { label: "Sun", value: sunCenter, note: `${sunPosition}, azimuth ${sun.sunAzimuthDegrees.toFixed(0)}°` },
      { label: "Earth", value: earthCenter, note: `${Math.round(earth.visibleEarthFraction * 100)}% of the disk, ${earthPosition}` },
    ];
  });

  const mapMetric = ref<VisibilityMetric>("sunlight");
  const mapPatch = computed<VisibilityPatchInterface | null>(() => {
    const sunlight = sunlightResult.value?.patch;
    const earth = earthResult.value?.patch;

    if (!sunlight || !earth) {
      return null;
    }
    if (mapMetric.value === "sunlight") {
      return sunlight;
    }
    if (mapMetric.value === "earth") {
      return earth;
    }

    return jointPatch(sunlight, earth);
  });
  let request = new AbortController();

  function regionAverage(patch: VisibilityPatchInterface | null) {
    if (!patch) {
      return null;
    }

    let totalFraction = 0;
    let pointCount = 0;

    for (const point of patch.points) {
      if (point === null) {
        continue;
      }

      totalFraction += patchFraction(point);
      pointCount++;
    }

    if (pointCount === 0) {
      return null;
    }

    return Math.round((totalFraction / pointCount) * 100);
  }

  async function calculate() {
    request.abort();
    request = new AbortController();

    const current = request;
    const datasetId = props.datasetId!;

    isCalculating.value = true;
    sunlightProgress.value = 0;
    earthProgress.value = 0;
    errorMessage.value = "";

    try {
      if (props.radiusMeters) {
        const [sunlightPatch, earthPatch] = await Promise.all([
          api.terrain.illuminationPatch(datasetId, props.location, props.timestamp, props.radiusMeters, current.signal, (update) => {
            if (!current.signal.aborted) {
              sunlightProgress.value = update.percentage;
            }
          }),
          api.terrain.earthPatch(datasetId, props.location, props.timestamp, props.radiusMeters, current.signal, (update) => {
            if (!current.signal.aborted) {
              earthProgress.value = update.percentage;
            }
          }),
        ]);

        if (current.signal.aborted) {
          return;
        }

        sunlightResult.value = { center: sunlightPatch.center, patch: sunlightPatch };
        earthResult.value = { center: earthPatch.center, patch: earthPatch };
      } else {
        const [sunlight, earth] = await Promise.all([
          api.terrain.illumination(datasetId, props.location, props.timestamp, current.signal),
          api.terrain.earth(datasetId, props.location, props.timestamp, current.signal),
        ]);

        if (current.signal.aborted) {
          return;
        }

        sunlightResult.value = { center: sunlight, patch: null };
        earthResult.value = { center: earth, patch: null };
      }
    } catch (error) {
      if (!current.signal.aborted) {
        errorMessage.value = getFirstApiErrorMessage(error, "Unable to calculate sunlight and Earth visibility here.");
        current.abort();
      }
    } finally {
      if (request === current) {
        isCalculating.value = false;
      }
    }
  }

  function clear() {
    request.abort();
    emit("patch", null, null);
    sunlightResult.value = null;
    earthResult.value = null;
    errorMessage.value = "";
    isCalculating.value = false;
  }

  watch(
    [() => props.location.latitude, () => props.location.longitude, () => props.radiusMeters, () => props.timestamp, () => props.datasetId],
    clear
  );
  watch(mapPatch, (patch) => emit("patch", patch, sunlightResult.value?.patch ?? null));
  onBeforeUnmount(clear);
</script>
