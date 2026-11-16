<template>
  <svg
    viewBox="0 0 100 100"
    class="pointer-events-none absolute inset-0 h-full w-full"
    aria-hidden="true"
  >
    <circle
      cx="50"
      cy="50"
      r="49.5"
      fill="none"
      stroke="rgba(255, 255, 255, 0.35)"
      stroke-width="0.5"
    />
    <circle
      cx="50"
      cy="50"
      :r="markerColor ? 2.4 : 1.6"
      :fill="markerColor ?? 'none'"
      stroke="white"
      stroke-width="0.6"
    />
    <text
      x="95"
      y="7"
      fill="white"
      font-size="5"
      text-anchor="end"
    >
      N
    </text>
    <rect
      x="4"
      y="94"
      :width="scale.width"
      height="0.8"
      fill="white"
    />
    <text
      x="4"
      y="91.5"
      fill="white"
      font-size="4"
    >
      {{ scale.label }}
    </text>
    <g v-if="bodyPoint">
      <line
        :x1="bodyPoint.x"
        :y1="bodyPoint.y"
        :x2="bodyPoint.innerX"
        :y2="bodyPoint.innerY"
        :stroke="VISIBLE_COLORS[body]"
        stroke-width="0.9"
      />
      <circle
        :cx="bodyPoint.x"
        :cy="bodyPoint.y"
        r="2"
        :fill="VISIBLE_COLORS[body]"
      />
    </g>
  </svg>
</template>

<script setup lang="ts">
  import { computed } from "vue";
  import { VISIBLE_COLORS } from "@/views/home/viewer/sunlightOverlay";

  const SCALE_LENGTHS_METERS = [100, 250, 500, 1000, 2000, 2500, 5000, 10000, 20000, 25000];

  const props = defineProps<{ radiusMeters: number; body: "sunlight" | "earth"; azimuthDegrees?: number; markerColor?: string }>();

  const scale = computed(() => {
    const diameter = props.radiusMeters * 2;
    const fitting = SCALE_LENGTHS_METERS.filter((candidate) => candidate <= diameter / 4);
    const length = fitting[fitting.length - 1] ?? SCALE_LENGTHS_METERS[0]!;

    return { width: (length / diameter) * 100, label: length >= 1000 ? `${length / 1000} km` : `${length} m` };
  });

  const bodyPoint = computed(() => {
    if (props.azimuthDegrees === undefined) {
      return null;
    }

    const azimuth = (props.azimuthDegrees * Math.PI) / 180;
    const point = (radius: number) => ({ x: 50 + Math.sin(azimuth) * radius, y: 50 - Math.cos(azimuth) * radius });
    const outer = point(46);
    const inner = point(38);

    return { x: outer.x, y: outer.y, innerX: inner.x, innerY: inner.y };
  });
</script>
