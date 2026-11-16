<template>
  <FloatingPanel
    :title="selection.name"
    close-label="Close site"
    @close="store.focusSelection(null)"
  >
    <template #subtitle>
      <p class="font-mono text-xs text-secondary">{{ formatCoordinates(selection.latitude, selection.longitude) }}</p>
      <p class="text-xs text-secondary">{{ formatRadius(selection.radiusMeters) }}</p>
    </template>
    <form
      v-if="isRenaming"
      class="mt-3 flex gap-2 *:min-w-0"
      @submit.prevent="rename"
    >
      <AppTextInput
        v-model="editedName"
        required
        maxlength="120"
        ref="nameInput"
        :aria-label="`New name for ${selection.name}`"
        class="min-w-0 flex-1"
      />
      <AppButton button-type="submit">Save</AppButton>
      <AppButton @click="stopRenaming">Cancel</AppButton>
    </form>
    <template v-else>
      <VisibilityCheck
        class="mt-3"
        :location="selection"
        :radius-meters="selection.radiusMeters ?? 0"
        :dataset-id="datasetId"
        :timestamp="timestamp"
        @patch="(patch, sunlight) => emit('patch', patch, sunlight)"
      >
        <template #actions="{ hasResult }">
          <AppButton
            :tone="hasResult ? 'primary' : 'secondary'"
            @click="emit('plan', selection.id)"
            >Plan over time</AppButton
          >
          <AppButton
            v-if="!isConfirmingDelete"
            ref="renameButton"
            @click="startRename"
            >Rename</AppButton
          >
          <ConfirmButton
            v-model:confirming="isConfirmingDelete"
            label="Delete"
            confirm-label="Delete site"
            @confirm="store.removeSelection(selection.id)"
          />
        </template>
      </VisibilityCheck>
    </template>
  </FloatingPanel>
</template>

<script setup lang="ts">
  import AppTextInput from "@/components/ui/AppTextInput.vue";
  import { nextTick, ref, watch } from "vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import ConfirmButton from "@/components/ui/ConfirmButton.vue";
  import FloatingPanel from "@/components/ui/FloatingPanel.vue";
  import type { VisibilityPatchInterface } from "@/types/terrain/VisibilityInterface";
  import type { IlluminationPatchInterface } from "@/types/terrain/IlluminationPatchInterface";
  import type { SunlightSelectionInterface } from "@/types/terrain/SunlightSelectionInterface";
  import { formatCoordinates, formatRadius } from "@/views/home/sites/coordinateFormat";
  import { useSunlightStore } from "@/views/home/sunlightStore";
  import VisibilityCheck from "../../visibility/components/VisibilityCheck.vue";

  const props = defineProps<{ selection: SunlightSelectionInterface; datasetId: number | null; timestamp: string }>();
  const emit = defineEmits<{
    patch: [patch: VisibilityPatchInterface | null, sunlight: IlluminationPatchInterface | null];
    plan: [selectionId: number];
  }>();
  const store = useSunlightStore();
  const isRenaming = ref(false);
  const isConfirmingDelete = ref(false);
  const editedName = ref("");
  const nameInput = ref<{ focus: () => void; select: () => void }>();
  const renameButton = ref<{ $el: HTMLElement }>();

  async function startRename() {
    editedName.value = props.selection.name;
    isRenaming.value = true;

    await nextTick();
    nameInput.value?.select();
  }

  async function stopRenaming() {
    isRenaming.value = false;

    await nextTick();
    renameButton.value?.$el.focus();
  }

  async function rename() {
    if (await store.renameSelection(props.selection.id, editedName.value)) {
      await stopRenaming();
    }
  }

  watch(
    () => props.selection.id,
    () => {
      isRenaming.value = false;
      isConfirmingDelete.value = false;
    }
  );
</script>
