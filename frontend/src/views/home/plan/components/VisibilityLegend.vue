<template>
  <div
    class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-secondary"
    role="group"
    :aria-label="`${metricLabel(metric)} color scale`"
  >
    <VisibilityScale :metric="metric" />
    <template v-if="filtered">
      <span class="flex items-center gap-1.5">
        <span
          class="h-2.5 w-6 rounded-sm"
          :style="{ background: fadedGradient }"
          aria-hidden="true"
        />
        Below your minimums
      </span>
      <span class="flex items-center gap-1.5">
        <span
          class="h-3.5 w-3 rounded-sm ring-1 ring-accent ring-inset"
          aria-hidden="true"
        />
        Best window
      </span>
    </template>
    <span
      v-if="hasMissing"
      class="flex items-center gap-1.5"
    >
      <span
        class="size-2.5 rounded-sm"
        :style="{ background: NOT_CALCULATED_COLOR }"
        aria-hidden="true"
      />
      Not calculated
    </span>
    <span class="flex items-center gap-1.5">
      <span
        class="size-2.5 rounded-sm ring-1 ring-secondary/30 ring-inset"
        :style="{ background: OUTSIDE_PLAN_COLOR }"
        aria-hidden="true"
      />
      Outside plan
    </span>
  </div>
</template>

<script setup lang="ts">
  import { computed } from "vue";
  import type { VisibilityMetric } from "@/types/terrain/VisibilityInterface";
  import { belowMinimumColor, NOT_CALCULATED_COLOR, OUTSIDE_PLAN_COLOR, visibilityFractionColor } from "@/views/home/viewer/sunlightOverlay";
  import VisibilityScale from "./VisibilityScale.vue";
  import { metricLabel } from "@/views/home/visibility/visibilityView";

  const props = withDefaults(defineProps<{ metric: VisibilityMetric; filtered?: boolean; hasMissing?: boolean }>(), {
    filtered: false,
    hasMissing: true,
  });
  const fadedGradient = computed(
    () =>
      `linear-gradient(to right, ${[0, 0.25, 0.5, 0.75, 1].map((fraction) => belowMinimumColor(visibilityFractionColor(fraction, props.metric))).join(", ")})`
  );
</script>
