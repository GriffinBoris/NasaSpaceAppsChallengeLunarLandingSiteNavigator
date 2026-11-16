<template>
  <fieldset
    ref="fieldset"
    class="scroll-mt-16 space-y-3 rounded-md border border-line bg-surface p-3"
  >
    <legend class="sr-only">Your minimums</legend>
    <p
      class="text-sm font-medium text-body"
      aria-hidden="true"
    >
      Your minimums
    </p>
    <div class="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap sm:items-end sm:gap-x-4">
      <div class="min-w-0 space-y-1">
        <p class="text-xs text-secondary">{{ labels.sun }}</p>
        <AppSelect
          :model-value="criteria.minimumSunFraction"
          :label="`${labels.sun} minimum`"
          :options="FRACTION_OPTIONS"
          class="w-full sm:w-36"
          @update:model-value="update('minimumSunFraction', $event)"
        />
      </div>
      <div class="min-w-0 space-y-1">
        <p class="text-xs text-secondary">{{ labels.earth }}</p>
        <AppSelect
          :model-value="criteria.minimumEarthFraction"
          :label="`${labels.earth} minimum`"
          :options="FRACTION_OPTIONS"
          class="w-full sm:w-36"
          @update:model-value="update('minimumEarthFraction', $event)"
        />
      </div>
      <div
        v-if="isRegion"
        class="col-span-2 min-w-0 space-y-1 sm:col-span-1"
      >
        <p class="text-xs text-secondary">Area with both</p>
        <AppSelect
          :model-value="criteria.minimumJointShare"
          label="Area with both minimum"
          :options="JOINT_OPTIONS"
          class="w-full sm:w-36"
          @update:model-value="update('minimumJointShare', $event)"
        />
      </div>
      <div class="col-span-2 flex items-center sm:min-h-9">
        <AppSwitch
          :model-value="highlight && result.matchingMilliseconds > 0"
          :disabled="!result.matchingMilliseconds"
          :aria-describedby="result.matchingMilliseconds ? undefined : statusId"
          @update:model-value="highlight = $event"
          >Highlight on chart</AppSwitch
        >
      </div>
    </div>
    <div class="space-y-1">
      <p
        :id="statusId"
        class="text-sm"
        :class="result.matchingMilliseconds ? 'text-body' : 'text-secondary'"
        role="status"
      >
        {{ statusText }}
      </p>
      <details class="text-xs text-secondary">
        <summary class="rounded hover:text-body focus-visible:outline-2 focus-visible:outline-focus-ring">How hours are matched</summary>
        <div class="mt-2 space-y-2">
          <p>
            {{
              isRegion
                ? "Sun and Earth minimums use the area's averages. The shared area needs some Sun and an unobstructed Earth-center direction at the same samples, so it can change over time."
                : "The point must also have an unobstructed direction to Earth's center."
            }}
          </p>
          <p>The best window is the longest unbroken run of matching samples, with ties favoring shared coverage.</p>
          <p>
            {{ formatOptimalDuration(stepSeconds * 1000) }} per saved sample, capped at the plan end. Missing results break windows; conditions
            between samples are unknown.
          </p>
        </div>
      </details>
    </div>
  </fieldset>
</template>

