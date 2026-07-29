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
        <div class="field" style="flex: 1">
          <label for="login-username">Benutzername</label>
          <input
            id="login-username"
            v-model="username"
            autocomplete="username"
            required
            style="width: 100%"
          />
        </div>
      </div>
      <div class="form-row">
        <div class="field" style="flex: 1">
          <label for="login-password">Passwort</label>
          <input
            id="login-password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
            style="width: 100%"
          />
        </div>
      </div>
      <button type="submit">Anmelden</button>
    </form>
  </div>
</template>
