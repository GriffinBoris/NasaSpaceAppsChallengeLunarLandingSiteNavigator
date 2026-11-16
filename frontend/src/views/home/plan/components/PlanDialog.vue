<template>
  <AppDialog
    v-model:visible="visible"
    :title="study ? 'Edit plan' : 'New plan'"
  >
    <form
      class="space-y-4"
      novalidate
      @submit.prevent="submit"
    >
      <label class="block space-y-1 text-xs font-medium text-secondary"
        >Name
        <AppTextInput
          v-model="name"
          autofocus
          maxlength="120"
          @focus="selectSuggestedName"
        />
      </label>
      <div class="space-y-1 text-xs text-secondary">
        <span
          class="font-medium"
          aria-hidden="true"
          >Sites</span
        >
        <div
          v-if="!siteOptions.length"
          class="flex flex-wrap items-center gap-3 text-sm"
        >
          <span>Plans need at least one saved site.</span>
          <AppButton @click="emit('addSite')">Add site</AppButton>
        </div>
        <AppMultiSelect
          v-else
          v-model="selectionIds"
          label="Sites"
          placeholder="Choose sites"
          selected-items-label="{0} sites"
          :options="siteOptions"
          class="w-full"
        />
        <p v-if="!study && !initialSelectionIds && siteOptions.length > 1">Every saved site starts selected. Remove any you don't need.</p>
      </div>
      <fieldset class="min-w-0 space-y-2">
        <legend class="text-sm font-medium text-body">Date range (UTC)</legend>
        <div class="grid gap-3 sm:grid-cols-2">
          <div
            v-for="field in timeFields"
            :key="field.label"
            role="group"
            :aria-label="`${field.label}, UTC`"
            class="space-y-1"
          >
            <p
              class="text-xs text-secondary"
              aria-hidden="true"
            >
              {{ field.label }}
            </p>
            <div class="flex gap-2">
              <AppTextInput
                v-model="field.input.date"
                type="date"
                :aria-label="`${field.label} date`"
                class="min-w-0 flex-1"
              />
              <AppTextInput
                v-model="field.input.clock"
                inputmode="numeric"
                maxlength="5"
                placeholder="HH:MM"
                :aria-label="`${field.label} time, 24-hour`"
                class="w-[4.5rem]"
              />
            </div>
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-x-3 gap-y-2 pt-2">
          <div
            class="grid w-full grid-cols-3 rounded-md border border-control-border p-0.5"
            role="group"
            aria-label="Quick date ranges"
          >
            <button
              v-for="length in PLAN_LENGTHS"
              :key="length.label"
              type="button"
              :aria-pressed="length === activeLength"
              :disabled="startTimestamp === null"
              class="rounded px-2.5 py-1 text-sm pointer-coarse:min-h-11 focus-visible:outline-2 focus-visible:outline-focus-ring disabled:cursor-not-allowed disabled:opacity-50"
              :class="
                length === activeLength ? 'bg-surface-muted font-medium text-body active:bg-line' : 'text-secondary hover:text-body active:bg-line'
              "
              @click="applyLength(length.hours)"
            >
              {{ length.label }}
            </button>
          </div>
          <span
            v-if="customLength"
            class="text-xs text-secondary"
            >{{ customLength }}</span
          >
        </div>
      </fieldset>
      <div class="space-y-1 text-xs text-secondary sm:w-1/2">
        <span
          class="font-medium"
          aria-hidden="true"
          >Check every</span
        >
        <AppSelect
          v-model="stepSeconds"
          label="Check every"
          :options="stepOptions"
          class="w-full"
        />
      </div>
      <details
        v-if="workerCount !== null"
        class="text-xs text-secondary"
      >
        <summary class="cursor-pointer rounded hover:text-body focus-visible:outline-2 focus-visible:outline-focus-ring">Advanced</summary>
        <div class="mt-2 space-y-1 sm:w-1/2">
          <span
            class="font-medium"
            aria-hidden="true"
            >Calculation workers</span
          >
          <AppSelect
            v-model="workerCount"
            label="Calculation workers"
            :options="store.workerOptions"
            class="w-full"
          />
          <p>More workers finish area sites sooner but use more server memory. Point sites always use one.</p>
        </div>
      </details>
      <div class="space-y-1 text-sm">
        <p
          :class="problem && hasSubmitted ? 'text-error' : problem ? 'text-secondary' : 'text-body'"
          :role="problem && hasSubmitted ? 'alert' : undefined"
        >
          {{ problem || resultSummary }}
        </p>
        <p class="text-xs text-secondary">
          {{ study ? "Keeps matching results and calculates the rest in the background." : "Calculates in the background." }}
          Plans are shared; anyone can edit or delete them.
        </p>
      </div>
      <p
        v-if="formError"
        class="text-sm text-error"
        role="alert"
      >
        {{ formError }}
      </p>
      <div class="flex justify-end gap-2">
        <AppButton @click="visible = false">Cancel</AppButton>
        <AppButton
          button-type="submit"
          tone="primary"
          :loading="isSubmitting"
          >{{ study ? "Save changes" : "Create plan" }}</AppButton
        >
      </div>
    </form>
  </AppDialog>
