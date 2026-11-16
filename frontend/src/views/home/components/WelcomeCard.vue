<template>
  <FloatingPanel
    title="Getting started"
    close-label="Dismiss introduction"
    @close="emit('dismiss')"
  >
    <p class="mt-1 text-sm text-body">Pick a point or site to check Sun and Earth visibility, or make a plan to compare dates.</p>
    <details class="mt-2 text-xs text-secondary">
      <summary class="cursor-pointer rounded focus-visible:outline-2 focus-visible:outline-focus-ring">Controls</summary>
      <p class="mt-1">
        Drag to rotate. Scroll or pinch to zoom. Arrow keys rotate, plus/minus zoom, and Enter selects the center. The lightbulb (Full lighting)
        lights all terrain for inspection; calculations still use the selected UTC time.
      </p>
    </details>
    <div class="mt-3 flex flex-wrap gap-2">
      <AppButton
        tone="primary"
        @click="emit('search')"
        >Search the Moon</AppButton
      >
      <AppButton @click="emit('addSite')">Add site</AppButton>
      <QuietButton @click="emit('dismiss')">Got it</QuietButton>
    </div>
  </FloatingPanel>
</template>

<script setup lang="ts">
  import AppButton from "@/components/ui/AppButton.vue";
  import FloatingPanel from "@/components/ui/FloatingPanel.vue";
  import QuietButton from "@/components/ui/QuietButton.vue";

  const emit = defineEmits<{ dismiss: []; search: []; addSite: [] }>();
</script>
