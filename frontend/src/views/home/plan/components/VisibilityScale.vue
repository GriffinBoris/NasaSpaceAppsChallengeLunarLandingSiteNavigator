<template>
  <div
    class="flex items-center gap-1.5 text-xs text-secondary"
    role="img"
    :aria-label="`${endpoints[0]} 0% to ${endpoints[1]} 100%`"
  >
    <span class="whitespace-nowrap">{{ endpoints[0] }} 0%</span>
    <span
      class="h-2.5 rounded-sm"
      :class="fill ? 'min-w-8 flex-1' : 'w-28'"
      :style="{ background: visibilityGradient(metric) }"
      aria-hidden="true"
    />
    <span class="whitespace-nowrap">100% {{ endpoints[1] }}</span>
  </div>
</template>

<script setup lang="ts">
  import { computed } from "vue";
  import type { VisibilityMetric } from "@/types/terrain/VisibilityInterface";
  import { visibilityGradient } from "@/views/home/viewer/sunlightOverlay";

  const SCALE_LABELS: Record<VisibilityMetric, [string, string]> = {
    sunlight: ["No Sun", "Full Sun"],
    earth: ["Earth blocked", "Earth visible"],
    joint: ["No overlap", "Sun and Earth"],
  };

  const props = withDefaults(defineProps<{ metric: VisibilityMetric; fill?: boolean; labels?: [string, string] }>(), {
    fill: false,
    labels: undefined,
  });
  const endpoints = computed(() => props.labels ?? SCALE_LABELS[props.metric]);
</script>
