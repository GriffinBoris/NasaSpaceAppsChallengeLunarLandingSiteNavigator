<template>
  <div class="mx-auto max-w-7xl space-y-6 px-4 py-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="min-w-0 space-y-3">
        <AppButton
          tone="ghost"
          class="-ml-2"
          @click="router.push({ name: 'home' })"
        >
          <ArrowLeft aria-hidden="true" />
          Back to the Moon
        </AppButton>
        <div>
          <h1
            ref="heading"
            class="text-2xl font-semibold break-words text-body outline-none"
            tabindex="-1"
          >
            {{ summary?.name ?? "Plan" }}
          </h1>
          <dl
            v-if="summary"
            class="mt-1 flex flex-wrap gap-x-5 gap-y-1 text-sm"
          >
            <div
              v-for="item in details"
              :key="item.label"
              class="flex gap-1.5"
            >
              <dt class="text-secondary">{{ item.label }}</dt>
              <dd class="text-balance text-body tabular-nums">{{ item.value }}</dd>
            </div>
          </dl>
        </div>
      </div>
      <div
        v-if="summary"
        class="flex flex-wrap items-center gap-2"
      >
        <AppButton
          v-if="isProcessing"
          :disabled="summary.status === 'stopping' || isPending"
          @click="store.stopStudy(studyId)"
          >Stop</AppButton
        >
        <AppButton
          v-else-if="summary.status !== 'complete'"
          :disabled="isPending"
          @click="store.calculateStudy(studyId, summary.workerCount)"
          >{{ calculateLabel(summary) }}</AppButton
        >
        <AppButton
          :disabled="isProcessing || isPending"
          @click="emit('edit', studyId)"
          >Edit</AppButton
        >
        <ConfirmButton
          v-if="isConfirmingDelete"
          v-model:confirming="isConfirmingDelete"
          label="Delete"
          confirm-label="Delete plan"
          @confirm="remove"
        />
        <AppMenuButton
          v-else-if="moreItems.length"
          label="More"
          :items="moreItems"
          @select="chooseMore"
        />
        <AppButton
          tone="primary"
          @click="showOnMoon"
          >Show on Moon</AppButton
        >
      </div>
    </div>
    <div
      v-if="activityText"
      class="space-y-2"
    >
      <div
        v-if="summary?.status === 'running' || summary?.status === 'stopping'"
        class="h-1 overflow-hidden rounded-full bg-line"
        role="progressbar"
        :aria-valuenow="summary.progress?.percentage ?? 0"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-label="summary.progress?.phase === 'preparing' ? 'Terrain preparation progress' : 'Plan calculation progress'"
      >
        <div
          class="h-full bg-accent"
          :style="{ width: `${summary.progress?.percentage ?? 0}%` }"
        />
      </div>
      <p
        class="text-sm text-secondary"
        role="status"
      >
        {{ activityText }}
      </p>
    </div>
    <div
      v-if="loadError"
      class="space-y-2"
    >
      <AlertBanner :message="loadError" />
      <AppButton @click="load">Try again</AppButton>
    </div>
    <StoreErrorNotice v-else-if="store.errorMessage" />
    <AlertBanner
      v-if="summary?.status === 'failed' && summary.errorMessage"
      :message="summary.errorMessage"
    />
    <div
      v-if="isLoading"
      class="flex justify-center py-16 text-sm text-secondary"
    >
      <LoadingSpinner
        size="large"
        label="Loading plan results"
        class="flex-col gap-3"
      />
    </div>
    <template v-else-if="study && selectedSite">
      <div
        v-if="sites.length > 1"
        class="w-fit max-w-3xl space-y-1 rounded-lg border border-line bg-surface px-4 py-3"
      >
        <p class="text-xs font-medium text-secondary">Across all sites</p>
        <p class="text-base font-semibold text-body">{{ keepDurationsTogether(insight.lead) }}</p>
        <p
          v-if="insight.detail"
          class="text-sm text-secondary"
        >
          {{ keepDurationsTogether(insight.detail) }}
        </p>
      </div>
      <section
        v-if="sites.length > 1"
        aria-labelledby="sites-compared-heading"
        class="space-y-3"
      >
        <div>
          <h2
            id="sites-compared-heading"
            class="text-lg font-semibold text-body"
          >
            Sites compared
          </h2>
          <p class="text-sm text-secondary">
            Select a site for details. Sun columns average the area; "center" columns use the site's center.<span class="sm:hidden">
              Scroll sideways for more columns.</span
            >
          </p>
        </div>
        <SiteComparisonTable
          :sites="sites"
          :selected-id="selectedSite.selection.id"
          :step-seconds="study.stepSeconds"
          :study="study"
          :frames="detail!.frames"
          @select="selectedId = $event"
        />
      </section>
      <SiteVisibilityPanels
        ref="panels"
        v-model:time-index="timeIndex"
        :study="study"
        :site="selectedSite"
        :frames="detail!.frames"
        :schedule="schedule"
      >
        <template #overview>
          <section
            aria-labelledby="selected-site-heading"
            class="space-y-3 border-t border-line pt-6"
          >
            <div>
              <h2
                id="selected-site-heading"
                class="text-lg font-semibold text-body"
              >
                {{ selectedSite.selection.name }}
              </h2>
              <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-secondary">
                <span class="font-mono">{{ formatCoordinates(selectedSite.selection.latitude, selectedSite.selection.longitude) }}</span>
                <span>{{ formatRadius(selectedSite.selection.radiusMeters) }}</span>
              </div>
            </div>
            <PlanSiteSummary
              :study="study"
              :frames="detail!.frames"
              :site="selectedSite"
              :schedule="schedule"
              :time-index="timeIndex"
              :window-seconds="windowSeconds"
              :optimal="optimal"
              @select="showTimeOnMaps"
              @adjust-minimums="minimums?.focus(scrollBehavior())"
            />
            <SiteComparisonTable
              v-if="sites.length === 1"
              class="lg:grid-cols-4"
              :sites="[selectedSite]"
              :selected-id="selectedSite.selection.id"
              :step-seconds="study.stepSeconds"
              :study="study"
              :frames="detail!.frames"
            />
          </section>
        </template>
        <template #calendar>
          <section
            aria-labelledby="whole-plan-heading"
            class="space-y-3"
          >
            <div>
              <h2
                id="whole-plan-heading"
                class="text-lg font-semibold text-body"
              >
                By hour
              </h2>
              <p class="text-xs text-secondary">{{ selectedSite.selection.name }}, whole plan</p>
            </div>
            <VisibilityMinimums
              ref="minimums"
              v-model="criteria"
              v-model:highlight="isHighlighting"
              :result="optimal"
              :radius-meters="selectedSite.selection.radiusMeters"
              :step-seconds="study.stepSeconds"
            />

            <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
              <VisibilityLegend
                :metric="heatMetric"
                :filtered="showsMatches"
                :has-missing="heatSites.some((site) => site.series.includes(null))"
              />
              <div
                class="flex rounded-md border border-control-border p-0.5 max-sm:order-first"
                role="group"
                aria-label="Value shown"
              >
                <button
                  v-for="option in METRIC_OPTIONS"
                  :key="option.value"
                  type="button"
                  class="rounded px-3 py-1 text-sm focus-visible:outline-2 focus-visible:outline-focus-ring pointer-coarse:min-h-11"
                  :class="
                    heatMetric === option.value
                      ? 'bg-surface-muted font-medium text-body active:bg-line'
                      : 'text-secondary hover:text-body active:bg-line'
                  "
                  :aria-pressed="heatMetric === option.value"
                  @click="heatMetric = option.value"
                >
                  {{ option.label }}
                </button>
              </div>
            </div>
            <VisibilityCalendar
              :series="heatSeries"
              :metric="heatMetric"
              :schedule="schedule"
              :step-seconds="study.stepSeconds"
              :selected-time="schedule[timeIndex]"
              :label-width="sites.length > 1 ? SITE_LABEL_WIDTH : undefined"
              :misses="optimal.misses"
              :fade="showsMatches"
              :highlight="showsMatches ? optimal.bestWindow : null"
              @select="selectTime"
            />
            <template v-if="sites.length > 1">
              <h3 class="text-base font-semibold text-body">Daily average by site</h3>
              <DailySunlightGrid
                :sites="heatSites"
                :metric="heatMetric"
                :selected-id="selectedSite.selection.id"
                :label-width="SITE_LABEL_WIDTH"
                @select="selectedId = $event"
              />
            </template>
          </section>
        </template>
        <template #horizon="{ sun, earth, directions, timeText }">
          <SiteHorizonView
            :study-id="study.id"
            :selection-id="selectedSite.selection.id"
            :result-revision="study.resultRevision"
            :sun="sun"
            :earth="earth"
            :directions="directions"
            :time-text="timeText"
          />
        </template>
      </SiteVisibilityPanels>
    </template>
  </div>
