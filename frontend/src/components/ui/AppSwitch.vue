<template>
  <button
    type="button"
    role="switch"
    :aria-checked="model"
    class="group inline-flex items-center gap-2 rounded text-sm text-body focus-visible:outline-2 focus-visible:outline-focus-ring disabled:cursor-not-allowed disabled:opacity-50 pointer-coarse:min-h-11"
    @click="model = !model"
  >
    <span
      class="relative h-5 w-9 shrink-0 rounded-full border motion-safe:transition-colors"
      :class="
        model
          ? 'border-accent bg-accent group-enabled:group-hover:bg-accent/85 group-enabled:group-active:bg-accent/70'
          : 'border-control-border bg-surface-muted group-enabled:group-hover:border-secondary group-enabled:group-active:bg-line'
      "
      aria-hidden="true"
    >
      <span
        class="absolute top-0.5 left-0.5 size-3.5 rounded-full motion-safe:transition-transform"
        :class="model ? 'translate-x-4 bg-primary-contrast' : 'bg-secondary'"
      />
    </span>
    <slot />
  </button>
</template>

<script setup lang="ts">
  const model = defineModel<boolean>({ required: true });
</script>
