import { createPinia } from "pinia";
import PrimeVue from "primevue/config";
import { createApp } from "vue";
import App from "./App.vue";
import "@fontsource-variable/inter";
import "@fontsource-variable/archivo/wdth.css";
import "./assets/base.css";
import router from "./router";

const app = createApp(App);
app.use(createPinia());
app.use(PrimeVue, { unstyled: true });
app.use(router);
app.mount("#app");
