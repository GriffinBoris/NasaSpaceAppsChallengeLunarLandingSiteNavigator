<template>
  <dl class="grid gap-2 tabular-nums sm:grid-cols-2 lg:grid-cols-4 [&_dt]:flex-none">
    <StatTile
      label="Best window"
      size="large"
      :value="bestWindow ? windowDuration(bestWindow) : 'None'"
      :note="bestWindow ? formatUtcRange(bestWindow.startTime, bestWindow.endTime) : noWindowText"
    >
      <template v-if="bestWindow">
        <dd class="text-xs text-secondary">{{ windowAverages(bestWindow) }}</dd>
        <dd class="mt-auto pt-1">
          <button
            type="button"
            :class="LINK_CLASS"
            @click="emit('select', bestWindow.startTime)"
          >
            Show on maps
          </button>
        </dd>
      </template>
      <dd
        v-else-if="optimal.calculatedMilliseconds"
        class="mt-auto pt-1"
      >
        <button
          type="button"
          :class="LINK_CLASS"
          @click="emit('adjustMinimums')"
        >
          Adjust minimums
        </button>
      </dd>
    </StatTile>
    <StatTile
      label="Meeting your minimums"
      size="large"
      :value="matchingDuration"
      :note="matchingNote"
    >
      <dd
        v-if="optimal.matchingMilliseconds"
        class="mt-auto pt-2"
        aria-hidden="true"
      >
        <div class="h-1.5 overflow-hidden rounded-full bg-line">
          <div
            class="h-full rounded-full bg-secondary"
            :style="{ width: `${matchingShare * 100}%` }"
          />
        </div>
      </dd>
    </StatTile>

    <StatTile
      :label="earthChange.label"
      size="large"
      :value="earthChange.value"
      :note="`From ${formatUtc(schedule[timeIndex]!)} at the site center`"
    >
      <dd class="text-xs text-secondary">{{ earthWindowsText }}</dd>
    </StatTile>
    <StatTile
      label="Longest dark"
      size="large"
      :value="longestDark ? longestDark.duration : darknessValue"
      :note="longestDark ? longestDark.range : noDarknessText"
    >
      <dd
        v-if="longestDark"
        class="mt-auto pt-1"
      >
        <button
          type="button"
          :class="LINK_CLASS"
          @click="emit('select', longestDark.start)"
        >
          Show on maps
        </button>
      </dd>
    </StatTile>
  </dl>
</template>

<script setup lang="ts">
  import { computed } from "vue";
  import StatTile from "@/components/ui/StatTile.vue";
  import type { OptimalTimesInterface, OptimalWindowInterface } from "@/types/terrain/OptimalTimesInterface";
  import type { PlanSiteInterface } from "@/types/terrain/PlanAnalysisInterface";
  import type { SunlightFrameInterface } from "@/types/terrain/SunlightFrameInterface";
  import type { SunlightStudyInterface } from "@/types/terrain/SunlightStudyInterface";
  import { earthCenterSeries, earthMetrics, nextEarthChange } from "@/views/home/visibility/earthAnalysis";
  import { formatOptimalDuration } from "../optimalTimes";
  import { runDurationLabel } from "../planAnalysis";
  import { formatUtc, formatUtcRange } from "../planTimeline";

  const LINK_CLASS =
    "rounded text-sm text-accent underline underline-offset-2 hover:text-body focus-visible:outline-2 focus-visible:outline-focus-ring pointer-coarse:min-h-11";

  const props = defineProps<{
    study: SunlightStudyInterface;
    frames: SunlightFrameInterface[];
    site: PlanSiteInterface;
    schedule: number[];
    timeIndex: number;
    windowSeconds: number;
    optimal: OptimalTimesInterface;
  }>();
  const emit = defineEmits<{ select: [timestamp: number]; adjustMinimums: [] }>();
  const planEnd = computed(() => props.schedule[0]! + props.windowSeconds * 1000);
  const isRegion = computed(() => props.site.selection.radiusMeters !== null);

  const bestWindow = computed(() => props.optimal.bestWindow);
  const noWindowText = computed(() => (props.optimal.calculatedMilliseconds ? "No hour meets every minimum" : "No results yet"));
  const matchingShare = computed(() =>
    props.optimal.calculatedMilliseconds ? props.optimal.matchingMilliseconds / props.optimal.calculatedMilliseconds : 0
  );
  const matchingDuration = computed(() => {
    if (props.optimal.matchingMilliseconds) {
      return formatOptimalDuration(props.optimal.matchingMilliseconds);
    }

    return props.optimal.calculatedMilliseconds ? "0 h" : "None";
  });

  const matchingNote = computed(() => {
    const { calculatedMilliseconds, matchingDayCount } = props.optimal;

    if (!calculatedMilliseconds) {
      return "No results yet";
    }

    const share = `${percent(matchingShare.value)} of ${formatOptimalDuration(calculatedMilliseconds)} checked`;

    return matchingDayCount ? `${share}, on ${matchingDayCount} ${matchingDayCount === 1 ? "day" : "days"}` : share;
  });

  const earthSeries = computed(() => earthCenterSeries(props.study, props.frames, props.site.selection.id));
  const earthChange = computed(() => nextEarthChange(earthSeries.value, props.timeIndex, props.study.stepSeconds));

  const earthWindowsText = computed(() => {
    const windows = earthMetrics(earthSeries.value).windows;
    const first = windows[0];

    if (!first) {
      return "No visible windows in the calculated samples";
    }

    const endIndex = first.startIndex + first.length;
    const end = endIndex === props.schedule.length ? planEnd.value : props.schedule[endIndex]!;
    const edge = first.startIndex === 0 || endIndex === props.schedule.length ? " (may extend beyond the plan)" : "";
    const more = windows.length > 1 ? `, plus ${windows.length - 1} more` : "";

    return `Visible ${formatUtcRange(props.schedule[first.startIndex]!, end)}${edge}${more}`;
  });

  const noDarknessText = computed(() => {
    const { calculatedCount } = props.site.metrics;

    if (!calculatedCount) {
      return "No results yet for this site";
    }

    return calculatedCount < props.schedule.length ? "No fully dark results so far" : "No sample in this plan is fully dark";
  });
  const darknessValue = computed(() => (props.site.metrics.calculatedCount === props.schedule.length ? "Never" : "None so far"));
  const longestDark = computed(() => {
    const run = props.site.metrics.darkRuns[0];

    if (!run) {
      return null;
    }

    const start = props.schedule[run.startIndex]!;

    const end = Math.min(start + run.length * props.study.stepSeconds * 1000, planEnd.value);

    return {
      start,
      range: formatUtcRange(start, end),
      duration: runDurationLabel(run, props.schedule.length, props.study.stepSeconds, props.windowSeconds),
    };
  });

  function windowDuration(window: OptimalWindowInterface) {
    const duration = formatOptimalDuration(window.durationMilliseconds);

    return window.startBoundary === "plan" || window.endBoundary === "plan" ? `At least ${duration}` : duration;
  }

  function windowAverages(window: OptimalWindowInterface) {
    const shared = isRegion.value ? `, Both ${percent(window.averageJointShare)}` : "";

    return `Sun ${percent(window.averageSunFraction)}, Earth ${percent(window.averageEarthFraction)}${shared}`;
  }

  function percent(fraction: number) {
    return `${Math.round(fraction * 100)}%`;
  }
</script>
