<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "./api";

const route = useRoute();
const router = useRouter();
const user = ref(null);

async function loadUser() {
  try {
    user.value = await api.me();
  } catch {
    user.value = null; // 401 → api.js leitet bereits auf /login um
  }
}

async function logout() {
  await api.logout();
  user.value = null;
  router.push("/login");
}

// Nach erfolgreichem Login (Routenwechsel weg von /login) Nutzer nachladen
router.afterEach((to, from) => {
  if (from.path === "/login" && to.path !== "/login") loadUser();
});

onMounted(() => {
  if (route.path !== "/login") loadUser();
});
</script>

<template>
  <nav class="topnav">
    <span class="brand">🏐 ABSoSol Volleyball Scout</span>
    <template v-if="user">
      <RouterLink to="/matches">Matches</RouterLink>
      <RouterLink to="/teams">Teams</RouterLink>
      <span style="margin-left: auto">
        {{ user.username }}<span v-if="user.role === 'viewer'"> (nur lesen)</span>
        · <a href="#" @click.prevent="logout">Abmelden</a>
      </span>
    </template>
  </nav>
  <main :class="{ 'main-wide': route.meta.wide }">
    <RouterView />
  </main>
</template>
