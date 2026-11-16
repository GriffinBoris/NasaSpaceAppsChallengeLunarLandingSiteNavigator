<template>
  <div
    class="pointer-events-none flex flex-col gap-2"
    aria-live="polite"
  >
    <div
      v-for="notice in store.notices"
      :key="notice.id"
      class="pointer-events-auto flex items-start gap-3 rounded-lg border bg-surface/95 px-3 py-2 shadow-xl"
      :class="notice.tone === 'error' ? 'border-error/40' : 'border-line'"
      :role="notice.tone === 'error' ? 'alert' : 'status'"
    >
      <p
        class="min-w-0 flex-1 py-1 text-sm"
        :class="notice.tone === 'error' ? 'text-error' : 'text-body'"
      >
        {{ notice.message }}
      </p>
      <RouterLink
        v-if="notice.studyId !== null"
        :to="{ name: 'plan', params: { studyId: notice.studyId } }"
        class="shrink-0"
        :class="QUIET_BUTTON_CLASS"
        @click="store.dismissNotice(notice.id)"
        >Details</RouterLink
      >
      <button
        type="button"
        :class="CLOSE_BUTTON_CLASS"
        aria-label="Dismiss"
        @click="store.dismissNotice(notice.id)"
      >
        ×
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { QUIET_BUTTON_CLASS } from "@/components/ui/quietButtonClass";
  import { onUnmounted, watch } from "vue";
  import { RouterLink } from "vue-router";
  import { CLOSE_BUTTON_CLASS } from "@/components/ui/closeButtonClass";
  import type { SunlightStudyInterface } from "@/types/terrain/SunlightStudyInterface";
  import { isPlanProcessing } from "@/views/home/plan/planTimeline";
  import { useSunlightStore } from "@/views/home/sunlightStore";

  const SUCCESS_NOTICE_MS = 10000;

  const store = useSunlightStore();
  const timers = new Map<number, ReturnType<typeof setTimeout>>();
  let previousStudies = new Map<number, SunlightStudyInterface>();

  watch(
    () => store.studies,
    (studies) => {
      for (const study of studies) {
        const previous = previousStudies.get(study.id);

        if (!previous || !isPlanProcessing(previous) || isPlanProcessing(study)) {
          continue;
        }

        if (study.status === "complete") {
          store.addNotice({ studyId: study.id, tone: "success", message: `${study.name} finished calculating.` });
        } else if (study.status === "failed") {
          store.addNotice({ studyId: study.id, tone: "error", message: `${study.name} failed. ${study.errorMessage}`.trim() });
        }
      }

      previousStudies = new Map(studies.map((study) => [study.id, study]));
    },
    { immediate: true }
  );

  watch(
    () => store.notices,
    (notices) => {
      for (const notice of notices) {
        if (notice.tone !== "success" || timers.has(notice.id)) {
          continue;
        }

        timers.set(
          notice.id,
          setTimeout(() => {
            timers.delete(notice.id);
            store.dismissNotice(notice.id);
          }, SUCCESS_NOTICE_MS)
        );
      }
    }
  );

  onUnmounted(() => {
    for (const timer of timers.values()) {
      clearTimeout(timer);
    }
  });
</script>
