<template>
  <AppButton
    :disabled="disabled"
    aria-haspopup="menu"
    :aria-expanded="isOpen"
    @click="popover?.toggle($event)"
  >
    <span class="max-w-48 truncate">{{ label }}</span>
    <ChevronDown aria-hidden="true" />
  </AppButton>
  <AppPopover
    ref="popover"
    @show="isOpen = true"
    @hide="isOpen = false"
  >
    <ul
      role="menu"
      :aria-label="label"
      class="min-w-44 space-y-0.5"
      @keydown="moveFocus"
    >
      <li
        v-for="item in items"
        :key="item.value"
        role="none"
      >
        <button
          type="button"
          :role="selected === undefined ? 'menuitem' : 'menuitemradio'"
          :aria-checked="selected === undefined ? undefined : item.value === selected"
          class="w-full rounded px-3 py-1.5 text-left text-sm pointer-coarse:min-h-11 hover:bg-surface-muted focus-visible:outline-2 focus-visible:outline-focus-ring"
          :class="item.value === selected ? 'bg-surface-muted font-medium text-body' : 'text-body'"
          @click="choose(item.value)"
        >
          {{ item.label }}
        </button>
      </li>
    </ul>
  </AppPopover>
</template>

<script setup lang="ts">
  import { ChevronDown } from "@lucide/vue";
  import { ref } from "vue";
  import AppButton from "./AppButton.vue";
  import AppPopover from "./AppPopover.vue";

  defineProps<{ label: string; items: { label: string; value: string }[]; selected?: string; disabled?: boolean }>();
  const emit = defineEmits<{ select: [value: string] }>();
  const popover = ref<InstanceType<typeof AppPopover>>();
  const isOpen = ref(false);

  function moveFocus(event: KeyboardEvent) {
    const items = Array.from((event.currentTarget as HTMLElement).querySelectorAll<HTMLElement>("[role^='menuitem']"));
    const index = items.indexOf(document.activeElement as HTMLElement);
    const nextIndex = { ArrowDown: index + 1, ArrowUp: index - 1, Home: 0, End: items.length - 1 }[event.key];

    if (nextIndex === undefined) {
      return;
    }

    event.preventDefault();
    items[(nextIndex + items.length) % items.length]?.focus();
  }

  function choose(value: string) {
    popover.value!.hide();
    emit("select", value);
  }
</script>