</template>

<script setup lang="ts">
  import AppTextInput from "@/components/ui/AppTextInput.vue";
  import { computed, ref, watch } from "vue";
  import { useRouter } from "vue-router";
  import AppButton from "@/components/ui/AppButton.vue";
  import AppDialog from "@/components/ui/AppDialog.vue";
  import AppMultiSelect from "@/components/ui/AppMultiSelect.vue";
  import AppSelect from "@/components/ui/AppSelect.vue";
  import type { UtcInputInterface } from "@/types/terrain/NewPlanFormInterface";
  import type { SunlightStudyInterface } from "@/types/terrain/SunlightStudyInterface";
  import { getFirstApiErrorCode, getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { matchingLength, parseUtcInput, PLAN_LENGTHS, suggestPlanName, timesPerSite, toUtcInput } from "@/views/home/plan/newPlanForm";
  import { formatDuration } from "@/views/home/plan/planTimeline";
  import { useSunlightStore } from "@/views/home/sunlightStore";

  const HOUR = 3600000;
  const DEFAULT_LENGTH_HOURS = 14 * 24;
  const LARGE_PLAN_RESULTS = 2000;

  const visible = defineModel<boolean>("visible", { required: true });
  const emit = defineEmits<{ addSite: [] }>();
  const router = useRouter();

  const props = defineProps<{
    datasetId: number | null;
    viewerTime: string;
    initialSelectionIds: number[] | null;
    study: SunlightStudyInterface | null;
  }>();
  const store = useSunlightStore();
  const customName = ref<string | null>(null);
  const selectionIds = ref<number[]>([]);
  const start = ref<UtcInputInterface>({ date: "", clock: "" });
  const end = ref<UtcInputInterface>({ date: "", clock: "" });
  const stepSeconds = ref(3600);
  const workerCount = ref<number | null>(null);
  const hasSubmitted = ref(false);
  const formError = ref("");
  const isSubmitting = ref(false);

  const timeFields = computed(() => [
    { label: "Start", input: start.value },
    { label: "End", input: end.value },
  ]);
  const startTimestamp = computed(() => parseUtcInput(start.value));
  const endTimestamp = computed(() => parseUtcInput(end.value));
  const durationMs = computed(() => (startTimestamp.value === null || endTimestamp.value === null ? 0 : endTimestamp.value - startTimestamp.value));
  const activeLength = computed(() => matchingLength(durationMs.value));
  const customLength = computed(() =>
    durationMs.value > 0 && !activeLength.value ? `Custom range, ${formatDuration(durationMs.value / 1000)}` : ""
  );

  const siteOptions = computed(() => {
    const saved = store.selections.map((selection) => ({ label: selection.name, value: selection.id }));

    const deleted = (props.study?.selections ?? [])
      .filter((pinned) => !store.selections.some((selection) => selection.id === pinned.id))
      .map((pinned) => ({ label: `${pinned.name} (deleted site)`, value: pinned.id }));

    return [...saved, ...deleted];
  });
  const chosenSelections = computed(() => store.selections.filter((selection) => selectionIds.value.includes(selection.id)));
  const suggestedName = computed(() => {
    if (startTimestamp.value === null || endTimestamp.value === null) {
      return "";
    }

    return suggestPlanName(
      chosenSelections.value.map((selection) => selection.name),
      startTimestamp.value,
      endTimestamp.value
    );
  });

  const name = computed({
    get: () => customName.value ?? suggestedName.value,
    set: (value: string) => {
      customName.value = value;
    },
  });

  const checksPerSite = computed(() => timesPerSite(durationMs.value, stepSeconds.value));
  const resultCount = computed(() => checksPerSite.value * selectionIds.value.length);
  const stepOptions = computed(() =>
    store.stepOptions.map((option) => {
      const count = timesPerSite(durationMs.value, option.seconds) * selectionIds.value.length;

      return {
        label: option.label,
        value: option.seconds,
        description: count ? countLabel(count, "result") : undefined,
      };
    })
  );
  const resultSummary = computed(() => {
    const siteCount = selectionIds.value.length;
    const checks = `checked ${countLabel(checksPerSite.value, "time")}${siteCount === 1 ? "" : " each"}`;

    const summary = `${countLabel(resultCount.value, "result")}: ${countLabel(siteCount, "site")}, ${checks}.`;

    return resultCount.value > LARGE_PLAN_RESULTS
      ? `${summary} Large plans can take a long time, and other plans wait until this one finishes.`
      : summary;
  });
  const problem = computed(() => {
    if (!selectionIds.value.length) {
      return "Choose at least one site.";
    }
    if (startTimestamp.value === null || endTimestamp.value === null) {
      return "Enter a date and a 24-hour time such as 17:00 for the start and end.";
    }
    if (durationMs.value <= 0) {
      return "End must be after start.";
    }

    if (!name.value.trim()) {
      return "Name the plan.";
    }

    return "";
  });

  function countLabel(count: number, noun: string) {
    return `${count.toLocaleString("en-US")} ${count === 1 ? noun : `${noun}s`}`;
  }

  function selectSuggestedName(event: FocusEvent) {
    if (customName.value === null) {
      (event.target as HTMLInputElement).select();
    }
  }

  function applyLength(hours: number) {
    end.value = toUtcInput(startTimestamp.value! + hours * HOUR);
  }

  function reset() {
    hasSubmitted.value = false;
    formError.value = "";

    if (props.study) {
      customName.value = props.study.name;
      selectionIds.value = props.study.selections.map((selection) => selection.id);
      start.value = toUtcInput(Date.parse(props.study.startTime));
      end.value = toUtcInput(Date.parse(props.study.endTime));
      stepSeconds.value = props.study.stepSeconds;
      workerCount.value = props.study.workerCount;
      return;
    }

    const viewerHour = Math.floor(Date.parse(props.viewerTime) / HOUR) * HOUR;

    customName.value = null;
    selectionIds.value = props.initialSelectionIds ?? store.selections.map((selection) => selection.id);
    start.value = toUtcInput(viewerHour);
    end.value = toUtcInput(viewerHour + DEFAULT_LENGTH_HOURS * HOUR);
    stepSeconds.value = 3600;
    workerCount.value = store.defaultWorkerCount;
  }

  async function submit() {
    hasSubmitted.value = true;

    if (problem.value || workerCount.value === null || (!props.study && props.datasetId === null)) {
      return;
    }

    const planName = name.value.trim();
    const plan = {
      name: planName,
      selectionIds: [...selectionIds.value],
      startTime: new Date(startTimestamp.value!).toISOString(),
      endTime: new Date(endTimestamp.value!).toISOString(),
      stepSeconds: stepSeconds.value,
      workerCount: workerCount.value,
    };

    isSubmitting.value = true;

    try {
      if (props.study) {
        await store.updateStudy(props.study.id, plan);
        visible.value = false;
        return;
      }

      const created = await store.createStudy({ ...plan, datasetId: props.datasetId! });

      visible.value = false;

      if (created) {
        await router.push({ name: "plan", params: { studyId: created.id } });
      }
    } catch (error) {
      const message = getFirstApiErrorMessage(error, props.study ? "Unable to save this plan." : "Unable to create this plan.");

      if (getFirstApiErrorCode(error) === "study_queue_unavailable") {
        const saved = props.study ? `Changes to ${planName} were saved` : `${planName} was saved`;

        store.addNotice({ studyId: null, tone: "error", message: `${saved} but could not start. ${message} Retry it from Plans.` });
        visible.value = false;
        return;
      }

      formError.value = message;
    } finally {
      isSubmitting.value = false;
    }
  }

  watch(visible, (isVisible) => {
    if (isVisible) {
      reset();
    }
  });
  watch(
    () => store.defaultWorkerCount,
    (defaultWorkerCount) => {
      if (workerCount.value === null) {
        workerCount.value = defaultWorkerCount;
      }
    }
  );
  watch([name, selectionIds, start, end, stepSeconds, workerCount], () => (formError.value = ""), { deep: true });
</script>
