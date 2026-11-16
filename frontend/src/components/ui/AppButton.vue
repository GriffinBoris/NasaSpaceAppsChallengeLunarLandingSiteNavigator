<template>
  <button
    v-bind="buttonAttributes"
    :type="buttonType"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    :class="
      cn(
        'inline-flex min-h-9 items-center justify-center gap-2 rounded-md border px-3 text-sm font-medium transition-colors pointer-coarse:min-h-11 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring disabled:cursor-not-allowed disabled:opacity-60 [&>svg]:size-4 [&>svg]:shrink-0',
        TONE_CLASSES[tone],
        loading && 'disabled:cursor-progress disabled:opacity-100',
        square && 'w-9 px-0 pointer-coarse:w-11',
        $attrs.class as string
      )
    "
  >
    <LoadingSpinner v-if="loading" />
    <slot />
  </button>
</template>

<script setup lang="ts">
  import { computed, useAttrs } from "vue";
  import { cn } from "@/utils/className";
  import LoadingSpinner from "./LoadingSpinner.vue";

  const TONE_CLASSES = {
    primary: "border-primary bg-primary text-primary-contrast hover:bg-primary/90 active:bg-primary/75",
    secondary: "border-line bg-surface text-body hover:bg-surface-muted active:bg-line",
    ghost: "border-transparent bg-transparent text-body hover:bg-surface-muted active:bg-line",
    danger: "border-error/40 bg-surface text-error hover:bg-error/10 active:bg-error/20",
  };

  defineOptions({ inheritAttrs: false });

  withDefaults(
    defineProps<{
      buttonType?: "button" | "submit" | "reset";
      disabled?: boolean;
      loading?: boolean;
      tone?: "primary" | "secondary" | "ghost" | "danger";
      square?: boolean;
    }>(),
    { buttonType: "button", tone: "secondary", disabled: false, loading: false, square: false }
  );
  const attributes = useAttrs();
  const buttonAttributes = computed(() => Object.fromEntries(Object.entries(attributes).filter(([name]) => name !== "class")));
</script>
