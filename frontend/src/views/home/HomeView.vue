<template>
  <Teleport
    defer
    to="#header-actions"
  >
    <template v-if="isOnMoon">
      <nav
        aria-label="Sites and plans"
        class="flex items-center gap-1"
      >
        <AppButton
          tone="ghost"
          :class="ICON_ON_PHONES"
          @click="isSitesOpen = true"
        >
          <MapPin aria-hidden="true" />
          <span class="max-sm:sr-only">Sites</span>
        </AppButton>
        <AppButton
          tone="ghost"
          :class="`${ICON_ON_PHONES} relative`"
          @click="isPlansOpen = true"
        >
          <CalendarRange aria-hidden="true" />
          <span class="max-sm:sr-only">Plans</span>

          <span
            v-if="planActivity"
            class="text-xs text-secondary tabular-nums max-sm:sr-only"
            :aria-label="planActivity.description"
            >{{ planActivity.badge }}</span
          >
          <span
            v-if="planActivity"
            class="absolute top-1.5 right-1.5 size-2 rounded-full bg-accent sm:hidden"
            aria-hidden="true"
          />
        </AppButton>
      </nav>
      <div class="flex min-w-0 flex-1 items-center justify-center gap-2">
        <TimeControl
          :time="viewerTime"
          :disabled="isApplyingTime || datasetId === null"
          :applying="isApplyingTime"
          @apply="applyViewerTime"
        />
      </div>
      <AppButton
        :class="`${ICON_ON_PHONES} sm:w-52 sm:justify-start sm:font-normal sm:text-secondary`"
        @click="isSearchOpen = true"
      >
        <Search aria-hidden="true" />
        <span class="max-sm:sr-only">Search the Moon</span>
      </AppButton>
      <AppButton
        tone="primary"
        :class="ICON_ON_PHONES"
        :disabled="datasetId === null"
        @click="openNewPlan(null)"
      >
        <Plus aria-hidden="true" />
        <span class="max-sm:sr-only">New plan</span>
      </AppButton>
    </template>
  </Teleport>
  <div class="relative min-h-[75dvh] flex-1 lg:min-h-0">
    <div
      class="absolute inset-0"
      :inert="!isOnMoon"
    >
      <h1 class="sr-only">Moon explorer</h1>
      <MoonViewer
        ref="viewer"
        v-model:location="location"
        v-model:radius-km="radiusKm"
        :has-selection="isPointOpen || store.focusedSelection !== null"
        :has-card="isPointOpen || store.focusedSelection !== null || isWelcomeOpen"
        :label-bounds="featureLabelBounds"
        class="absolute inset-0"
        @ready="datasetId = $event"
        @time="viewerTime = $event"
        @pick="openPoint"
        @feature="pickFeature"
        @help="isWelcomeOpen = true"
      />

      <div class="pointer-events-none absolute inset-3 flex flex-col items-end justify-between gap-3 max-sm:top-16 max-sm:justify-end">
        <div
          ref="selectionPanel"
          class="flex min-h-0 w-full flex-col gap-3 max-sm:max-h-[55%] sm:w-96"
        >
          <StoreErrorNotice class="pointer-events-auto" />
          <SiteCard
            v-if="store.focusedSelection"
            class="pointer-events-auto min-h-0 overflow-y-auto"
            :selection="store.focusedSelection"
            :dataset-id="datasetId"
            :timestamp="viewerTime"
            @patch="(patch, sunlight) => viewer?.showPatch(patch, sunlight)"
            @plan="openNewPlan([$event])"
          />
          <PointCard
            v-else-if="isPointOpen"
            v-model:radius-km="pointRadiusKm"
            class="pointer-events-auto min-h-0 overflow-y-auto"
            :location="location"
            :dataset-id="datasetId"
            :timestamp="viewerTime"
            :suggested-name="featureName"
            @close="isPointOpen = false"
            @patch="(patch, sunlight) => viewer?.showPatch(patch, sunlight)"
            @plan="openNewPlan([$event])"
          />
          <WelcomeCard
            v-else-if="isWelcomeOpen"
            class="pointer-events-auto min-h-0 overflow-y-auto"
            @dismiss="dismissWelcome"
            @search="isSearchOpen = true"
            @add-site="isAddSiteVisible = true"
          />
        </div>
      </div>
    </div>
    <RouterView v-slot="{ Component }">
      <div
        v-if="Component"
        class="absolute inset-0 z-30 overflow-y-auto bg-background"
      >
        <component
          :is="Component"
          @edit="openEditPlan"
          @show-on-moon="showOnMoon"
        />
      </div>
    </RouterView>
    <PlanNotices
      class="absolute left-1/2 z-40 w-[min(28rem,calc(100%-1.5rem))] -translate-x-1/2"
      :class="isOnMoon ? 'top-3' : 'bottom-3'"
    />
  </div>
  <AppDrawer
    v-model:visible="isSitesOpen"
    title="Saved sites"
  >
    <p class="px-2 pb-2 text-xs text-secondary">Sites are shared with everyone using this app. Anyone can rename or delete them.</p>
    <StoreErrorNotice class="px-2 pb-2" />
    <SiteList @picked="isSitesOpen = false" />
    <template #footer>
      <AppButton @click="isAddSiteVisible = true">Add site</AppButton>
    </template>
  </AppDrawer>
  <AppDrawer
    v-model:visible="isPlansOpen"
    title="Plans"
  >
    <p class="px-2 pb-2 text-xs text-secondary">Plans are shared with everyone using this app. Anyone can edit or delete them.</p>
    <StoreErrorNotice class="px-2 pb-2" />
    <PlanList
      @picked="isPlansOpen = false"
      @edit="openEditPlan"
    />
    <template #footer>
      <AppButton
        tone="primary"
        :disabled="datasetId === null"
        @click="openNewPlan(null)"
        >New plan</AppButton
      >
    </template>
  </AppDrawer>
  <AddSiteDialog
    v-model:visible="isAddSiteVisible"
    :location="location"
    :radius-km="radiusKm"
  />
  <FeatureSearchDialog
    v-model:visible="isSearchOpen"
    @pick="pickFeature"
  />
  <PlanDialog
    v-model:visible="isPlanDialogVisible"
    :dataset-id="datasetId"
    :viewer-time="viewerTime"
    :initial-selection-ids="planSelectionIds"
    :study="editingStudy"
    @add-site="isAddSiteVisible = true"
  />
