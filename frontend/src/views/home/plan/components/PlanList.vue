<template>
  <LoadingSpinner
    v-if="!store.studies.length && store.isLoading"
    label="Loading plans…"
    class="flex px-2 py-2 text-sm text-secondary"
  />
  <p
    v-else-if="!store.studies.length"
    class="px-2 py-2 text-sm text-secondary"
  >
    No plans yet. Create one to see how sites fare over a range of dates.
  </p>
  <ul
    v-else
    class="space-y-0.5"
  >
    <li
      v-for="study in store.studies"
      :key="study.id"
      class="rounded-md pb-1 hover:bg-surface-muted"
    >
      <RouterLink
        :to="{ name: 'plan', params: { studyId: study.id } }"
        class="block w-full rounded-md px-2 pt-2 pb-1 text-left focus-visible:outline-2 focus-visible:outline-focus-ring"
        @click="emit('picked')"
      >
        <span class="block text-sm font-medium break-words text-body">{{ study.name }}</span>
        <span class="block text-xs text-secondary">{{ formatWindow(study.startTime, study.endTime) }}</span>
        <span
          v-if="statusText(study)"
          class="block text-xs"
          :class="study.status === 'failed' ? 'font-medium text-error' : 'text-secondary'"
          >{{ statusText(study) }}</span
        >
        <span
          v-if="study.status === 'running' && study.progress?.stage"
          class="block text-xs text-secondary"
          >{{ study.progress.stage }}</span
        >
        <span
          v-if="study.status === 'running' || study.status === 'stopping'"
          class="mt-1.5 block h-1 overflow-hidden rounded-full bg-line"
        >
          <span
            class="block h-full bg-accent"
            :style="{ width: `${study.progress?.percentage ?? 0}%` }"
          />
        </span>
      </RouterLink>

      <div class="flex flex-wrap items-center pl-0.5">
        <QuietButton
          :aria-label="`Edit ${study.name}`"
          :disabled="isPlanProcessing(study) || store.pendingStudyIds.has(study.id)"
          @click="emit('edit', study.id)"
          >Edit</QuietButton
        >
        <ConfirmButton
          quiet
          label="Delete"
          confirm-label="Delete"
          :aria-label="`Delete ${study.name} and its results`"
          :disabled="isPlanProcessing(study) || store.pendingStudyIds.has(study.id)"
          @confirm="store.removeStudy(study.id)"
        />
      </div>
    </li>
  </ul>
</template>

<script setup lang="ts">
  import LoadingSpinner from "@/components/ui/LoadingSpinner.vue";
  import { RouterLink } from "vue-router";
  import ConfirmButton from "@/components/ui/ConfirmButton.vue";
  import QuietButton from "@/components/ui/QuietButton.vue";
  import type { SunlightStudyInterface } from "@/types/terrain/SunlightStudyInterface";
  import { describePlanStatus, describeQueue, formatWindow, isPlanProcessing } from "@/views/home/plan/planTimeline";
  import { useSunlightStore } from "@/views/home/sunlightStore";

  const emit = defineEmits<{ picked: []; edit: [studyId: number] }>();
  const store = useSunlightStore();

  function statusText(study: SunlightStudyInterface) {
    const counts = `${study.completedFrames.toLocaleString("en-US")} of ${study.expectedFrames.toLocaleString("en-US")} results`;

    switch (study.status) {
      case "complete":
        return "";
      case "pending":
        return "Not calculated";
      case "queued":
        return describeQueue(study, store.studies);
      case "running":
        return `${describePlanStatus(study)}, ${counts}`;
      case "stopping":
        return "Stopping, keeping completed results";
      case "stopped":
        return `Stopped at ${counts}`;
      case "failed":
        return `Failed at ${counts}`;
    }
  }
</script>
