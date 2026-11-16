<template>
  <Dialog
    v-model:visible="visible"
    modal
    position="top"
    :draggable="false"
    :header="title"
    :pt="{
      mask: { class: 'fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/70 p-4 sm:pt-16' },
      root: { class: 'w-full max-w-lg rounded-xl border border-line bg-surface text-body shadow-xl' },
      header: { class: 'flex items-center justify-between gap-3 px-5 pt-4 pb-2' },
      title: { class: 'font-display font-semibold [font-stretch:110%]' },
      pcCloseButton: { root: { class: CLOSE_BUTTON_CLASS } },
      content: { class: 'px-5 pb-5' },
    }"
  >
    <slot />
  </Dialog>
</template>

<script setup lang="ts">
  import Dialog from "primevue/dialog";
  import { CLOSE_BUTTON_CLASS } from "./closeButtonClass";

  const visible = defineModel<boolean>("visible", { required: true });
  defineProps<{ title: string }>();
</script>
