<template>
  <div class="flex flex-col rounded-md bg-surface-muted px-3 py-2">
    <dt class="flex-1 text-xs text-secondary">{{ label }}</dt>
    <dd :class="cn('font-semibold text-body tabular-nums', size === 'large' ? 'text-xl leading-7' : 'text-base')">{{ value }}</dd>
    <dd
      v-if="note"
      class="text-xs text-secondary"
    >
      {{ note }}
    </dd>

    <slot />
  </div>
</template>

<script setup lang="ts">
  import { cn } from "@/utils/className";

  withDefaults(defineProps<{ label: string; value: string; note?: string; size?: "regular" | "large" }>(), { note: "", size: "regular" });
</script>
