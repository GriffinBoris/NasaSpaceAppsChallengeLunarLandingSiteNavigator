<template>
  <span
    ref="root"
    class="contents"
  >
    <template v-if="!isConfirming">
      <QuietButton
        v-if="quiet"
        ref="startButton"
        :disabled="disabled"
        :aria-label="ariaLabel"
        @click="isConfirming = true"
        >{{ label }}</QuietButton
      >
      <AppButton
        v-else
        ref="startButton"
        tone="danger"
        :disabled="disabled"
        :aria-label="ariaLabel"
        @click="isConfirming = true"
        >{{ label }}</AppButton
      >
    </template>
    <template v-else>
      <QuietButton
        v-if="quiet"
        tone="danger"
        :aria-label="ariaLabel && `Confirm: ${ariaLabel}`"
        @click="confirm"
        >{{ confirmLabel }}</QuietButton
      >
      <AppButton
        v-else
        tone="danger"
        :aria-label="ariaLabel && `Confirm: ${ariaLabel}`"
        @click="confirm"
        >{{ confirmLabel }}</AppButton
      >
      <QuietButton
        v-if="quiet"
        ref="keepButton"
        @click="isConfirming = false"
        >Keep</QuietButton
      >
      <AppButton
        v-else
        ref="keepButton"
        @click="isConfirming = false"
        >Keep</AppButton
      >
    </template>
  </span>
</template>

<script setup lang="ts">
  import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
  import AppButton from "./AppButton.vue";
  import QuietButton from "./QuietButton.vue";

  withDefaults(defineProps<{ label: string; confirmLabel: string; ariaLabel?: string; quiet?: boolean; disabled?: boolean }>(), {
    ariaLabel: undefined,
    quiet: false,
    disabled: false,
  });
  const emit = defineEmits<{ confirm: [] }>();
  const isConfirming = defineModel<boolean>("confirming", { default: false });
  const root = ref<HTMLSpanElement>();
  const startButton = ref<{ $el: HTMLElement }>();
  const keepButton = ref<{ $el: HTMLElement }>();

  watch(isConfirming, async (confirming) => {
    const hadFocus = root.value?.contains(document.activeElement) || document.activeElement === document.body;

    await nextTick();

    if (hadFocus) {
      (confirming ? keepButton : startButton).value?.$el.focus();
    }
  });

  onMounted(() => {
    if (isConfirming.value) {
      keepButton.value?.$el.focus();
    }
  });

  function confirm() {
    isConfirming.value = false;
    emit("confirm");
  }

  onBeforeUnmount(() => {
    if (!root.value?.contains(document.activeElement)) {
      return;
    }

    const container = root.value.parentElement?.closest<HTMLElement>('[role="dialog"], section');

    void nextTick(() => container?.querySelector<HTMLElement>("button:not([disabled]), a[href]")?.focus());
  });
</script>
