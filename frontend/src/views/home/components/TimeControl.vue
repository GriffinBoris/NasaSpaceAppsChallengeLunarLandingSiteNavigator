<template>
  <div
    class="flex min-w-0 items-center rounded-md border border-line bg-surface"
    role="group"
    aria-label="Viewer time"
  >
    <AppButton
      tone="ghost"
      square
      class="min-h-[2.125rem] rounded-none rounded-l-md max-sm:hidden"
      :disabled="!time || disabled"
      aria-label="Previous day"
      title="Previous day"
      @click="shiftDay(-1)"
    >
      <ChevronLeft aria-hidden="true" />
    </AppButton>
    <AppButton
      tone="ghost"
      class="min-h-[2.125rem] min-w-0 rounded-md px-2.5 text-xs whitespace-nowrap tabular-nums sm:rounded-none sm:border-x-line sm:text-sm"
      :disabled="!time || disabled"
      :loading="applying"
      aria-haspopup="dialog"
      :aria-label="time ? `Viewer time ${label}. Change time` : 'Loading viewer time'"
      @click="popover?.toggle($event)"
    >
      <span class="min-w-0 truncate">{{ clockText }}<span v-if="time"> UTC</span></span>
    </AppButton>
    <AppButton
      tone="ghost"
      square
      class="min-h-[2.125rem] rounded-none rounded-r-md max-sm:hidden"
      :disabled="!time || disabled"
      aria-label="Next day"
      title="Next day"
      @click="shiftDay(1)"
    >
      <ChevronRight aria-hidden="true" />
    </AppButton>
  </div>
  <AppPopover
    ref="popover"
    @show="draft = time.slice(0, 16)"
  >
    <form
      class="w-64 space-y-3 p-2"
      @submit.prevent="apply(`${draft}:00Z`)"
    >
      <label class="block space-y-1 text-xs font-medium text-secondary"
        >Date and time (UTC)
        <AppTextInput
          v-model="draft"
          type="datetime-local"
          step="60"
          required
        />
      </label>
      <div class="flex justify-end gap-2">
        <AppButton @click="apply(new Date().toISOString())">Now</AppButton>
        <AppButton
          button-type="submit"
          tone="primary"
          >Apply</AppButton
        >
      </div>
    </form>
  </AppPopover>
</template>

<script setup lang="ts">
  import AppTextInput from "@/components/ui/AppTextInput.vue";
  import { ChevronLeft, ChevronRight } from "@lucide/vue";
  import { computed, ref } from "vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import AppPopover from "@/components/ui/AppPopover.vue";
  import { formatUtc } from "@/views/home/plan/planTimeline";

  const props = defineProps<{ time: string; disabled: boolean; applying: boolean }>();
  const emit = defineEmits<{ apply: [timestamp: string] }>();
  const popover = ref<InstanceType<typeof AppPopover>>();
  const draft = ref("");
  const label = computed(() => (props.time ? formatUtc(Date.parse(props.time)) : "Loading time"));
  const clockText = computed(() => label.value.replace(/ UTC$/, ""));

  function shiftDay(days: number) {
    const nextTime = new Date(props.time);

    nextTime.setUTCDate(nextTime.getUTCDate() + days);
    apply(nextTime.toISOString());
  }

  function apply(timestamp: string) {
    popover.value!.hide();
    emit("apply", new Date(timestamp).toISOString());
  }
</script>
