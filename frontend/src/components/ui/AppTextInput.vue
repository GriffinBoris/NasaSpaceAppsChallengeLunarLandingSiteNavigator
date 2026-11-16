<template>
  <input
    ref="input"
    v-model="model"
    v-bind="inputAttributes"
    :class="
      cn(
        'min-h-9 w-full rounded-md border border-control-border pointer-coarse:min-h-11 bg-background px-2.5 text-sm text-body focus-visible:outline-2 focus-visible:outline-focus-ring',
        $attrs.class as string
      )
    "
  />
</template>

<script setup lang="ts" generic="T extends string | number">
  import { computed, ref, useAttrs } from "vue";
  import { cn } from "@/utils/className";

  defineOptions({ inheritAttrs: false });

  const model = defineModel<T>({ required: true });
  const attributes = useAttrs();
  const inputAttributes = computed(() => Object.fromEntries(Object.entries(attributes).filter(([name]) => name !== "class")));
  const input = ref<HTMLInputElement>();

  defineExpose({ focus: () => input.value!.focus(), select: () => input.value!.select() });
</script>
