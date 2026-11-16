import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import { defineConfigWithVueTs, vueTsConfigs } from "@vue/eslint-config-typescript";

export default defineConfigWithVueTs(
  { ignores: ["dist/**", "node_modules/**"] },
  js.configs.recommended,
  ...pluginVue.configs["flat/essential"],
  vueTsConfigs.recommended,
  { rules: { "vue/multi-word-component-names": "off" } },
  { files: ["src/**/*.{ts,vue}"], rules: { curly: "error" } }
);
