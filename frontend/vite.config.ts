import tailwindcss from "@tailwindcss/vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  base: "/static/",
  plugins: [tailwindcss(), vue()],
  server: {
    port: 5173,
    strictPort: true,
    origin: "http://localhost:5173",
  },
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  build: { rollupOptions: { output: { manualChunks: (id) => (id.includes("node_modules/three/") ? "three" : undefined) } } },
});
