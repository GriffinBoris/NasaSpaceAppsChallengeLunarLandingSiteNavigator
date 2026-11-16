<template>
  <Select
    v-model="model"
    :options="options"
    option-label="label"
    option-value="value"
    option-disabled="disabled"
    checkmark
    :aria-label="label"
    scroll-height="20rem"
    :pt="pt"
    @show="isOpen = true"
    @hide="isOpen = false"
    @keydown.capture="passClosedEscape"
  >
    <template #option="{ option }">
      <span class="flex min-w-0 flex-1 items-baseline justify-between gap-4">
        <span class="truncate">{{ option.label }}</span>
        <span
          v-if="option.description"
          class="shrink-0 text-xs text-secondary"
          >{{ option.description }}</span
        >
      </span>
    </template>
  </Select>
</template>

<script setup lang="ts" generic="T extends string | number">
  import Select from "primevue/select";
  import { ref } from "vue";
  import type { AppSelectOptionInterface } from "@/types/ui/AppSelectOptionInterface";
  import { cn } from "@/utils/className";

  const model = defineModel<T>({ required: true });
  defineProps<{ label: string; options: AppSelectOptionInterface<T>[] }>();
  const isOpen = ref(false);

  function passClosedEscape(event: KeyboardEvent) {
    if (event.key !== "Escape" || isOpen.value) {
      return;
    }

    event.stopImmediatePropagation();
    (event.currentTarget as HTMLElement).parentElement?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", code: "Escape", bubbles: true }));
  }

  const pt = {
    root: {
      class:
        "relative inline-flex min-h-9 min-w-0 pointer-coarse:min-h-11 cursor-pointer items-center rounded-md border border-control-border bg-background text-sm text-body hover:border-secondary has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-focus-ring",
    },
    label: { class: "min-w-0 flex-1 truncate py-1.5 pl-2.5 outline-none" },
    dropdown: { class: "flex w-8 shrink-0 items-center justify-center text-secondary" },
    dropdownIcon: { class: "size-3" },
    overlay: { class: "mt-1 rounded-md border border-line bg-surface p-1 text-body shadow-xl" },
    listContainer: { class: "overflow-auto" },
    list: { class: "space-y-0.5" },
    option: ({ context }: { context: { selected: boolean; focused: boolean; disabled: boolean } }) => ({
      class: cn(
        "flex items-center gap-2 rounded px-2 py-1.5 text-sm whitespace-nowrap",
        context.disabled ? "cursor-not-allowed text-secondary opacity-60" : "cursor-pointer text-body",
        context.focused && !context.disabled && "bg-surface-muted",
        context.selected && "font-medium"
      ),
    }),
    optionCheckIcon: { class: "size-3.5 shrink-0 text-accent" },
    optionBlankIcon: { class: "size-3.5 shrink-0" },
  };
</script>
