<template>
  <FloatingPanel
    :title="suggestedName || 'Selected point'"
    close-label="Close selected point"
    @close="emit('close')"
  >
    <template #subtitle>
      <p class="font-mono text-xs text-secondary">{{ formatCoordinates(location.latitude, location.longitude) }}</p>
    </template>
    <div class="mt-3 flex items-center justify-between gap-3 text-xs text-secondary">
      <span
        class="font-medium"
        aria-hidden="true"
        >Area</span
      >
      <AppSelect
        v-model="radiusKm"
        label="Area"
        :options="AREA_OPTIONS"
      />
    </div>
    <form
      v-if="intent"
      class="mt-3 space-y-2"
      @submit.prevent="save"
    >
      <label class="block space-y-1 text-xs font-medium text-secondary"
        >{{ intent === "plan" ? "Name this site to plan it" : "Site name" }}
        <AppTextInput
          v-model="name"
          required
          maxlength="120"
          ref="nameInput"
        />
      </label>
      <p class="text-sm text-secondary">Saved sites are visible to everyone using this app.</p>
      <div class="flex gap-2 *:whitespace-nowrap">
        <AppButton
          class="flex-1"
          button-type="submit"
          tone="primary"
          :loading="isSaving"
          >{{ intent === "plan" ? "Save and plan" : "Save site" }}</AppButton
        >
        <AppButton @click="cancel">Cancel</AppButton>
      </div>
    </form>
    <template v-else>
      <VisibilityCheck
        class="mt-3"
        :location="location"
        :radius-meters="radiusKm * 1000"
        :dataset-id="datasetId"
        :timestamp="timestamp"
        @patch="(patch, sunlight) => emit('patch', patch, sunlight)"
      >
        <template #actions="{ hasResult }">
          <AppButton
            ref="planButton"
            :tone="hasResult ? 'primary' : 'secondary'"
            @click="start('plan')"
            >Plan over time</AppButton
          >
          <AppButton
            ref="saveButton"
            @click="start('save')"
            >Save as site</AppButton
          >
        </template>
      </VisibilityCheck>
    </template>
  </FloatingPanel>
</template>

<script setup lang="ts">
  import AppTextInput from "@/components/ui/AppTextInput.vue";
  import { nextTick, ref, watch } from "vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import AppSelect from "@/components/ui/AppSelect.vue";
  import FloatingPanel from "@/components/ui/FloatingPanel.vue";
  import type { VisibilityPatchInterface } from "@/types/terrain/VisibilityInterface";
  import type { IlluminationPatchInterface } from "@/types/terrain/IlluminationPatchInterface";
  import type { TerrainLocationInterface } from "@/types/terrain/TerrainLocationInterface";
  import { formatCoordinates } from "@/views/home/sites/coordinateFormat";
  import { useSunlightStore } from "@/views/home/sunlightStore";
  import VisibilityCheck from "../../visibility/components/VisibilityCheck.vue";

  const AREA_OPTIONS = [
    { label: "Point", value: 0 },
    { label: "0.5 km radius", value: 0.5 },
    { label: "1 km radius", value: 1 },
    { label: "2.5 km radius", value: 2.5 },
    { label: "5 km radius", value: 5 },
    { label: "10 km radius", value: 10 },
    { label: "25 km radius", value: 25 },
    { label: "50 km radius", value: 50 },
  ];

  const radiusKm = defineModel<number>("radiusKm", { required: true });
  const props = defineProps<{ location: TerrainLocationInterface; datasetId: number | null; timestamp: string; suggestedName?: string }>();
  const emit = defineEmits<{
    close: [];
    patch: [patch: VisibilityPatchInterface | null, sunlight: IlluminationPatchInterface | null];
    plan: [selectionId: number];
  }>();
  const store = useSunlightStore();
  const intent = ref<"save" | "plan" | null>(null);
  const isSaving = ref(false);
  const name = ref(props.suggestedName ?? "");
  const nameInput = ref<{ focus: () => void; select: () => void }>();
  const planButton = ref<{ $el: HTMLElement }>();
  const saveButton = ref<{ $el: HTMLElement }>();

  async function start(nextIntent: "save" | "plan") {
    intent.value = nextIntent;

    await nextTick();
    nameInput.value?.focus();
  }

  async function cancel() {
    const previousIntent = intent.value;

    intent.value = null;

    await nextTick();
    (previousIntent === "plan" ? planButton : saveButton).value?.$el.focus();
  }

  async function save() {
    isSaving.value = true;

    const selection = await store.saveSelection({
      name: name.value,
      latitude: props.location.latitude,
      longitude: props.location.longitude,
      radiusMeters: radiusKm.value ? radiusKm.value * 1000 : null,
    });

    isSaving.value = false;

    if (!selection) {
      return;
    }

    if (intent.value === "plan") {
      emit("plan", selection.id);
    }

    void store.focusSelection(selection.id);
  }

  watch(
    () => [props.location.latitude, props.location.longitude, props.suggestedName],
    () => {
      intent.value = null;
      name.value = props.suggestedName ?? "";
    }
  );
</script>
