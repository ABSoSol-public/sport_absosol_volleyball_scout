<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api";

const router = useRouter();
const username = ref("");
const password = ref("");
const error = ref("");

async function submit() {
  error.value = "";
  try {
    await api.login({ username: username.value, password: password.value });
    router.push("/matches");
  } catch (e) {
    error.value = e.message;
  }
}
</script>

<template>
  <div class="card" style="max-width: 24rem; margin: 3rem auto">
    <h1>Anmelden</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <form @submit.prevent="submit">
      <div class="form-row">
        <input
          v-model="username"
          placeholder="Benutzername"
          autocomplete="username"
          required
          style="flex: 1"
        />
      </div>
      <div class="form-row">
        <input
          v-model="password"
          type="password"
          placeholder="Passwort"
          autocomplete="current-password"
          required
          style="flex: 1"
        />
      </div>
      <button type="submit">Anmelden</button>
    </form>
  </div>
</template>
