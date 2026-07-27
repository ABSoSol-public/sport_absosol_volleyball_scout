<script setup>
import { onMounted, ref } from "vue";
import { api } from "../api";

const teams = ref([]);
const selectedTeam = ref(null);
const error = ref("");

const newTeam = ref({ code: "", name: "" });
const newPlayer = ref({ number: null, last_name: "", first_name: "", position: "", is_libero: false });

async function loadTeams() {
  teams.value = await api.listTeams();
}

async function selectTeam(team) {
  selectedTeam.value = await api.getTeam(team.id);
}

async function createTeam() {
  error.value = "";
  try {
    await api.createTeam(newTeam.value);
    newTeam.value = { code: "", name: "" };
    await loadTeams();
  } catch (e) {
    error.value = e.message;
  }
}

async function addPlayer() {
  error.value = "";
  try {
    await api.addPlayer(selectedTeam.value.id, newPlayer.value);
    newPlayer.value = { number: null, last_name: "", first_name: "", position: "", is_libero: false };
    await selectTeam(selectedTeam.value);
  } catch (e) {
    error.value = e.message;
  }
}

onMounted(loadTeams);
</script>

<template>
  <h1>Teams</h1>
  <p v-if="error" class="error">{{ error }}</p>

  <div class="card">
    <h2>Neues Team</h2>
    <form class="form-row" @submit.prevent="createTeam">
      <input v-model="newTeam.code" placeholder="Code (z. B. TSV)" maxlength="8" required />
      <input v-model="newTeam.name" placeholder="Teamname" required />
      <button type="submit">Anlegen</button>
    </form>
  </div>

  <div class="card">
    <table>
      <thead>
        <tr><th>Code</th><th>Name</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="team in teams" :key="team.id">
          <td>{{ team.code }}</td>
          <td>{{ team.name }}</td>
          <td><button class="secondary" @click="selectTeam(team)">Kader</button></td>
        </tr>
      </tbody>
    </table>
  </div>

  <div v-if="selectedTeam" class="card">
    <h2>Kader: {{ selectedTeam.name }}</h2>
    <table>
      <thead>
        <tr><th>Nr.</th><th>Name</th><th>Position</th><th>Libero</th></tr>
      </thead>
      <tbody>
        <tr v-for="player in selectedTeam.players" :key="player.id">
          <td>{{ player.number }}</td>
          <td>{{ player.last_name }} {{ player.first_name }}</td>
          <td>{{ player.position }}</td>
          <td>{{ player.is_libero ? "L" : "" }}</td>
        </tr>
      </tbody>
    </table>
    <form class="form-row" @submit.prevent="addPlayer">
      <input v-model.number="newPlayer.number" type="number" min="0" max="99" placeholder="Nr." required style="width: 5rem" />
      <input v-model="newPlayer.last_name" placeholder="Nachname" required />
      <input v-model="newPlayer.first_name" placeholder="Vorname" />
      <input v-model="newPlayer.position" placeholder="Position" />
      <label><input v-model="newPlayer.is_libero" type="checkbox" /> Libero</label>
      <button type="submit">Spieler hinzufügen</button>
    </form>
  </div>
</template>
