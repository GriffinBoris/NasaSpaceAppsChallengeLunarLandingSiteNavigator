<template>
  <div
    ref="overlay"
    class="pointer-events-none absolute inset-0 text-xs"
    role="group"
    aria-label="Moon feature names"
  >
    <button
      type="button"
      tabindex="-1"
      v-for="label in names.labels.value"
      :key="label.feature.id"
      :title="label.feature.englishName ? `${label.feature.name} (${label.feature.englishName})` : label.feature.name"
      :style="{ left: `${label.x}px`, top: `${label.y}px`, width: `${label.width}px` }"
      class="pointer-events-auto absolute -translate-x-1/2 -translate-y-1/2 rounded px-1.5 py-0.5 text-white/80 [text-shadow:0_1px_3px_black,0_0_3px_black] hover:bg-black/50 hover:text-white focus-visible:outline-2 focus-visible:outline-focus-ring"
      @click="emit('pick', label.feature)"
    >
      <span class="block truncate leading-4">{{ label.feature.name }}</span>
      <span
        v-if="label.feature.englishName"
        class="block truncate text-xs text-white/70"
        >{{ label.feature.englishName }}</span
      >
    </button>
    <p
      v-if="names.errorMessage.value"
      class="absolute bottom-14 left-3 rounded bg-surface px-3 py-1.5 text-secondary"
      role="status"
    >
      {{ names.errorMessage.value }}
    </p>
  </div>
</template>

<script setup lang="ts">
  import { onMounted, ref } from "vue";
  import type { LunarFeatureInterface } from "@/types/terrain/LunarFeatureInterface";
  import type { FeatureLabelView } from "@/views/home/viewer/featureLabelView";
  import { useFeatureLabels } from "@/views/home/viewer/useFeatureLabels";

  const props = defineProps<{ getView: () => FeatureLabelView | null; reservedBounds: () => DOMRect[] }>();
  const emit = defineEmits<{ pick: [feature: LunarFeatureInterface] }>();
  const overlay = ref<HTMLDivElement>();
  const context = document.createElement("canvas").getContext("2d")!;
  const names = useFeatureLabels(props.getView, screenBounds, (name) => context.measureText(name).width);

  function screenBounds() {
    const origin = overlay.value!.getBoundingClientRect();

    return props.reservedBounds().map((bounds) => ({
      left: bounds.left - origin.left,
      right: bounds.right - origin.left,
      top: bounds.top - origin.top,
      bottom: bounds.bottom - origin.top,
    }));
  }

  onMounted(() => {
    context.font = `13px ${getComputedStyle(overlay.value!).fontFamily}`;
    names.update();
  });

  defineExpose({ update: names.update });
</script>
