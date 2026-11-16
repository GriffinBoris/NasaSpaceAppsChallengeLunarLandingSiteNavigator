<template>
  <div
    ref="container"
    class="overflow-y-auto rounded focus-visible:outline-2 focus-visible:outline-focus-ring"
    :tabindex="overflows ? 0 : undefined"
    :role="overflows ? 'region' : undefined"
    :aria-label="overflows ? label : undefined"
  >
    <div
      ref="content"
      class="space-y-2"
    >
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { onMounted, onUnmounted, ref } from "vue";

  defineProps<{ label: string }>();
  const container = ref<HTMLDivElement>();
  const content = ref<HTMLDivElement>();
  const overflows = ref(false);
  let observer: ResizeObserver;

  function measure() {
    overflows.value = container.value!.scrollHeight > container.value!.clientHeight;
  }

  onMounted(() => {
    observer = new ResizeObserver(measure);
    observer.observe(container.value!);
    observer.observe(content.value!);
    measure();
  });
  onUnmounted(() => observer.disconnect());
</script>
