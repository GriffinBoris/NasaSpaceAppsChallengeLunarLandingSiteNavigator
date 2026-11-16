<template>
  <Tabs
    v-model:value="active"
    lazy
    :pt="{ root: { class: 'flex flex-col gap-3' } }"
  >
    <TabList :pt="{ tabList: { class: 'flex gap-1 border-b border-line' }, activeBar: { class: 'hidden' } }">
      <Tab
        v-for="tab in tabs"
        :key="tab.value"
        :value="tab.value"
        :pt="{ root: { class: TAB_CLASS } }"
        >{{ tab.label }}</Tab
      >
    </TabList>
    <TabPanels>
      <TabPanel
        v-for="tab in tabs"
        :key="tab.value"
        :value="tab.value"
        :pt="{ root: { class: 'rounded focus-visible:outline-2 focus-visible:outline-focus-ring' } }"
      >
        <slot :name="tab.value" />
      </TabPanel>
    </TabPanels>
  </Tabs>
</template>

<script setup lang="ts">
  import Tab from "primevue/tab";
  import TabList from "primevue/tablist";
  import TabPanel from "primevue/tabpanel";
  import TabPanels from "primevue/tabpanels";
  import Tabs from "primevue/tabs";
  import { ref } from "vue";

  const TAB_CLASS =
    "-mb-px cursor-pointer border-b-2 border-transparent px-2.5 py-2 text-sm pointer-coarse:min-h-11 font-medium text-secondary hover:text-body active:bg-surface-muted focus-visible:outline-2 focus-visible:outline-focus-ring aria-selected:border-body aria-selected:text-body";

  const props = defineProps<{ tabs: { value: string; label: string }[] }>();
  const active = ref(props.tabs[0]!.value);
</script>
