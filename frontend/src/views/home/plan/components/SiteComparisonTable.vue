<template>
  <dl
    v-if="sites.length === 1"
    class="grid grid-cols-2 gap-2"
  >
    <StatTile
      v-for="(column, index) in COLUMNS"
      :key="column"
      :label="column"
      :value="values(sites[0]!)[index]!"
      size="large"
      :class="COLUMNS.length % 2 && index === COLUMNS.length - 1 ? 'col-span-2' : ''"
    />
  </dl>
  <div
    v-else
    class="space-y-2"
  >
    <div class="overflow-x-auto">
      <table class="w-full min-w-[40rem] border-collapse text-sm">
        <thead>
          <tr class="border-b border-line text-xs text-secondary">
            <th
              scope="col"
              class="sticky left-0 z-10 bg-background py-2 pr-3 text-left font-normal"
            >
              Site
            </th>
            <th
              v-for="column in COLUMNS"
              :key="column"
              scope="col"
              class="px-3 py-2 text-right font-normal whitespace-nowrap"
            >
              {{ column }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="site in sites"
            :key="site.selection.id"
            class="border-b border-line"
            :class="site.selection.id === selectedId ? 'bg-surface-muted' : ''"
          >
            <th
              scope="row"
              class="sticky left-0 z-10 py-2 pr-3 text-left font-normal"
              :class="site.selection.id === selectedId ? 'bg-surface-muted' : 'bg-background'"
            >
              <button
                type="button"
                class="border-l-2 pl-2 text-left pointer-coarse:min-h-11 max-sm:w-28 sm:whitespace-nowrap focus-visible:outline-2 focus-visible:outline-focus-ring"
                :class="site.selection.id === selectedId ? 'border-accent font-medium text-body' : 'border-transparent text-body hover:text-accent'"
                :aria-pressed="site.selection.id === selectedId"
                @click="emit('select', site.selection.id)"
              >
                {{ site.selection.name }}
              </button>
            </th>
            <td
              v-for="(value, index) in values(site)"
              :key="index"
              class="px-3 py-2 text-right whitespace-nowrap tabular-nums"
              :class="value === '–' ? 'text-secondary' : 'text-body'"
            >
              {{ value }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed } from "vue";
  import type { PlanSiteInterface, SunlightRunInterface } from "@/types/terrain/PlanAnalysisInterface";
  import type { SunlightFrameInterface } from "@/types/terrain/SunlightFrameInterface";
  import type { SunlightStudyInterface } from "@/types/terrain/SunlightStudyInterface";
  import { earthCenterSeries, earthMetrics } from "@/views/home/visibility/earthAnalysis";
  import StatTile from "@/components/ui/StatTile.vue";
  import { runDurationLabel } from "@/views/home/plan/planAnalysis";
  import { averageSun, studySchedule, studySeries } from "@/views/home/plan/planTimeline";

  const COLUMNS = [
    "Average Sun",
    "Fully lit checks",
    "Longest dark",
    "Longest with Sun",
    "Earth visible (center)",
    "Longest Earth block (center)",
    "Sun + Earth (area)",
  ];

  const props = defineProps<{
    sites: PlanSiteInterface[];
    selectedId: number;
    stepSeconds: number;
    study: SunlightStudyInterface;
    frames: SunlightFrameInterface[];
  }>();
  const emit = defineEmits<{ select: [selectionId: number] }>();
  const earthBySite = computed(() => {
    const metricsBySite = new Map<number, ReturnType<typeof earthMetrics>>();

    for (const site of props.sites) {
      const series = earthCenterSeries(props.study, props.frames, site.selection.id);

      metricsBySite.set(site.selection.id, earthMetrics(series));
    }

    return metricsBySite;
  });
  const jointBySite = computed(() => studySeries(props.study, props.frames, "joint"));

  function percent(fraction: number | null) {
    return fraction === null ? "–" : `${Math.round(fraction * 100)}%`;
  }

  function duration(run: SunlightRunInterface | null | undefined, hasResults: boolean) {
    if (!hasResults) {
      return "–";
    }

    if (!run) {
      return "Never";
    }

    const windowSeconds = (Date.parse(props.study.endTime) - Date.parse(props.study.startTime)) / 1000;

    return runDurationLabel(run, studySchedule(props.study).length, props.stepSeconds, windowSeconds);
  }

  function values(site: PlanSiteInterface) {
    const { metrics } = site;
    const hasResults = metrics.calculatedCount > 0;
    const earth = earthBySite.value.get(site.selection.id)!;

    return [
      percent(metrics.average),
      percent(metrics.fullyLitShare),
      duration(metrics.darkRuns[0], hasResults),
      duration(metrics.longestSunlit, hasResults),
      percent(earth.availableShare),
      duration(earth.outages[0], earth.availableShare !== null),
      percent(averageSun(jointBySite.value.get(site.selection.id)!)),
    ];
  }
</script>
