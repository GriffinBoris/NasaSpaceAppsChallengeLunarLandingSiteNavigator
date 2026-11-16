<template>
  <section
    class="rounded-xl border border-line bg-surface p-4 text-body shadow-xl outline-none focus-visible:outline-2 focus-visible:outline-focus-ring"
    tabindex="-1"
    :aria-label="title"
    @scroll.passive="isScrolled = ($event.target as HTMLElement).scrollTop > 0"
  >
    <div
      class="sticky -top-4 z-10 -mx-4 -mt-4 flex flex-wrap items-start justify-between gap-x-3 gap-y-2 rounded-t-xl bg-surface px-4 pt-4 pb-1"
      :class="{ 'shadow-[0_10px_10px_-10px_rgb(0_0_0/0.7)]': isScrolled }"
    >
      <div class="min-w-0">
        <h2
          class="truncate text-base font-semibold"
          :title="title"
        >
          {{ title }}
        </h2>
        <slot name="subtitle" />
      </div>
      <div class="ml-auto flex shrink-0 flex-wrap items-center gap-2">
        <slot name="actions" />
        <button
          type="button"
          :class="CLOSE_BUTTON_CLASS"
          :aria-label="closeLabel"
          @click="emit('close')"
        >
          <X
            class="size-4"
            aria-hidden="true"
          />
        </button>
      </div>
    </div>
    <slot />
  </section>
</template>

<script setup lang="ts">
  import { X } from "@lucide/vue";
  import { ref } from "vue";
  import { CLOSE_BUTTON_CLASS } from "./closeButtonClass";

  defineProps<{ title: string; closeLabel: string }>();
  const emit = defineEmits<{ close: [] }>();
  const isScrolled = ref(false);
</script>
