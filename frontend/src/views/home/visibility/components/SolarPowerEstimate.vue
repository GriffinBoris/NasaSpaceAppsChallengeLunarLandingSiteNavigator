<template>
  <section :class="framed ? 'rounded-md border border-line bg-surface p-3' : ''">
    <h3 class="text-base font-semibold text-body">Solar power estimate</h3>
    <div class="mt-3 space-y-3">
      <p class="text-xs text-secondary">
        At the site center
        <span class="block min-h-5 tabular-nums">{{ sunlight ? formatUtc(Date.parse(sunlight.timestamp)) : "No sunlight result loaded" }}</span>
      </p>
      <dl class="grid grid-cols-2 gap-2">
        <StatTile
          label="Level panel"
          size="large"
          :value="estimate ? formatWatts(estimate.levelPowerWatts) : '–'"
          :note="estimate ? `${formatNumber(estimate.levelIrradianceWattsPerSquareMeter)} W/m² sunlight` : '– W/m² sunlight'"
        />
        <StatTile
          label="Sun-tracking panel"
          size="large"
          :value="estimate ? formatWatts(estimate.trackingPowerWatts) : '–'"
          :note="estimate ? `${formatNumber(estimate.trackingIrradianceWattsPerSquareMeter)} W/m² sunlight` : '– W/m² sunlight'"
        />
      </dl>
      <p class="-mt-1 text-xs text-secondary">Illustrative power, before system losses</p>

      <ResultSummary
        class="min-h-5 text-sm leading-5 text-secondary"
        label="Solar power results"
      >
        <p v-if="sunlight">
          Sun elevation {{ sunlight.sunElevationDegrees.toFixed(1) }}°, {{ Math.round(sunlight.visibleSunFraction * 100) }}% visible.
        </p>
        <LoadingSpinner
          v-else-if="isLoading"
          label="Reading the saved sunlight result…"
        />
        <p
          v-else
          role="status"
        >
          A calculated sunlight result is needed at this time.
        </p>
      </ResultSummary>
      <div class="grid grid-cols-2 gap-2 text-secondary">
        <label class="space-y-1 text-xs font-medium"
          >Panel area (m²)
          <AppTextInput
            v-model="areaText"
            type="number"
            min="0"
            step="any"
            inputmode="decimal"
            :aria-invalid="Boolean(panelError)"
          />
        </label>
        <label class="space-y-1 text-xs font-medium"
          >Efficiency (%)
          <AppTextInput
            v-model="efficiencyText"
            type="number"
            min="0"
            max="100"
            step="any"
            inputmode="decimal"
            :aria-invalid="Boolean(panelError)"
          />
        </label>
      </div>
      <p
        v-if="panelError"
        class="text-sm text-error"
        role="alert"
      >
        {{ panelError }}
      </p>
      <details class="text-sm text-secondary">
        <summary class="cursor-pointer rounded focus-visible:outline-2 focus-visible:outline-focus-ring">About this estimate</summary>
        <div class="mt-3 space-y-3">
          <ul class="list-disc space-y-1 pl-4">
            <li>Level panels follow the reference horizon, regardless of terrain slope.</li>
            <li>Sun-tracking panels always face the Sun, with no mounting limits.</li>
            <li>
              Uses fixed {{ SOLAR_IRRADIANCE_WATTS_PER_SQUARE_METER.toLocaleString("en-US") }} W/m² sunlight, adjusted for Sun visibility, panel
              angle, area and efficiency.
            </li>
          </ul>
          <p>Illustrative power only, not stored energy. Less accurate near the horizon or in partial shadow.</p>
          <p>Excludes distance changes, eclipses, reflected light, panel height, and losses from temperature, dust, wiring and cell mismatch.</p>
          <p>
            Sources:
            <a
              class="text-accent underline"
              href="https://earth.gsfc.nasa.gov/climate/projects/solar-irradiance/science"
              target="_blank"
              rel="noopener noreferrer"
              >NASA sunlight reference</a
            >
            and
            <a
              class="text-accent underline"
              href="https://www.pvsyst.com/help/project-design/shadings/backtracking-strategy/cosine-effect.html"
              target="_blank"
              rel="noopener noreferrer"
              >panel angle relationship</a
            >.
          </p>
        </div>
      </details>
    </div>
  </section>
</template>

<script lang="ts">
  import { ref } from "vue";

  const panelAreaText = ref<string | number>("1");
  const panelEfficiencyText = ref<string | number>("30");
</script>

<script setup lang="ts">
  import LoadingSpinner from "@/components/ui/LoadingSpinner.vue";
  import { computed } from "vue";
  import AppTextInput from "@/components/ui/AppTextInput.vue";
  import StatTile from "@/components/ui/StatTile.vue";
  import ResultSummary from "@/components/ui/ResultSummary.vue";
  import type { IlluminationInterface } from "@/types/terrain/IlluminationInterface";
  import { formatUtc } from "@/views/home/plan/planTimeline";
  import { estimateSolarPower, solarPanelError, SOLAR_IRRADIANCE_WATTS_PER_SQUARE_METER } from "@/views/home/visibility/solarPower";

  const props = withDefaults(defineProps<{ sunlight: IlluminationInterface | null; isLoading?: boolean; framed?: boolean }>(), {
    isLoading: false,
    framed: true,
  });

  const areaText = panelAreaText;
  const efficiencyText = panelEfficiencyText;
  const panel = computed(() => ({ areaSquareMeters: Number(areaText.value), efficiencyPercent: Number(efficiencyText.value) }));
  const panelError = computed(() => solarPanelError(panel.value));
  const estimate = computed(() =>
    props.sunlight ? estimateSolarPower(props.sunlight.sunElevationDegrees, props.sunlight.visibleSunFraction, panel.value) : null
  );
  const numberFormatter = new Intl.NumberFormat("en", { maximumFractionDigits: 1 });

  function formatNumber(value: number) {
    return numberFormatter.format(value);
  }

  function formatWatts(value: number) {
    return `${formatNumber(value)} W`;
  }
</script>
