<template>
  <ApplicationShellView>
    <RouterView />
  </ApplicationShellView>
</template>

<script setup lang="ts">
  import { RouterView } from "vue-router";
  import ApplicationShellView from "@/views/application/ApplicationShellView.vue";
</script>
