<template>
  <AppDialog
    v-model:visible="visible"
    title="Search the Moon"
  >
    <form
      class="flex"
      @submit.prevent="search"
    >
      <AppTextInput
        v-model="query"
        aria-label="Feature name"
        placeholder="Feature name (2+ characters)"
        autofocus
        minlength="2"
        maxlength="120"
        required
        class="min-w-0 flex-1"
      />
    </form>
    <div
      v-if="errorMessage"
      class="mt-3 space-y-2"
    >
      <AlertBanner :message="errorMessage" />
      <AppButton @click="search">Try again</AppButton>
    </div>
    <LoadingSpinner
      v-if="isLoading"
      label="Searching…"
      class="mt-3 flex text-sm text-secondary"
    />
    <p
      v-else-if="catalogLoaded === false"
      class="mt-3 text-sm text-secondary"
      role="status"
    >
      Feature names are not available on this server yet. You can still click the Moon or add a site by coordinates.
    </p>
    <p
      v-else-if="query.trim().length === 1"
      class="mt-3 text-sm text-secondary"
      role="status"
    >
      Type at least two characters.
    </p>
    <p
      v-else-if="hasSearched && !features.length"
      class="mt-3 text-sm text-secondary"
      role="status"
    >
      No matching features.
    </p>
    <ul
      v-if="features.length"
      class="mt-3 max-h-80 space-y-1 overflow-y-auto"
      aria-label="Lunar features"
    >
      <li
        v-for="feature in features"
        :key="feature.id"
        class="flex items-center rounded-md hover:bg-surface-muted"
      >
        <button
          type="button"
          class="min-w-0 flex-1 rounded-md px-2 py-2 text-left focus-visible:outline-2 focus-visible:outline-focus-ring"
          @click="pick(feature)"
        >
          <span class="block text-sm text-body">{{ feature.name }}</span>
          <span
            v-if="feature.englishName"
            class="block text-sm text-secondary"
            >{{ feature.englishName }}</span
          >
          <span class="flex flex-wrap gap-x-3 text-xs text-secondary">
            <span>{{ featureTypeLabel(feature.featureType) }}</span>
            <span v-if="feature.diameterKm !== null">{{ feature.diameterKm.toLocaleString("en-US", { maximumFractionDigits: 1 }) }} km across</span>
          </span>
        </button>
        <a
          :href="feature.sourceUrl"
          target="_blank"
          rel="noopener noreferrer"
          :class="QUIET_BUTTON_CLASS"
          :aria-label="`USGS details for ${feature.name}, opens in a new tab`"
          >USGS</a
        >
      </li>
    </ul>
  </AppDialog>
</template>

<script setup lang="ts">
  import LoadingSpinner from "@/components/ui/LoadingSpinner.vue";
  import { QUIET_BUTTON_CLASS } from "@/components/ui/quietButtonClass";
  import AppTextInput from "@/components/ui/AppTextInput.vue";
  import { watch } from "vue";
  import AlertBanner from "@/components/ui/AlertBanner.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import AppDialog from "@/components/ui/AppDialog.vue";
  import type { LunarFeatureInterface } from "@/types/terrain/LunarFeatureInterface";
  import { useFeatureSearch } from "@/views/home/sites/useFeatureSearch";

  const visible = defineModel<boolean>("visible", { required: true });
  const emit = defineEmits<{ pick: [feature: LunarFeatureInterface] }>();
  const { query, features, catalogLoaded, isLoading, hasSearched, errorMessage, search, clear } = useFeatureSearch();

  function featureTypeLabel(featureType: string) {
    return featureType.split(",")[0]!;
  }

  function pick(feature: LunarFeatureInterface) {
    emit("pick", feature);
    visible.value = false;
  }

  watch(visible, (isVisible) => {
    if (isVisible) {
      query.value = "";
      void search();
    } else {
      clear();
    }
  });
</script>
