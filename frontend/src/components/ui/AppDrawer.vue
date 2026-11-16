<template>
  <Drawer
    v-model:visible="visible"
    position="left"
    :header="title"
    :aria-label="title"
    @show="rememberOpener"
    @after-hide="returnFocus"
    :pt="{
      mask: { class: 'fixed inset-0 z-40 flex justify-start bg-black/40' },
      root: { class: 'flex h-full w-full max-w-xs flex-col border-r border-line bg-surface text-body shadow-xl' },
      header: { class: 'flex items-center justify-between gap-3 px-4 pt-4 pb-2' },
      title: { class: 'font-display font-semibold [font-stretch:110%]' },
      pcCloseButton: { root: { class: CLOSE_BUTTON_CLASS } },
      content: { class: 'min-h-0 flex-1 overflow-y-auto px-2 pb-2' },
      footer: { class: 'border-t border-line px-4 py-3' },
    }"
  >
    <slot />
    <template
      v-if="$slots.footer"
      #footer
    >
      <slot name="footer" />
    </template>
  </Drawer>
</template>

<script setup lang="ts">
  import Drawer from "primevue/drawer";
  import { CLOSE_BUTTON_CLASS } from "./closeButtonClass";

  const visible = defineModel<boolean>("visible", { required: true });
  defineProps<{ title: string }>();
  let opener: HTMLElement | null = null;

  function rememberOpener() {
    opener = document.activeElement as HTMLElement | null;
  }

  function returnFocus() {
    if (document.activeElement === document.body && opener?.isConnected) {
      opener.focus();
    }
  }
</script>
