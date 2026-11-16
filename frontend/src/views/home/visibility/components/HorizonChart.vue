<template>
  <div class="space-y-3">
    <div class="overflow-x-auto">
      <svg
        viewBox="0 0 960 302"
        class="block w-full min-w-[36rem] rounded-md bg-background"
        :class="compact ? '[&_text]:text-[16px]' : ''"
        role="img"
        :aria-label="chartDescription"
      >
        <desc>
          Compass direction runs from north through east, south, and west back to north. Height is elevation in degrees. The shaded band marks terrain
          uncertainty. Sun and Earth markers show their centers.
        </desc>
        <g
          v-for="tick in chart.elevationTicks"
          :key="tick.elevation"
        >
          <line
            :x1="HORIZON_PLOT.left"
            :x2="HORIZON_PLOT.right"
            :y1="tick.y"
            :y2="tick.y"
            class="stroke-line"
          />
          <text
            :x="HORIZON_PLOT.left - 10"
            :y="tick.y + 4"
            text-anchor="end"
            class="fill-secondary text-[12px]"
          >
            {{ tick.elevation }}°
          </text>
        </g>
        <g
          v-for="tick in chart.compassTicks"
          :key="tick.azimuth"
        >
          <line
            :x1="tick.x"
            :x2="tick.x"
            :y1="HORIZON_PLOT.top"
            :y2="HORIZON_PLOT.bottom"
            class="stroke-line"
          />
          <text
            :x="tick.x"
            :y="HORIZON_PLOT.bottom + 21"
            text-anchor="middle"
            class="fill-body text-[13px]"
          >
            {{ tick.label }}
          </text>
          <text
            :x="tick.x"
            :y="HORIZON_PLOT.bottom + 40"
            text-anchor="middle"
            class="fill-secondary text-[13px]"
          >
            {{ tick.azimuth }}°
          </text>
        </g>
        <path
          :d="chart.terrainPath"
          class="fill-surface-muted"
        />
        <path
          :d="chart.uncertaintyPath"
          class="fill-secondary/25"
        />
        <path
          :d="chart.upperPath"
          fill="none"
          class="stroke-secondary"
          stroke-width="1.3"
        />
        <line
          :x1="HORIZON_PLOT.left"
          :x2="HORIZON_PLOT.right"
          :y1="chart.referenceY"
          :y2="chart.referenceY"
          class="stroke-accent"
          stroke-dasharray="5 5"
        />
        <g
          v-for="marker in markers"
          :key="marker.body"
        >
          <circle
            :cx="marker.x"
            :cy="marker.y"
            r="5"
            :fill="VISIBLE_COLORS[marker.body]"
            class="stroke-body"
            stroke-width="1"
          >
            <title>
              {{ marker.body === "sunlight" ? "Sun" : "Earth" }}: elevation {{ marker.elevationDegrees.toFixed(1) }}°, azimuth
              {{ marker.azimuthDegrees.toFixed(1) }}°
            </title>
          </circle>
          <text
            :x="marker.x"
            :y="marker.y + (marker.body === 'sunlight' ? -11 : 21)"
            :text-anchor="marker.textAnchor"
            class="fill-body text-[12px] font-medium"
          >
            {{ marker.body === "sunlight" ? "Sun" : "Earth" }}
          </text>
        </g>
      </svg>
    </div>
    <div class="flex flex-wrap gap-x-5 gap-y-1 text-xs text-secondary">
      <span
        v-for="marker in markers"
        :key="marker.body"
        class="inline-flex items-center gap-1.5"
      >
        <span
          class="h-2 w-2 rounded-full"
          :style="{ background: VISIBLE_COLORS[marker.body] }"
        />
        {{ marker.body === "sunlight" ? "Sun" : "Earth" }}: elevation {{ marker.elevationDegrees.toFixed(1) }}°, azimuth
        {{ marker.azimuthDegrees.toFixed(1) }}°
      </span>
      <span v-if="!compact">Dashed line: reference horizon at 0°</span>
    </div>
    <details
      v-if="horizon?.bounds && !compact"
      class="text-xs text-secondary"
    >
      <summary class="cursor-pointer rounded focus-visible:outline-2 focus-visible:outline-focus-ring">Terrain uncertainty</summary>
      <p class="mt-2">
        Terrain below the lower bound is solid; the band contains the uncertain skyline. Visibility maps use ray tracing where needed.
      </p>
    </details>
  </div>
</template>

<script setup lang="ts">
  import { computed } from "vue";
  import type { HorizonInterface } from "@/types/terrain/HorizonInterface";
  import type { BodyDirectionInterface } from "@/types/terrain/SiteTerrainInterface";
  import { VISIBLE_COLORS } from "@/views/home/viewer/sunlightOverlay";
  import { HORIZON_PLOT, horizonChart } from "../horizonChart";

  const props = withDefaults(
    defineProps<{
      horizon: HorizonInterface | null;
      sun: BodyDirectionInterface | null;
      earth: BodyDirectionInterface | null;
      elevationSeries: number[][];
      timeText: string;
      compact?: boolean;
    }>(),
    { compact: false }
  );
  const chart = computed(() => horizonChart(props.horizon, props.elevationSeries));
  const markers = computed(() => {
    const positions = [];

    for (const [body, direction] of [
      ["sunlight", props.sun],
      ["earth", props.earth],
    ] as const) {
      if (direction) {
        const position = chart.value.position(direction);
        let textAnchor = "middle";

        if (position.x > HORIZON_PLOT.right - 30) {
          textAnchor = "end";
        } else if (position.x < HORIZON_PLOT.left + 30) {
          textAnchor = "start";
        }

        positions.push({ body, ...direction, ...position, textAnchor });
      }
    }

    return positions;
  });
  const chartDescription = computed(() => {
    const positions = markers.value
      .map(
        (marker) =>
          `${marker.body === "sunlight" ? "Sun" : "Earth"} elevation ${marker.elevationDegrees.toFixed(1)} degrees, azimuth ${marker.azimuthDegrees.toFixed(1)} degrees`
      )
      .join(". ");

    return `Horizon, ${props.timeText}. ${positions}. ${props.horizon?.bounds ? "Terrain bounds shown." : "Terrain skyline unavailable."}`;
  });
</script>
