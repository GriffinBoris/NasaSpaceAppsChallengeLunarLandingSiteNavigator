import { publicRoutes } from "@/router/publicRoutes";
import { createRouter, createWebHashHistory } from "vue-router";

export default createRouter({
  history: createWebHashHistory(),
  routes: [...publicRoutes, { path: "/:pathMatch(.*)*", redirect: { name: "home" } }],
});