</template>

<script setup lang="ts">
  import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
  import { RouterView, useRoute, useRouter } from "vue-router";
  import { CalendarRange, MapPin, Plus, Search } from "@lucide/vue";
  import { replaceRouteQuery } from "@/utils/routeQuery";
  import { moonViewQuery, parseMoonViewQuery, type MoonViewQueryInterface } from "@/views/home/moonViewQuery";
  import { usePolling } from "@/composables/usePolling";
  import AppButton from "@/components/ui/AppButton.vue";
  import AppDrawer from "@/components/ui/AppDrawer.vue";
  import type { SunlightStudyInterface } from "@/types/terrain/SunlightStudyInterface";
  import type { TerrainLocationInterface } from "@/types/terrain/TerrainLocationInterface";
  import type { LunarFeatureInterface } from "@/types/terrain/LunarFeatureInterface";
  import FeatureSearchDialog from "@/views/home/sites/components/FeatureSearchDialog.vue";
  import { useSunlightStore } from "@/views/home/sunlightStore";
  import { describePlanStatus } from "@/views/home/plan/planTimeline";
  import AddSiteDialog from "@/views/home/sites/components/AddSiteDialog.vue";
  import MoonViewer from "@/views/home/viewer/components/MoonViewer.vue";
  import PlanDialog from "@/views/home/plan/components/PlanDialog.vue";
  import PlanList from "@/views/home/plan/components/PlanList.vue";
  import PointCard from "@/views/home/sites/components/PointCard.vue";
  import SiteCard from "@/views/home/sites/components/SiteCard.vue";
  import SiteList from "@/views/home/sites/components/SiteList.vue";
  import TimeControl from "@/views/home/components/TimeControl.vue";
  import StoreErrorNotice from "@/views/home/components/StoreErrorNotice.vue";
  import PlanNotices from "@/views/home/plan/components/PlanNotices.vue";
  import WelcomeCard from "@/views/home/components/WelcomeCard.vue";

  const WELCOME_DISMISSED_KEY = "lunar-navigator.welcome-dismissed";

  const ICON_ON_PHONES = "max-sm:w-9 max-sm:px-0 max-sm:pointer-coarse:w-11";

  type Surface = "sites" | "plans" | "search" | "addSite" | "plan";
  const openSurface = ref<Surface | null>(null);

  function surfaceModel(surface: Surface) {
    return computed({
      get: () => openSurface.value === surface,
      set: (isOpen: boolean) => {
        if (isOpen) {
          openSurface.value = surface;
        } else if (openSurface.value === surface) {
          openSurface.value = null;
        }
      },
    });
  }

  const store = useSunlightStore();
  const route = useRoute();
  const router = useRouter();
  const isOnMoon = computed(() => route.name === "home");

  const planActivity = computed(() => {
    const running = store.studies.find((study) => study.status === "running");

    if (running) {
      return { badge: `${running.progress?.percentage ?? 0}%`, description: describePlanStatus(running) };
    }

    const queuedCount = store.studies.filter((study) => study.status === "queued").length;

    return queuedCount ? { badge: `${queuedCount} queued`, description: `${queuedCount} queued` } : null;
  });
  const viewer = ref<InstanceType<typeof MoonViewer>>();
  const selectionPanel = ref<HTMLDivElement>();
  const labelObstacles = new ResizeObserver(() => viewer.value?.refreshLabels());
  const location = ref<TerrainLocationInterface>({ latitude: -89.5, longitude: 0 });
  const pointRadiusKm = ref(5);
  const radiusKm = ref(pointRadiusKm.value);
  const datasetId = ref<number | null>(null);
  const viewerTime = ref("");
  const isApplyingTime = ref(false);
  const isPointOpen = ref(false);
  const isSitesOpen = surfaceModel("sites");
  const isPlansOpen = surfaceModel("plans");
  const isSearchOpen = surfaceModel("search");
  const isAddSiteVisible = surfaceModel("addSite");
  const isPlanDialogVisible = surfaceModel("plan");
  const isWelcomeOpen = ref(!readWelcomeDismissed());
  const featureName = ref("");

  const planSelectionIds = ref<number[] | null>(null);
  const editingStudy = ref<SunlightStudyInterface | null>(null);

  const { startPolling, stopPolling } = usePolling(store.refreshStudies, () => !store.hasProcessingStudies, 2000);

  watch(
    () => store.hasProcessingStudies,
    (isProcessing) => {
      if (isProcessing) {
        startPolling();
      } else {
        stopPolling();
      }
    },
    { immediate: true }
  );

  watch(openSurface, (surface) => {
    if (surface === "sites" || surface === "plans" || surface === "plan") {
      void store.loadLists();
    }
  });

  watch([isOnMoon, isPointOpen, () => store.focusedSelectionId, isWelcomeOpen], async () => {
    await nextTick();

    if (!isOnMoon.value || document.activeElement !== document.body) {
      return;
    }

    const card = selectionPanel.value?.querySelector<HTMLElement>("section");

    if (card) {
      card.focus();
    } else {
      viewer.value?.focus();
    }
  });

  watch(
    location,
    () => {
      featureName.value = "";
    },
    { flush: "sync" }
  );

  async function applyViewerTime(timestamp: string) {
    if (!viewer.value || isApplyingTime.value) {
      return;
    }

    hasChosenTime = true;
    isApplyingTime.value = true;

    try {
      await viewer.value.applyTime(timestamp);
    } finally {
      isApplyingTime.value = false;
    }
  }

  function readWelcomeDismissed() {
    try {
      return localStorage.getItem(WELCOME_DISMISSED_KEY) === "true";
    } catch (error) {
      console.warn("Unable to read the introduction preference.", error);
      return false;
    }
  }

  function dismissWelcome() {
    isWelcomeOpen.value = false;

    try {
      localStorage.setItem(WELCOME_DISMISSED_KEY, "true");
    } catch (error) {
      console.warn("Unable to save the introduction preference.", error);
    }
  }

  function featureLabelBounds(): DOMRect[] {
    return selectionPanel.value?.clientHeight ? [selectionPanel.value.getBoundingClientRect()] : [];
  }

  function openPoint() {
    featureName.value = "";
    radiusKm.value = pointRadiusKm.value;
    isPointOpen.value = true;
    store.focusSelection(null);
  }

  async function pickFeature(feature: LunarFeatureInterface) {
    store.focusSelection(null);

    location.value = { latitude: feature.latitude, longitude: feature.longitude };
    featureName.value = feature.name;
    pointRadiusKm.value = 0;
    radiusKm.value = 0;
    isPointOpen.value = true;

    await nextTick();
    viewer.value?.focusLocation(location.value, (feature.diameterKm ?? 0) * 500);
  }

  function openNewPlan(selectionIds: number[] | null) {
    planSelectionIds.value = selectionIds;
    editingStudy.value = null;
    isPlanDialogVisible.value = true;
  }

  function openEditPlan(studyId: number) {
    editingStudy.value = store.studies.find((study) => study.id === studyId)!;
    isPlanDialogVisible.value = true;
  }

  watch(
    () => store.focusedSelectionId,
    (selectionId) => {
      if (selectionId !== null) {
        isPointOpen.value = false;
      }
    }
  );

  watch(pointRadiusKm, (value) => {
    if (isPointOpen.value) {
      radiusKm.value = value;
    }
  });

  let hasChosenTime = false;
  let isViewRestored = false;
  let listsRequest = Promise.resolve();

  async function restoreView() {
    isViewRestored = false;
    await listsRequest;
    await showView(parseMoonViewQuery(route.query));

    isViewRestored = true;
    writeViewQuery();
  }

  async function showView(view: MoonViewQueryInterface) {
    if (view.time) {
      await applyViewerTime(view.time);
    }

    if (view.siteId !== null && store.selections.some((selection) => selection.id === view.siteId)) {
      store.focusSelection(view.siteId);
    } else if (view.point) {
      store.focusSelection(null);
      location.value = view.point.location;
      pointRadiusKm.value = view.point.radiusKm;
      radiusKm.value = view.point.radiusKm;
      isPointOpen.value = true;

      await nextTick();
      viewer.value?.focusLocation(view.point.location, view.point.radiusKm * 1000);
    }
  }

  async function showOnMoon(view: MoonViewQueryInterface) {
    await router.push({ name: "home" });
    await showView(view);
  }

  let writtenQuery = "";

  function writeViewQuery() {
    if (!isViewRestored || !isOnMoon.value) {
      return;
    }

    const query = moonViewQuery({
      siteId: store.focusedSelectionId,
      point: isPointOpen.value ? { location: location.value, radiusKm: radiusKm.value } : null,
      time: hasChosenTime ? viewerTime.value : null,
    });

    writtenQuery = JSON.stringify(query);
    replaceRouteQuery(router, route.query, query);
  }

  watch(
    () => route.query,
    (query) => {
      if (isViewRestored && isOnMoon.value && JSON.stringify(query) !== writtenQuery) {
        void restoreView();
      }
    }
  );

  watch(datasetId, (id, previousId) => {
    if (id !== null && previousId === null && !isViewRestored) {
      void restoreView();
    }
  });
  watch([isOnMoon, () => store.focusedSelectionId, isPointOpen, location, radiusKm, viewerTime], writeViewQuery);

  onMounted(() => {
    labelObstacles.observe(selectionPanel.value!);
    listsRequest = store.loadLists();
  });
  onUnmounted(() => {
    labelObstacles.disconnect();
    store.dispose();
  });
</script>
