<template>
  <AppDialog
    v-model:visible="visible"
    title="Add site"
  >
    <div class="space-y-5">
      <p class="text-sm text-secondary">Saved sites are shared; anyone can rename or delete them.</p>
      <StoreErrorNotice />
      <AppTabs :tabs="SITE_TABS">
        <template #featured>
          <div class="space-y-3">
            <div
              v-for="group in FEATURED_SITE_GROUPS"
              :key="group.name"
              class="space-y-1"
            >
              <h3 class="text-xs text-secondary">{{ group.name }}</h3>
              <ul class="divide-y divide-line">
                <li
                  v-for="site in group.sites"
                  :key="site.name"
                  class="flex items-center justify-between gap-3 py-1.5"
                >
                  <div class="min-w-0">
                    <p class="truncate text-sm text-body">{{ site.name }}</p>
                    <p class="truncate text-xs text-secondary">{{ site.description }}</p>
                  </div>
                  <span
                    v-if="isSaved(site)"
                    class="rounded text-xs text-secondary outline-none focus-visible:outline-2 focus-visible:outline-focus-ring"
                    tabindex="-1"
                    :data-added="site.name"
                    >Added</span
                  >
                  <AppButton
                    v-else
                    :aria-label="`Add ${site.name}`"
                    @click="addFeaturedSite(site)"
                    >Add</AppButton
                  >
                </li>
              </ul>
            </div>
          </div>
        </template>
        <template #coordinates>
          <form
            class="space-y-3"
            aria-label="Coordinates"
            @submit.prevent="saveCustomSite"
          >
            <label class="block space-y-1 text-xs font-medium text-secondary"
              >Name
              <AppTextInput
                v-model="name"
                required
                maxlength="120"
                placeholder="Shackleton rim"
              />
            </label>
            <div class="grid grid-cols-2 gap-3">
              <label class="block space-y-1 text-xs font-medium text-secondary"
                >Latitude (°N)
                <AppTextInput
                  v-model.number="draft.latitude"
                  type="number"
                  min="-90"
                  max="90"
                  step="any"
                  required
                />
              </label>
              <label class="block space-y-1 text-xs font-medium text-secondary"
                >Longitude (°E)
                <AppTextInput
                  v-model.number="draft.longitude"
                  type="number"
                  min="-180"
                  max="180"
                  step="any"
                  required
                />
              </label>
              <div class="space-y-1 text-xs text-secondary">
                <span
                  class="font-medium"
                  aria-hidden="true"
                  >Type</span
                >
                <AppSelect
                  v-model="draft.siteType"
                  label="Type"
                  :options="SITE_TYPE_OPTIONS"
                  class="w-full"
                />
              </div>
              <label
                v-if="draft.siteType === 'region'"
                class="block space-y-1 text-xs text-secondary"
                >Radius (km)
                <AppTextInput
                  v-model.number="draft.radiusKm"
                  type="number"
                  min="0.25"
                  max="50"
                  step="any"
                  required
                />
              </label>
            </div>
            <div class="flex justify-end">
              <AppButton
                button-type="submit"
                :loading="isSaving"
                >Save site</AppButton
              >
            </div>
          </form>
        </template>
      </AppTabs>
    </div>
  </AppDialog>
</template>

<script setup lang="ts">
  import AppTextInput from "@/components/ui/AppTextInput.vue";
  import { nextTick, ref, watch } from "vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import AppDialog from "@/components/ui/AppDialog.vue";
  import AppSelect from "@/components/ui/AppSelect.vue";
  import type { TerrainLocationInterface } from "@/types/terrain/TerrainLocationInterface";
  import { FEATURED_SITE_GROUPS, type FeaturedSiteInterface } from "@/views/home/sites/featuredSites";
  import { useSunlightStore } from "@/views/home/sunlightStore";
  import AppTabs from "@/components/ui/AppTabs.vue";
  import StoreErrorNotice from "../../components/StoreErrorNotice.vue";

  const SITE_TABS = [
    { value: "featured", label: "Featured sites" },
    { value: "coordinates", label: "Coordinates" },
  ];

  const SITE_TYPE_OPTIONS = [
    { label: "Point", value: "point" },
    { label: "Region", value: "region" },
  ];

  const visible = defineModel<boolean>("visible", { required: true });

  const props = defineProps<{ location: TerrainLocationInterface; radiusKm: number }>();
  const store = useSunlightStore();
  const name = ref("");
  const isSaving = ref(false);
  const draft = ref({ latitude: 0, longitude: 0, radiusKm: 5, siteType: "point" });

  function isSaved(site: FeaturedSiteInterface) {
    return store.selections.some(
      (selection) => selection.latitude === site.latitude && selection.longitude === site.longitude && selection.radiusMeters === null
    );
  }

  async function addFeaturedSite(site: FeaturedSiteInterface) {
    const selection = await store.saveSelection({ name: site.name, latitude: site.latitude, longitude: site.longitude, radiusMeters: null });

    if (!selection) {
      return;
    }

    void store.focusSelection(selection.id);
    await nextTick();
    document.querySelector<HTMLElement>(`[data-added="${CSS.escape(site.name)}"]`)?.focus();
  }

  async function saveCustomSite() {
    isSaving.value = true;

    const selection = await store.saveSelection({
      name: name.value,
      latitude: draft.value.latitude,
      longitude: draft.value.longitude,
      radiusMeters: draft.value.siteType === "point" ? null : draft.value.radiusKm * 1000,
    });

    isSaving.value = false;

    if (!selection) {
      return;
    }

    name.value = "";
    visible.value = false;
    void store.focusSelection(selection.id);
  }

  watch(visible, (isVisible) => {
    if (!isVisible) {
      return;
    }

    draft.value = {
      latitude: props.location.latitude,
      longitude: props.location.longitude,
      radiusKm: props.radiusKm || 5,
      siteType: props.radiusKm ? "region" : "point",
    };
  });
</script>
