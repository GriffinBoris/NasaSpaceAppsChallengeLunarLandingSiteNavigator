import type { RouteRecordRaw } from "vue-router";

export const publicRoutes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "home",
    component: () => import("@/views/home/HomeView.vue"),
    children: [
      {
        path: "plans/:studyId(\\d+)",
        name: "plan",
        component: () => import("@/views/home/plan/PlanView.vue"),
        props: (route) => ({ studyId: Number(route.params.studyId) }),
      },
    ],
  },
];
