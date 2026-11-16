<template>
  <div
    v-if="store.errorMessage"
    class="space-y-2"
  >
    <AlertBanner :message="store.errorMessage" />
    <div class="flex gap-2">
      <AppButton
        v-if="!store.stepOptions.length"
        @click="store.loadLists()"
        >Retry</AppButton
      >
      <AppButton @click="store.errorMessage = ''">Dismiss</AppButton>
    </div>
  </div>
</template>

<script setup lang="ts">
  import AlertBanner from "@/components/ui/AlertBanner.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import { useSunlightStore } from "@/views/home/sunlightStore";

  const store = useSunlightStore();
</script>
