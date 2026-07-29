import { createRouter, createWebHistory } from "vue-router";
import TeamsView from "../views/TeamsView.vue";
import MatchesView from "../views/MatchesView.vue";
import MatchDetailView from "../views/MatchDetailView.vue";
import LiveScoutView from "../views/LiveScoutView.vue";
import LoginView from "../views/LoginView.vue";

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/matches" },
    { path: "/login", component: LoginView },
    { path: "/teams", component: TeamsView },
    { path: "/matches", component: MatchesView },
    { path: "/matches/:id", component: MatchDetailView, props: true },
    { path: "/matches/:id/live", component: LiveScoutView, props: true },
  ],
});
