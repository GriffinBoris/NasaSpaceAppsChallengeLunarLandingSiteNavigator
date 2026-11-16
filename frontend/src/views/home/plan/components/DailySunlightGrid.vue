<template>
  <div class="space-y-3">
    <div class="overflow-x-auto pb-1">
      <div
        class="grid w-max min-w-full items-center gap-0.5"
        :style="{ gridTemplateColumns: `${labelWidth} repeat(${dayCount}, minmax(0.875rem, 1fr))` }"
        role="group"
        :aria-label="`Daily ${metricLabel(metric).toLowerCase()} by site. Use arrow keys to move between days.`"
        @click="select"
        @focusin="focusDay"
        @mouseover="showDay"
        @keydown="grid.onKeyDown"
      >
        <template
          v-for="(site, row) in sites"
          :key="site.selection.id"
        >
          <button
            type="button"
            class="sticky left-0 z-20 border-l-2 bg-background pr-2 pl-2 text-left text-sm leading-tight line-clamp-2 max-sm:pr-1 max-sm:pl-1.5 max-sm:text-xs focus-visible:outline-2 focus-visible:outline-focus-ring"
            :class="site.selection.id === selectedId ? 'border-accent font-medium text-body' : 'border-transparent text-secondary hover:text-body'"
            :data-site="site.selection.id"
            :aria-pressed="site.selection.id === selectedId"
            :title="site.selection.name"
          >
            {{ site.selection.name }}
          </button>
          <button
            v-for="(day, column) in site.days"
            :key="day.day"
            type="button"
            class="h-6 rounded-[2px] focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus-ring"
            :style="{ background: day.average === null ? NOT_CALCULATED_COLOR : visibilityFractionColor(day.average, metric) }"
            :title="dayTitle(site.selection.name, day)"
            :aria-label="dayTitle(site.selection.name, day)"
            :tabindex="grid.tabIndex(row, column)"
            :data-site="site.selection.id"
            :data-row="row"
            :data-column="column"
            :data-description="dayTitle(site.selection.name, day)"
          />
        </template>
        <span />
        <span
          v-for="(label, index) in dayLabels"
          :key="index"
          class="overflow-visible text-xs whitespace-nowrap text-secondary"
          :class="[
            dayLabelClass(index, dayLabels.length),
            { 'max-sm:invisible': dayTick(index, dayLabels.length) === 'wide', 'sm:invisible': dayTick(index, dayLabels.length) === 'narrow' },
          ]"
          aria-hidden="true"
          >{{ label }}</span
        >
      </div>
    </div>
    <p
      class="min-h-4 text-xs text-secondary"
      aria-hidden="true"
    >
      {{ shownDay || "Point at, tap, or focus a day to see its value." }}
    </p>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from "vue";
  import { useGridNavigation } from "@/composables/useGridNavigation";
  import type { VisibilityMetric } from "@/types/terrain/VisibilityInterface";
  import { metricLabel } from "@/views/home/visibility/visibilityView";
  import type { DaySunlightInterface, PlanSiteInterface } from "@/types/terrain/PlanAnalysisInterface";
  import { dayLabelClass, dayTick, formatDay } from "@/views/home/plan/planTimeline";
  import { NOT_CALCULATED_COLOR, visibilityFractionColor } from "@/views/home/viewer/sunlightOverlay";

  const props = defineProps<{ sites: PlanSiteInterface[]; selectedId: number; metric: VisibilityMetric; labelWidth: string }>();
  const emit = defineEmits<{ select: [selectionId: number] }>();
  const days = computed(() => props.sites[0]?.days ?? []);
  const dayCount = computed(() => days.value.length);
  const grid = useGridNavigation(() => ({ rowCount: props.sites.length, columnCount: dayCount.value }));
  const shownDay = ref("");

  watch([() => props.metric, () => props.sites], () => (shownDay.value = ""));
  const dayLabels = computed(() => days.value.map((day, index) => (dayTick(index, days.value.length) ? formatDay(day.day) : "")));

  function dayTitle(name: string, day: DaySunlightInterface) {
    const date = formatDay(day.day);

    if (day.average === null) {
      return `${name}, ${date}: not calculated`;
    }

    const results = `${day.calculatedCount} ${day.calculatedCount === 1 ? "result" : "results"}`;

    return `${name}, ${date}: ${Math.round(day.average * 100)}% average ${metricLabel(props.metric).toLowerCase()} from ${results}`;
  }

  function showDay(event: Event) {
    const description = (event.target as HTMLElement).closest<HTMLElement>("[data-description]")?.dataset.description;

    if (description) {
      shownDay.value = description;
    }
  }

  function focusDay(event: FocusEvent) {
    grid.onFocusIn(event);
    showDay(event);
  }

  function select(event: MouseEvent) {
    showDay(event);

    const target = (event.target as HTMLElement).closest<HTMLElement>("[data-site]");

    if (target) {
      emit("select", Number(target.dataset.site));
    }
  }
</script>
