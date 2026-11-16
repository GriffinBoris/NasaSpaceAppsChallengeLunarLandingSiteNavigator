<template>
  <MultiSelect
    v-model="model"
    :options="options"
    option-label="label"
    option-value="value"
    display="comma"
    :max-selected-labels="2"
    :selected-items-label="selectedItemsLabel"
    :placeholder="placeholder"
    :show-toggle-all="false"
    :filter="hasFilter"
    :auto-filter-focus="hasFilter"
    filter-placeholder="Search"
    :aria-label="label"
    scroll-height="20rem"
    :pt="pt"
  >
    <template #header>
      <div class="flex items-center justify-between gap-3 px-2 pb-1 text-xs text-secondary">
        <span>{{ model.length }} of {{ options.length }} chosen</span>
        <span class="-mr-2 flex">
          <QuietButton @click="model = options.map((option) => option.value)">All</QuietButton>
          <QuietButton @click="model = []">None</QuietButton>
        </span>
      </div>
    </template>
  </MultiSelect>
</template>

<script setup lang="ts" generic="T extends string | number">
  import MultiSelect from "primevue/multiselect";
  import { computed } from "vue";
  import type { AppSelectOptionInterface } from "@/types/ui/AppSelectOptionInterface";
  import { cn } from "@/utils/className";
  import QuietButton from "./QuietButton.vue";

  const FILTER_MINIMUM_OPTIONS = 8;

  const model = defineModel<T[]>({ required: true });
  const props = defineProps<{ label: string; options: AppSelectOptionInterface<T>[]; placeholder: string; selectedItemsLabel: string }>();

  const hasFilter = computed(() => props.options.length > FILTER_MINIMUM_OPTIONS);

  const pt = {
    root: {
      class:
        "relative inline-flex min-h-9 min-w-0 pointer-coarse:min-h-11 cursor-pointer items-center rounded-md border border-control-border bg-background text-sm text-body hover:border-secondary has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-focus-ring",
    },
    hiddenInputContainer: { class: "sr-only" },
    labelContainer: { class: "min-w-0 flex-1" },
    label: { class: "truncate py-1.5 pl-2.5" },
    dropdown: { class: "flex w-8 shrink-0 items-center justify-center text-secondary" },
    dropdownIcon: { class: "size-3" },
    overlay: { class: "mt-1 rounded-md border border-line bg-surface p-1 text-body shadow-xl" },
    header: { class: "px-1 pb-1" },
    pcFilterContainer: { root: { class: "block" } },
    pcFilter: {
      root: {
        class:
          "min-h-8 w-full rounded-md border border-control-border bg-background px-2.5 text-sm text-body focus-visible:outline-2 focus-visible:outline-focus-ring",
      },
    },
    pcFilterIconContainer: { root: { class: "hidden" } },
    listContainer: { class: "overflow-auto" },
    list: { class: "space-y-0.5" },
    option: ({ context }: { context: { focused: boolean } }) => ({
      class: cn("flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm whitespace-nowrap", context.focused && "bg-surface-muted"),
    }),
    pcOptionCheckbox: ({ context }: { context: { selected: boolean } }) => ({
      root: { class: "relative inline-flex size-4 shrink-0" },
      input: { class: "absolute inset-0 m-0 cursor-pointer opacity-0" },
      box: {
        class: cn(
          "flex size-4 items-center justify-center rounded border",
          context.selected ? "border-accent bg-accent text-background" : "border-secondary bg-background"
        ),
      },
      icon: { class: "size-3" },
    }),
    emptyMessage: { class: "px-2 py-1.5 text-sm text-secondary" },
  };
</script>
