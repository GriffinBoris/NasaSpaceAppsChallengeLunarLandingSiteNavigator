<template>
  <header class="group flex items-center gap-3 border-b border-line bg-surface px-3 py-2 sm:px-4">
    <RouterLink
      :to="{ name: 'home' }"
      class="flex shrink-0 items-center gap-2 rounded focus-visible:outline-2 focus-visible:outline-focus-ring"
    >
      <Moon
        class="size-5"
        aria-hidden="true"
      />

      <span class="font-display font-semibold tracking-tight [font-stretch:110%] max-lg:sr-only group-has-[#header-actions:empty]:not-sr-only"
        >Lunar Landing Site Navigator</span
      >
    </RouterLink>
    <div
      id="header-actions"
      class="flex min-w-0 flex-1 items-center gap-2"
    />
  </header>
</template>

<script setup lang="ts">
  import { Moon } from "@lucide/vue";
  import { RouterLink } from "vue-router";
</script>
