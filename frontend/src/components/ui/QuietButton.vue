<template>
  <button
    type="button"
    :class="cn(QUIET_BUTTON_CLASS, tone === 'danger' && 'font-medium text-error hover:text-error')"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
  import { cn } from "@/utils/className";
  import { QUIET_BUTTON_CLASS } from "./quietButtonClass";

  withDefaults(defineProps<{ tone?: "neutral" | "danger" }>(), { tone: "neutral" });
</script>
