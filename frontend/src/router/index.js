import { createRouter, createWebHistory } from "vue-router";
import TeamsView from "../views/TeamsView.vue";
import MatchesView from "../views/MatchesView.vue";
import LiveScoutView from "../views/LiveScoutView.vue";

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/matches" },
    { path: "/teams", component: TeamsView },
    { path: "/matches", component: MatchesView },
    { path: "/matches/:id/live", component: LiveScoutView, props: true },
  ],
});
