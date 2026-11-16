<template>
  <div
    :role="tone === 'error' ? 'alert' : 'status'"
    :class="cn('w-full rounded-md border px-4 py-3 text-sm leading-6', TONE_CLASSES[tone])"
  >
    {{ message }}
  </div>
</template>

<script setup lang="ts">
  import { cn } from "@/utils/className";

  const TONE_CLASSES = {
    error: "border-error/20 bg-error/10 text-error",
    success: "border-success/20 bg-success/10 text-success",
    warning: "border-warning/20 bg-warning/10 text-warning",
  };

  withDefaults(defineProps<{ message: string; tone?: "error" | "success" | "warning" }>(), { tone: "error" });
</script>
