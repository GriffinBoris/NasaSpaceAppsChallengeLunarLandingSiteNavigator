<template>
  <div class="flex flex-col gap-2">
    <template v-if="calendar">
      <div class="overflow-x-auto pb-1">
        <div class="relative w-max min-w-full">
          <div
            class="grid gap-0.5"
            :style="gridTemplate"
            role="group"
            :aria-label="`${metricLabel(metric)} by UTC hour and day. Use arrow keys to move between cells.`"
            @click="selectCell"
            @focusin="focusCell"
            @mouseover="showCell"
            @keydown="grid.onKeyDown"
          >
            <span
              class="sticky left-0 z-20 bg-background pr-1 text-right text-xs leading-none text-secondary"
              aria-hidden="true"
              >UTC</span
            >
            <span
              v-for="(day, column) in calendar.days"
              :key="day.day"
              class="overflow-visible text-xs leading-none whitespace-nowrap text-secondary"
              :class="[
                dayLabelClass(column, calendar.days.length),
                {
                  'max-sm:invisible': dayTick(column, calendar.days.length) === 'wide',
                  'sm:invisible': dayTick(column, calendar.days.length) === 'narrow',
                },
              ]"
              aria-hidden="true"
              >{{ dayTick(column, calendar.days.length) ? formatDay(day.day) : "" }}</span
            >
            <template
              v-for="row in rowCount"
              :key="row"
            >
              <span
                class="sticky left-0 z-20 h-3.5 overflow-visible bg-background pr-1 text-right text-xs leading-none text-secondary tabular-nums"
                aria-hidden="true"
                >{{ rowLabel(row - 1) }}</span
              >
              <button
                v-for="(day, column) in calendar.days"
                :key="day.day"
                type="button"
                class="h-3.5 rounded-[2px] focus-visible:relative focus-visible:z-10 focus-visible:outline-2 focus-visible:outline-focus-ring"
                :class="[
                  isSelectedCell(day.day, row - 1)
                    ? 'relative z-10 outline-2 -outline-offset-1 outline-body'
                    : isOutsidePlan(day.day, row - 1)
                      ? 'cursor-default'
                      : 'hover:outline-1 hover:-outline-offset-1 hover:outline-secondary',
                  isOutsidePlan(day.day, row - 1) ? 'ring-1 ring-secondary/30 ring-inset' : '',
                ]"
                :aria-disabled="isOutsidePlan(day.day, row - 1) || undefined"
                :style="{ background: cellColor(day.day, row - 1, column, day.cells[row - 1] ?? null) }"
                :aria-label="cellTitle(day.day, row - 1, column, day.cells[row - 1] ?? null)"
                :aria-current="isSelectedCell(day.day, row - 1) ? 'time' : undefined"
                :tabindex="grid.tabIndex(row - 1, column)"
                :data-row="row - 1"
                :data-column="column"
                :data-time="day.day + (row - 1) * calendar.columnHours * HOUR"
              />
            </template>
          </div>
          <div
            class="pointer-events-none absolute inset-0 z-[5] grid gap-0.5"
            :style="gridTemplate"
            aria-hidden="true"
          >
            <div
              v-for="segment in highlightSegments"
              :key="segment.column"
              class="rounded-[3px] ring-1 ring-accent"
              :style="{ gridColumn: segment.column + 2, gridRow: `${segment.firstRow + 2} / ${segment.lastRow + 3}` }"
            />
          </div>
        </div>
      </div>
      <p
        class="min-h-15 text-xs text-secondary max-sm:order-first sm:min-h-5"
        aria-hidden="true"
      >
        {{ readout }}
      </p>
    </template>
    <p
      v-else
      class="text-sm text-secondary"
    >
      This plan checks once a day, so there is no time of day to chart. Use a shorter step for an hour-by-hour view.
    </p>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from "vue";
  import { useGridNavigation } from "@/composables/useGridNavigation";
  import type { VisibilityMetric } from "@/types/terrain/VisibilityInterface";
  import { visibilityCalendar } from "@/views/home/plan/planAnalysis";
  import { dayLabelClass, dayTick, formatDay, formatUtc, type SunlightSeries } from "@/views/home/plan/planTimeline";
  import { belowMinimumColor, NOT_CALCULATED_COLOR, OUTSIDE_PLAN_COLOR, visibilityFractionColor } from "@/views/home/viewer/sunlightOverlay";
  import { metricLabel } from "@/views/home/visibility/visibilityView";

  const HOUR = 3600000;
  const MINIMUM_NAMES: Record<VisibilityMetric, string> = { sunlight: "Sun", earth: "Earth", joint: "shared area" };

  const props = withDefaults(
    defineProps<{
      series: SunlightSeries;
      metric: VisibilityMetric;
      schedule: number[];
      stepSeconds: number;
      selectedTime?: number;
      labelWidth?: string;
      misses?: (VisibilityMetric[] | null)[];
      fade?: boolean;
      highlight?: { startTime: number; endTime: number } | null;
    }>(),
    { selectedTime: undefined, labelWidth: "2.25rem", misses: undefined, fade: false, highlight: null }
  );
  const emit = defineEmits<{ select: [timestamp: number] }>();
  const calendar = computed(() => visibilityCalendar(props.schedule, props.series, props.stepSeconds));

  const matchCalendar = computed(() =>
    props.misses
      ? visibilityCalendar(
          props.schedule,
          props.misses.map((missed) => (missed === null ? null : Number(missed.length === 0))),
          props.stepSeconds
        )
      : null
  );
  const rowCount = computed(() => calendar.value?.days[0]?.cells.length ?? 0);
  const gridTemplate = computed(() => ({
    gridTemplateColumns: `${props.labelWidth} repeat(${calendar.value?.days.length ?? 0}, minmax(0.875rem, 1fr))`,
    gridTemplateRows: `0.8125rem repeat(${rowCount.value}, 0.875rem)`,
  }));
  const highlightSegments = computed(() => {
    const window = props.highlight;

    if (!window || !calendar.value) {
      return [];
    }

    const span = calendar.value.columnHours * HOUR;

    return calendar.value.days.flatMap((day, column) => {
      const rows = Array.from({ length: rowCount.value }, (_, row) => row).filter((row) => {
        const start = day.day + row * span;

        return start >= window.startTime && start < window.endTime;
      });

      return rows.length ? [{ column, firstRow: rows[0]!, lastRow: rows[rows.length - 1]! }] : [];
    });
  });
  const grid = useGridNavigation(() => ({ rowCount: rowCount.value, columnCount: calendar.value?.days.length ?? 0 }));

  const shownCell = ref<{ row: number; column: number } | null>(null);

  const readout = computed(() => {
    const selected = props.selectedTime === undefined ? null : `Maps show ${formatUtc(props.selectedTime)}.`;
    const day = shownCell.value && calendar.value?.days[shownCell.value.column];

    if (!shownCell.value || !day) {
      return selected ? `${selected} Select a time to change them.` : "Select a time to update the maps.";
    }

    const { row, column } = shownCell.value;
    const label = cellTitle(day.day, row, column, day.cells[row] ?? null);

    if (!selected || isSelectedCell(day.day, row)) {
      return `${label}.`;
    }

    return `${label}. ${selected}`;
  });

  function rowLabel(row: number) {
    const hours = row * calendar.value!.columnHours;

    return hours % 6 === 0 ? String(hours).padStart(2, "0") : "";
  }

  function cellStart(day: number, row: number) {
    return day + row * calendar.value!.columnHours * HOUR;
  }

  function isOutsidePlan(day: number, row: number) {
    return isOutsidePlanAt(cellStart(day, row));
  }

  function isOutsidePlanAt(start: number) {
    return start + calendar.value!.columnHours * HOUR <= props.schedule[0]! || start > props.schedule[props.schedule.length - 1]!;
  }

  function isSelectedCell(day: number, row: number) {
    if (props.selectedTime === undefined) {
      return false;
    }

    const start = cellStart(day, row);

    return props.selectedTime >= start && props.selectedTime < start + calendar.value!.columnHours * HOUR;
  }

  function cellMatch(column: number, row: number) {
    return matchCalendar.value?.days[column]?.cells[row] ?? null;
  }

  function cellColor(day: number, row: number, column: number, fraction: number | null) {
    if (fraction === null) {
      return isOutsidePlan(day, row) ? OUTSIDE_PLAN_COLOR : NOT_CALCULATED_COLOR;
    }

    const color = visibilityFractionColor(fraction, props.metric);

    return props.fade && cellMatch(column, row) === 0 ? belowMinimumColor(color) : color;
  }

  function cellTitle(day: number, row: number, column: number, fraction: number | null) {
    const start = cellStart(day, row);

    if (isOutsidePlanAt(start)) {
      return `${formatUtc(start)} is ${start < props.schedule[0]! ? "before the plan starts" : "after the plan ends"}`;
    }

    const match = cellMatch(column, row);

    const firstSample = Math.max(0, Math.ceil((start - props.schedule[0]!) / (props.stepSeconds * 1000)));
    const missed = match === 0 ? (props.misses![firstSample] ?? []) : [];

    const value = fraction === null ? "not calculated" : `${Math.floor(fraction * 1000 + 1e-9) / 10}%`;

    const windowNote = props.highlight && start >= props.highlight.startTime && start < props.highlight.endTime ? ", in the best window" : "";

    return `${formatUtc(start)}: ${metricLabel(props.metric).toLowerCase()} ${value}${minimumNote(match, missed)}${windowNote}`;
  }

  function minimumNote(match: number | null, missed: VisibilityMetric[]) {
    if (match === null) {
      return "";
    }
    if (match > 0) {
      return ", meets your minimums";
    }
    if (!missed.length) {
      return ", below your minimums";
    }

    const names = missed.map((metric) => MINIMUM_NAMES[metric]);
    const list = names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}` : names[0];

    return `, below the ${list} minimum${names.length > 1 ? "s" : ""}`;
  }

  function showCell(event: Event) {
    const cell = (event.target as HTMLElement).closest<HTMLElement>("[data-time]");

    if (cell) {
      shownCell.value = { row: Number(cell.dataset.row), column: Number(cell.dataset.column) };
    }
  }

  function focusCell(event: FocusEvent) {
    grid.onFocusIn(event);
    showCell(event);
  }

  function selectCell(event: MouseEvent) {
    showCell(event);

    const target = (event.target as HTMLElement).closest<HTMLElement>("[data-time]");

    if (target && !isOutsidePlanAt(Number(target.dataset.time))) {
      emit("select", Number(target.dataset.time));
    }
  }
</script>
