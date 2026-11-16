<template>
  <AppContainer>
    <a
      href="#main-content"
      class="sr-only focus:not-sr-only focus:absolute focus:z-10 focus:bg-surface focus:p-4"
      @click.prevent="focusMainContent"
      >Skip to content</a
    >
    <ApplicationHeader />
    <MainContentPane>
      <slot />
    </MainContentPane>
  </AppContainer>
</template>

<script setup lang="ts">
  import AppContainer from "@/components/layout/AppContainer.vue";
  import MainContentPane from "@/components/layout/MainContentPane.vue";
  import ApplicationHeader from "@/views/application/components/ApplicationHeader.vue";

  function focusMainContent() {
    document.getElementById("main-content")?.focus();
  }
</script>
