<template>
  <span
    v-if="label"
    role="status"
    class="inline-flex items-center gap-2"
  >
    <span
      :class="cn(SPINNER_CLASS, SIZE_CLASSES[size])"
      aria-hidden="true"
    />
    {{ label }}
  </span>
  <span
    v-else
    :class="cn(SPINNER_CLASS, SIZE_CLASSES[size])"
    aria-hidden="true"
  />
</template>

<script setup lang="ts">
  import { cn } from "@/utils/className";

  const SPINNER_CLASS = "inline-block shrink-0 rounded-full border-current border-r-transparent motion-safe:animate-spin";
  const SIZE_CLASSES = { small: "size-4 border-2", large: "size-8 border-[3px]" };

  withDefaults(defineProps<{ label?: string; size?: "small" | "large" }>(), { label: "", size: "small" });
</script>