<script setup lang="ts">
  import { computed, ref, useId } from "vue";
  import AppSelect from "@/components/ui/AppSelect.vue";
  import AppSwitch from "@/components/ui/AppSwitch.vue";
  import type { OptimalTimeCriteriaInterface, OptimalTimesInterface } from "@/types/terrain/OptimalTimesInterface";
  import type { VisibilityMetric } from "@/types/terrain/VisibilityInterface";
  import { formatOptimalDuration } from "../optimalTimes";

  const FRACTION_OPTIONS = [0.01, 0.1, 0.25, 0.5, 0.75, 0.95, 1].map((value) => ({ label: `${Math.round(value * 100)}%`, value }));
  const JOINT_OPTIONS = [{ label: "Any overlap", value: 0 }, ...FRACTION_OPTIONS];
  const MINIMUM_NAMES: Record<VisibilityMetric, string> = { sunlight: "Sun", earth: "Earth", joint: "area with both" };

  const criteria = defineModel<OptimalTimeCriteriaInterface>({ required: true });
  const highlight = defineModel<boolean>("highlight", { required: true });
  const props = defineProps<{ result: OptimalTimesInterface; radiusMeters: number | null; stepSeconds: number }>();
  const fieldset = ref<HTMLFieldSetElement>();
  const statusId = useId();
  const isRegion = computed(() => props.radiusMeters !== null);

  const labels = computed(() => (isRegion.value ? { sun: "Average Sun", earth: "Average Earth" } : { sun: "Visible Sun", earth: "Visible Earth" }));

  const areaName = computed(() => `The ${props.radiusMeters! / 1000} km-radius area's`);

  const statusText = computed(() => {
    const { matchingMilliseconds, calculatedMilliseconds, totalMilliseconds, peaks } = props.result;

    if (!calculatedMilliseconds) {
      return "No paired, verified Sun/Earth results yet.";
    }

    const isComplete = calculatedMilliseconds === totalMilliseconds;
    const checked = isComplete
      ? `${formatOptimalDuration(calculatedMilliseconds)} checked`
      : `${formatOptimalDuration(calculatedMilliseconds)} of ${formatOptimalDuration(totalMilliseconds)} checked`;

    if (matchingMilliseconds) {
      return `${formatOptimalDuration(matchingMilliseconds)} of ${formatOptimalDuration(calculatedMilliseconds)}${isComplete ? "" : " checked so far"} meet every minimum.`;
    }
    if (isRegion.value && peaks!.joint === 0) {
      return `Sun and Earth are never visible together here (${checked}).`;
    }

    const unreachable = [
      {
        label: isRegion.value ? `${areaName.value} average Sun` : "Sun",
        control: "Sun",
        peak: peaks!.sunlight,
        minimum: criteria.value.minimumSunFraction,
      },
      {
        label: isRegion.value ? `${areaName.value} average Earth view` : "Earth",
        control: "Earth",
        peak: peaks!.earth,
        minimum: criteria.value.minimumEarthFraction,
      },
      ...(isRegion.value ? [{ label: "The shared area", control: "area", peak: peaks!.joint, minimum: criteria.value.minimumJointShare }] : []),
    ].find((measure) => measure.peak < measure.minimum);

    return unreachable
      ? `${unreachable.label} never reaches ${Math.round(unreachable.minimum * 100)}% here (peak ${Math.floor(unreachable.peak * 1000 + 1e-9) / 10}%, ${checked}). Lower the ${unreachable.control} minimum to see other times.`
      : `No hour meets every minimum (${checked}).${mostBlockingHint.value}`;
  });

  const mostBlockingHint = computed(() => {
    const soleBlocks: Record<VisibilityMetric, number> = { sunlight: 0, earth: 0, joint: 0 };

    for (const missed of props.result.misses) {
      if (missed?.length === 1) {
        soleBlocks[missed[0]!]++;
      }
    }

    let metric: VisibilityMetric = "sunlight";
    let count = 0;

    for (const candidate of ["sunlight", "earth", "joint"] as const) {
      if (soleBlocks[candidate] > count) {
        metric = candidate;
        count = soleBlocks[candidate];
      }
    }

    return count ? ` Lowering the ${MINIMUM_NAMES[metric]} minimum would match the most hours.` : " Try lower minimums.";
  });

  function update(key: keyof OptimalTimeCriteriaInterface, value: number) {
    criteria.value = { ...criteria.value, [key]: value };
  }

  function focus(behavior: ScrollBehavior) {
    fieldset.value!.scrollIntoView({ behavior, block: "start" });
    fieldset.value!.querySelector<HTMLElement>("[role=combobox]")!.focus({ preventScroll: true });
  }

  defineExpose({ focus });
</script>
