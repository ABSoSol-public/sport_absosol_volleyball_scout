<script setup>
import { onMounted, ref } from "vue";
import { api } from "../api";

const matches = ref([]);
const teams = ref([]);
const error = ref("");

const today = new Date().toISOString().slice(0, 10);
const newMatch = ref({
  match_date: today,
  competition: "",
  home_team_id: null,
  away_team_id: null,
});

async function load() {
  [matches.value, teams.value] = await Promise.all([api.listMatches(), api.listTeams()]);
}

async function createMatch() {
  error.value = "";
  try {
    await api.createMatch(newMatch.value);
    await load();
  } catch (e) {
    error.value = e.message;
  }
}

const importInfo = ref("");

async function importDvw(event) {
  const file = event.target.files[0];
  if (!file) return;
  error.value = "";
  importInfo.value = "Importiere …";
  try {
    const result = await api.importDvw(file);
    importInfo.value = `Import OK: ${result.sets} Sätze, ${result.rallies} Ballwechsel, ${result.actions} Aktionen.`;
    await load();
  } catch (e) {
    importInfo.value = "";
    error.value = e.message;
  } finally {
    event.target.value = "";
  }
}

onMounted(load);
</script>

<template>
  <h1>Matches</h1>
  <p v-if="error" class="error">{{ error }}</p>

  <div class="card">
    <h2>Neues Match</h2>
    <form class="form-row" @submit.prevent="createMatch">
      <div class="field">
        <label for="new-match-date">Datum</label>
        <input id="new-match-date" v-model="newMatch.match_date" type="date" required />
      </div>
      <div class="field">
        <label for="new-match-competition">Wettbewerb</label>
        <input id="new-match-competition" v-model="newMatch.competition" placeholder="optional" />
      </div>
      <div class="field">
        <label for="new-match-home">Heimteam</label>
        <select id="new-match-home" v-model.number="newMatch.home_team_id" required>
          <option :value="null" disabled>Heimteam …</option>
          <option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option>
        </select>
      </div>
      <div class="field">
        <label for="new-match-away">Gastteam</label>
        <select id="new-match-away" v-model.number="newMatch.away_team_id" required>
          <option :value="null" disabled>Gastteam …</option>
          <option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option>
        </select>
      </div>
      <button type="submit">Anlegen</button>
    </form>
    <p v-if="teams.length < 2">Zuerst mindestens zwei Teams unter „Teams“ anlegen.</p>
    <div class="form-row">
      <div class="field">
        <label for="dvw-file">DataVolley-Datei importieren (.dvw)</label>
        <input id="dvw-file" type="file" accept=".dvw" @change="importDvw" />
      </div>
      <span v-if="importInfo">{{ importInfo }}</span>
    </div>
  </div>

  <div class="card">
    <table>
      <thead>
        <tr><th>Datum</th><th>Wettbewerb</th><th>Heim</th><th>Gast</th><th>Status</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="match in matches" :key="match.id">
          <td>{{ match.match_date }}</td>
          <td>{{ match.competition }}</td>
          <td>{{ match.home_team.name }}</td>
          <td>{{ match.away_team.name }}</td>
          <td>{{ match.status }}</td>
          <td>
            <RouterLink v-if="match.status === 'finished'" :to="`/matches/${match.id}`">
              <button>Ansehen</button>
            </RouterLink>
            <RouterLink v-else :to="`/matches/${match.id}/live`">
              <button>Live-Scouting</button>
            </RouterLink>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
