<template>
  <div
    ref="overlay"
    class="pointer-events-none absolute inset-0"
    role="group"
    aria-label="Saved sites on the Moon"
  >
    <template
      v-for="marker in markers"
      :key="marker.id"
    >
      <span
        class="absolute top-0 left-0 size-2.5 rounded-full border-2 border-space"
        :class="marker.id === store.focusedSelectionId ? 'bg-white' : 'bg-accent'"
        :style="{ transform: `translate(${marker.x - 5}px, ${marker.y - 5}px)` }"
        aria-hidden="true"
      />
      <button
        type="button"
        class="pointer-events-auto absolute top-0 left-0 rounded bg-surface px-1.5 py-0.5 text-xs whitespace-nowrap focus-visible:outline-2 focus-visible:outline-focus-ring"
        :class="marker.id === store.focusedSelectionId ? 'font-medium text-body' : 'text-secondary hover:text-body'"
        :style="{ transform: `translate(${marker.x + 9}px, ${marker.y - 10 + marker.labelRow * 22}px)` }"
        :aria-pressed="marker.id === store.focusedSelectionId"
        @click="store.focusSelection(marker.id)"
      >
        {{ marker.name }}
      </button>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { onUnmounted, ref, shallowRef, watch } from "vue";
  import type { SiteMarkerInterface } from "@/types/terrain/SiteMarkerInterface";
  import type { TerrainLocationInterface } from "@/types/terrain/TerrainLocationInterface";
  import { useSunlightStore } from "@/views/home/sunlightStore";

  const props = defineProps<{ project: (location: TerrainLocationInterface) => { x: number; y: number } | null }>();
  const store = useSunlightStore();
  const markers = shallowRef<SiteMarkerInterface[]>([]);
  const overlay = ref<HTMLDivElement>();
  let frame = 0;

  function measure() {
    frame = 0;

    const visibleMarkers: SiteMarkerInterface[] = [];

    for (const selection of store.selections) {
      const position = props.project(selection);

      if (!position) {
        continue;
      }

      const labelRow = visibleMarkers.filter((marker) => Math.hypot(marker.x - position.x, marker.y - position.y) < 12).length;

      visibleMarkers.push({ id: selection.id, name: selection.name, ...position, labelRow });
    }

    markers.value = visibleMarkers;
  }

  function update() {
    if (!frame) {
      frame = requestAnimationFrame(measure);
    }
  }

  watch(() => store.selections, update, { deep: true });
  onUnmounted(() => cancelAnimationFrame(frame));

  function bounds(): DOMRect[] {
    if (!overlay.value) {
      return [];
    }

    return Array.from(overlay.value.querySelectorAll("button"), (button) => {
      const rectangle = button.getBoundingClientRect();

      return new DOMRect(rectangle.left - 18, rectangle.top, rectangle.width + 18, rectangle.height);
    });
  }

  defineExpose({ update, bounds });
</script>