</template>

<script setup lang="ts">
  import LoadingSpinner from "@/components/ui/LoadingSpinner.vue";
  import { computed, nextTick, onMounted, onUnmounted, ref, shallowRef, watch } from "vue";
  import { ArrowLeft } from "@lucide/vue";
  import { useRouter } from "vue-router";
  import { formatCoordinates, formatRadius } from "@/views/home/sites/coordinateFormat";
  import AlertBanner from "@/components/ui/AlertBanner.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import AppMenuButton from "@/components/ui/AppMenuButton.vue";
  import ConfirmButton from "@/components/ui/ConfirmButton.vue";
  import type { PlanSiteInterface } from "@/types/terrain/PlanAnalysisInterface";
  import type { SunlightStudyDetailInterface } from "@/types/terrain/SunlightFrameInterface";
  import { api } from "@/utils/api";
  import { getApiErrorStatus, getFirstApiErrorMessage } from "@/utils/errorHandling";
  import type { VisibilityMetric } from "@/types/terrain/VisibilityInterface";
  import { dailySunlight, planInsight, siteMetrics } from "@/views/home/plan/planAnalysis";
  import { planResultsCsv } from "@/views/home/plan/planCsv";
  import { mergeFrames } from "./planResults";
  import {
    calculateLabel,
    describePlanStatus,
    describeQueue,
    formatDuration,
    formatWindow,
    isPlanProcessing,
    studySchedule,
    studySeries,
  } from "@/views/home/plan/planTimeline";
  import { useSunlightStore } from "@/views/home/sunlightStore";
  import type { MoonViewQueryInterface } from "@/views/home/moonViewQuery";
  import DailySunlightGrid from "./components/DailySunlightGrid.vue";
  import VisibilityCalendar from "./components/VisibilityCalendar.vue";
  import VisibilityLegend from "./components/VisibilityLegend.vue";
  import SiteVisibilityPanels from "./components/SiteVisibilityPanels.vue";
  import SiteHorizonView from "./components/SiteHorizonView.vue";
  import PlanSiteSummary from "./components/PlanSiteSummary.vue";
  import VisibilityMinimums from "./components/VisibilityMinimums.vue";
  import { optimalTimes } from "./optimalTimes";
  import type { OptimalTimeCriteriaInterface } from "@/types/terrain/OptimalTimesInterface";
  import SiteComparisonTable from "./components/SiteComparisonTable.vue";
  import StoreErrorNotice from "@/views/home/components/StoreErrorNotice.vue";

  const REFRESH_DELAY_MS = 1500;
  const METRIC_OPTIONS: { value: VisibilityMetric; label: string }[] = [
    { value: "sunlight", label: "Sun" },
    { value: "earth", label: "Earth" },
    { value: "joint", label: "Both" },
  ];
  const APPLICATION_TITLE = "Lunar Landing Site Navigator";

  const SITE_LABEL_WIDTH = "clamp(4.5rem, 22vw, 12rem)";

  const props = defineProps<{ studyId: number }>();
  const emit = defineEmits<{ edit: [studyId: number]; showOnMoon: [view: MoonViewQueryInterface] }>();
  const router = useRouter();
  const store = useSunlightStore();
  const detail = shallowRef<SunlightStudyDetailInterface | null>(null);
  const isLoading = ref(true);
  const loadError = ref("");
  const selectedId = ref<number | null>(null);

  const timeIndex = ref(0);
  const panels = ref<InstanceType<typeof SiteVisibilityPanels>>();
  const minimums = ref<InstanceType<typeof VisibilityMinimums>>();
  const heading = ref<HTMLHeadingElement>();

  const summary = computed(() => store.studies.find((study) => study.id === props.studyId) ?? detail.value?.study ?? null);
  const study = computed(() => detail.value?.study ?? null);
  const isProcessing = computed(() => summary.value !== null && isPlanProcessing(summary.value));

  const activityText = computed(() => {
    const current = summary.value;

    if (!current) {
      return "";
    }

    switch (current.status) {
      case "pending":
        return current.savedResults ? "Saved results are kept. Continue calculates only missing sunlight and Earth results." : "";
      case "queued":
        return `${describeQueue(current, store.studies)}. Results appear here as they finish, even if you close this tab.`;
      case "running": {
        const saved = `${current.completedFrames.toLocaleString("en-US")} of ${current.expectedFrames.toLocaleString("en-US")} results saved.`;
        const stage = current.progress?.stage;

        return stage && stage !== "Queued" ? `${saved} ${stage}.` : saved;
      }
      case "stopping":
        return "Stopping after the current step. Finished results are kept.";
      default:
        return "";
    }
  });
  const isPending = computed(() => store.pendingStudyIds.has(props.studyId));
  const isConfirmingDelete = ref(false);

  const moreItems = computed(() => [
    ...(detail.value?.frames.length ? [{ label: "Export CSV", value: "export" }] : []),
    ...(isProcessing.value || isPending.value ? [] : [{ label: "Delete plan", value: "delete" }]),
  ]);

  function chooseMore(action: string) {
    if (action === "export") {
      exportCsv();
    }
    if (action === "delete") {
      isConfirmingDelete.value = true;
    }
  }

  const schedule = computed(() => (study.value ? studySchedule(study.value) : []));
  const windowSeconds = computed(() => (study.value ? (Date.parse(study.value.endTime) - Date.parse(study.value.startTime)) / 1000 : 0));

  function planSites(metric: VisibilityMetric): PlanSiteInterface[] {
    if (!study.value || !detail.value) {
      return [];
    }

    const seriesBySite = studySeries(study.value, detail.value.frames, metric);

    return study.value.selections.map((selection) => {
      const series = seriesBySite.get(selection.id)!;

      return { selection, series, metrics: siteMetrics(series), days: dailySunlight(schedule.value, series) };
    });
  }

  const sites = computed(() => planSites("sunlight"));
  const selectedSite = computed(() => sites.value.find((site) => site.selection.id === selectedId.value) ?? sites.value[0]);
  const heatMetric = ref<VisibilityMetric>("sunlight");
  const heatSites = computed(() => (heatMetric.value === "sunlight" ? sites.value : planSites(heatMetric.value)));
  const heatSeries = computed(() => heatSites.value.find((site) => site.selection.id === selectedSite.value!.selection.id)!.series);

  const criteria = ref<OptimalTimeCriteriaInterface>({ minimumSunFraction: 0.1, minimumEarthFraction: 0.1, minimumJointShare: 0.01 });
  const optimal = computed(() => optimalTimes(study.value!, detail.value!.frames, selectedSite.value!.selection.id, criteria.value));
  const isHighlighting = ref(true);

  const showsMatches = computed(() => isHighlighting.value && optimal.value.matchingMilliseconds > 0);

  const insight = computed(() => {
    if (!sites.value.some((site) => site.metrics.calculatedCount > 0)) {
      return {
        lead: "No results yet.",
        detail: isProcessing.value ? "They appear here as the plan calculates." : "Calculate this plan to see how its sites fare.",
      };
    }

    return planInsight(
      sites.value.map((site) => ({ name: site.selection.name, metrics: site.metrics })),
      schedule.value,
      study.value!.stepSeconds,
      windowSeconds.value
    );
  });

  function keepDurationsTogether(text: string) {
    return text.replace(/(\d) (d|h|min|s)\b/g, "$1\u00a0$2").replace(/\b(d|h) (\d)/g, "$1\u00a0$2");
  }

  const details = computed(() => {
    const current = summary.value!;

    return [
      { label: "Window", value: formatWindow(current.startTime, current.endTime) },
      { label: "Step", value: formatDuration(current.stepSeconds) },
      { label: "Sites", value: String(current.selections.length) },

      ...(current.status === "complete"
        ? []
        : [{ label: "Results", value: `${current.completedFrames.toLocaleString("en-US")} of ${current.expectedFrames.toLocaleString("en-US")}` }]),
      ...(isPlanProcessing(current) || current.status === "complete" ? [] : [{ label: "Status", value: describePlanStatus(current) }]),
    ];
  });

  let request = new AbortController();
  let refreshTimer: ReturnType<typeof setTimeout> | undefined;

  async function load() {
    request.abort();
    request = new AbortController();

    const current = request;

    loadError.value = "";

    try {
      const result = await api.studies.detail(props.studyId, current.signal, detail.value?.study.resultRevision);

      if (!current.signal.aborted) {
        detail.value = { ...result, frames: mergeFrames(detail.value?.frames ?? [], result.frames, result.reset) };
      }
    } catch (error) {
      if (current.signal.aborted) {
        return;
      }

      loadError.value =
        getApiErrorStatus(error) === 404
          ? "This plan no longer exists. Plans are shared, so someone may have deleted it."
          : getFirstApiErrorMessage(error, "Unable to load this plan.");
    } finally {
      if (request === current) {
        isLoading.value = false;
      }
    }
  }

  function selectTime(timestamp: number) {
    const index = Math.round((timestamp - schedule.value[0]!) / (study.value!.stepSeconds * 1000));

    timeIndex.value = Math.min(Math.max(index, 0), schedule.value.length - 1);
  }

  function scrollBehavior(): ScrollBehavior {
    return matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
  }

  function showTimeOnMaps(timestamp: number) {
    selectTime(timestamp);
    panels.value?.scrollToMaps(scrollBehavior());
  }

  function showOnMoon() {
    const selection = selectedSite.value?.selection;
    const timestamp = schedule.value[timeIndex.value];

    emit("showOnMoon", {
      siteId: selection?.id ?? null,
      point: selection
        ? { location: { latitude: selection.latitude, longitude: selection.longitude }, radiusKm: (selection.radiusMeters ?? 0) / 1000 }
        : null,
      time: timestamp === undefined ? null : new Date(timestamp).toISOString(),
    });
  }

  async function remove() {
    const studyId = props.studyId;
    const signal = request.signal;
    const removed = await store.removeStudy(studyId);

    if (removed && props.studyId === studyId && !signal.aborted) {
      await router.push({ name: "home" });
    }
  }

  function exportCsv() {
    const csv = planResultsCsv(detail.value!.study, detail.value!.frames);
    const fileName =
      detail
        .value!.study.name.toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "") || `plan-${props.studyId}`;
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const link = document.createElement("a");

    link.href = url;
    link.download = `${fileName}-visibility.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  watch(
    () => props.studyId,
    () => {
      isLoading.value = true;
      detail.value = null;
      selectedId.value = null;
      timeIndex.value = 0;
      void load();
    },
    { immediate: true }
  );

  watch([() => summary.value?.resultRevision, () => detail.value?.study.resultRevision], () => {
    if (!detail.value || !summary.value || refreshTimer) {
      return;
    }
    if (summary.value.resultRevision === detail.value.study.resultRevision) {
      return;
    }

    refreshTimer = setTimeout(() => {
      refreshTimer = undefined;
      void load();
    }, REFRESH_DELAY_MS);
  });

  watch(
    () => schedule.value.length,
    (length) => {
      timeIndex.value = Math.min(timeIndex.value, Math.max(length - 1, 0));
    }
  );

  watch(
    () => summary.value?.name,
    (name) => {
      document.title = name ? `${name} - ${APPLICATION_TITLE}` : APPLICATION_TITLE;
    },
    { immediate: true }
  );

  onMounted(async () => {
    await nextTick();
    heading.value?.focus();
  });

  onUnmounted(() => {
    request.abort();
    clearTimeout(refreshTimer);
    document.title = APPLICATION_TITLE;
  });
</script>
