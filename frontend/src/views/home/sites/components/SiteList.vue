<template>
  <LoadingSpinner
    v-if="!store.selections.length && store.isLoading"
    label="Loading saved sites…"
    class="flex px-2 py-2 text-sm text-secondary"
  />
  <p
    v-else-if="!store.selections.length"
    class="px-2 py-2 text-sm text-secondary"
  >
    No sites yet. Add a featured landing site, or click the Moon and save the point.
  </p>
  <template v-else>
    <ul class="space-y-0.5">
      <li
        v-for="selection in store.selections"
        :key="selection.id"
        class="flex items-start rounded-md hover:bg-surface-muted"
        :class="store.focusedSelectionId === selection.id ? 'bg-surface-muted' : ''"
      >
        <button
          type="button"
          class="flex min-w-0 flex-1 items-start justify-between gap-3 rounded-md px-2 py-2 text-left focus-visible:outline-2 focus-visible:outline-focus-ring"
          :aria-current="store.focusedSelectionId === selection.id || undefined"
          @click="pick(selection.id)"
        >
          <span class="min-w-0">
            <span class="block text-sm break-words text-body">{{ selection.name }}</span>
            <span class="block font-mono text-xs text-secondary">{{ formatCoordinates(selection.latitude, selection.longitude) }}</span>
            <span
              v-if="selection.radiusMeters !== null"
              class="block text-xs text-secondary"
              >{{ formatRadius(selection.radiusMeters) }}</span
            >
          </span>
        </button>
        <div class="flex shrink-0 items-center py-1.5 pr-1">
          <ConfirmButton
            quiet
            label="Delete"
            confirm-label="Delete"
            :aria-label="`Delete ${selection.name}`"
            @confirm="store.removeSelection(selection.id)"
          />
        </div>
      </li>
    </ul>
  </template>
</template>

<script setup lang="ts">
  import LoadingSpinner from "@/components/ui/LoadingSpinner.vue";
  import ConfirmButton from "@/components/ui/ConfirmButton.vue";
  import { formatCoordinates, formatRadius } from "@/views/home/sites/coordinateFormat";
  import { useSunlightStore } from "@/views/home/sunlightStore";

  const emit = defineEmits<{ picked: [] }>();
  const store = useSunlightStore();

  function pick(selectionId: number) {
    store.focusSelection(selectionId);
    emit("picked");
  }
</script>
