<template>
  <Popover
    ref="popover"
    :pt="{ root: { class: 'z-50 mt-1 rounded-md border border-line bg-surface p-1 text-body shadow-xl' } }"
    @show="onShow"
    @hide="onHide"
  >
    <div
      ref="content"
      @keydown.tab="keepTabInside"
    >
      <slot />
    </div>
  </Popover>
</template>

<script setup lang="ts">
  import { nextTick, ref } from "vue";
  import Popover from "primevue/popover";

  const FOCUSABLE = "input:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex='-1'])";

  const emit = defineEmits<{ show: []; hide: [] }>();
  const popover = ref<InstanceType<typeof Popover>>();
  const content = ref<HTMLDivElement>();
  let trigger: HTMLElement | null = null;

  async function onShow() {
    emit("show");

    await nextTick();

    if (!content.value?.contains(document.activeElement)) {
      content.value?.querySelector<HTMLElement>(FOCUSABLE)?.focus();
    }
  }

  function onHide() {
    emit("hide");

    if (content.value?.contains(document.activeElement) || document.activeElement === document.body) {
      trigger?.focus();
    }
  }

  function keepTabInside(event: KeyboardEvent) {
    const focusable = Array.from(content.value!.querySelectorAll<HTMLElement>(FOCUSABLE));
    const edge = event.shiftKey ? focusable[0] : focusable[focusable.length - 1];

    if (document.activeElement !== edge) {
      return;
    }

    event.preventDefault();
    popover.value!.hide();
    trigger?.focus();
  }

  defineExpose({
    toggle: (event: Event) => {
      trigger = event.currentTarget as HTMLElement;
      popover.value!.toggle(event);
    },
    hide: () => popover.value!.hide(),
  });
</script>
