<script setup>
import { onMounted, ref } from "vue";
import { api } from "../api";

const POSITIONS = [
  "Zuspieler",
  "Außenangreifer",
  "Diagonalangreifer",
  "Mittelblocker",
  "Libero",
  "Universalspieler",
];

const teams = ref([]);
const selectedTeam = ref(null);
const error = ref("");

const newTeam = ref({ code: "", name: "" });
const editingTeamId = ref(null);
const teamEdit = ref({ code: "", name: "" });

function blankPlayer() {
  return {
    number: null,
    last_name: "",
    first_name: "",
    position: "",
    is_libero: false,
    is_youth_player: false,
    is_primary_setter: false,
  };
}
const newPlayer = ref(blankPlayer());
const editingPlayerId = ref(null);
const playerEdit = ref(blankPlayer());

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

function startEditTeam(team) {
  editingTeamId.value = team.id;
  teamEdit.value = { code: team.code, name: team.name };
}

function cancelEditTeam() {
  editingTeamId.value = null;
}

async function saveTeam(team) {
  error.value = "";
  try {
    await api.updateTeam(team.id, teamEdit.value);
    editingTeamId.value = null;
    await loadTeams();
    if (selectedTeam.value?.id === team.id) await selectTeam(team);
  } catch (e) {
    error.value = e.message;
  }
}

async function addPlayer() {
  error.value = "";
  try {
    const data = { ...newPlayer.value, position: newPlayer.value.position || null };
    await api.addPlayer(selectedTeam.value.id, data);
    newPlayer.value = blankPlayer();
    await selectTeam(selectedTeam.value);
  } catch (e) {
    error.value = e.message;
  }
}

function startEditPlayer(player) {
  editingPlayerId.value = player.id;
  playerEdit.value = {
    number: player.number,
    last_name: player.last_name,
    first_name: player.first_name,
    position: player.position,
    is_libero: player.is_libero,
    is_youth_player: player.is_youth_player,
    is_primary_setter: player.is_primary_setter,
  };
}

function cancelEditPlayer() {
  editingPlayerId.value = null;
}

async function savePlayer(player) {
  error.value = "";
  try {
    const data = { ...playerEdit.value, position: playerEdit.value.position || null };
    await api.updatePlayer(selectedTeam.value.id, player.id, data);
    editingPlayerId.value = null;
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
      <div class="field">
        <label for="new-team-code">Code</label>
        <input id="new-team-code" v-model="newTeam.code" placeholder="z. B. TSV" maxlength="8" required />
      </div>
      <div class="field">
        <label for="new-team-name">Teamname</label>
        <input id="new-team-name" v-model="newTeam.name" placeholder="Vereinsname" required />
      </div>
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
          <template v-if="editingTeamId === team.id">
            <td><input v-model="teamEdit.code" maxlength="8" style="width: 6rem" /></td>
            <td><input v-model="teamEdit.name" style="width: 100%" /></td>
            <td>
              <button @click="saveTeam(team)">Speichern</button>
              <button class="secondary" @click="cancelEditTeam">Abbrechen</button>
            </td>
          </template>
          <template v-else>
            <td>{{ team.code }}</td>
            <td>{{ team.name }}</td>
            <td>
              <button class="secondary" @click="selectTeam(team)">Kader</button>
              <button class="secondary" @click="startEditTeam(team)">Bearbeiten</button>
            </td>
          </template>
        </tr>
      </tbody>
    </table>
  </div>

  <div v-if="selectedTeam" class="card">
    <h2>Kader: {{ selectedTeam.name }}</h2>
    <table>
      <thead>
        <tr>
          <th>Nr.</th><th>Name</th><th>Position</th><th>Libero</th><th>Jugend</th>
          <th title="Bestimmt bei zwei Zuspielern im Kader den Rotationscode (Z1–Z6) im Live-Scouting">
            Ref.-Zuspieler
          </th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="player in selectedTeam.players" :key="player.id">
          <template v-if="editingPlayerId === player.id">
            <td><input v-model.number="playerEdit.number" type="number" min="0" max="99" style="width: 4rem" /></td>
            <td>
              <input v-model="playerEdit.last_name" placeholder="Nachname" style="width: 7rem" />
              <input v-model="playerEdit.first_name" placeholder="Vorname" style="width: 7rem" />
            </td>
            <td>
              <select v-model="playerEdit.position">
                <option value="">–</option>
                <option v-for="p in POSITIONS" :key="p" :value="p">{{ p }}</option>
              </select>
            </td>
            <td><input v-model="playerEdit.is_libero" type="checkbox" /></td>
            <td><input v-model="playerEdit.is_youth_player" type="checkbox" /></td>
            <td><input v-model="playerEdit.is_primary_setter" type="checkbox" /></td>
            <td>
              <button @click="savePlayer(player)">Speichern</button>
              <button class="secondary" @click="cancelEditPlayer">Abbrechen</button>
            </td>
          </template>
          <template v-else>
            <td>{{ player.number }}</td>
            <td>{{ player.last_name }} {{ player.first_name }}</td>
            <td>{{ player.position }}</td>
            <td>{{ player.is_libero ? "L" : "" }}</td>
            <td>{{ player.is_youth_player ? "J" : "" }}</td>
            <td>{{ player.is_primary_setter ? "Z" : "" }}</td>
            <td><button class="secondary" @click="startEditPlayer(player)">Bearbeiten</button></td>
          </template>
        </tr>
      </tbody>
    </table>

    <h3>Spieler hinzufügen</h3>
    <form class="form-row" @submit.prevent="addPlayer">
      <div class="field">
        <label for="new-player-number">Nr.</label>
        <input
          id="new-player-number"
          v-model.number="newPlayer.number"
          type="number"
          min="0"
          max="99"
          required
          style="width: 5rem"
        />
      </div>
      <div class="field">
        <label for="new-player-last-name">Nachname</label>
        <input id="new-player-last-name" v-model="newPlayer.last_name" required />
      </div>
      <div class="field">
        <label for="new-player-first-name">Vorname</label>
        <input id="new-player-first-name" v-model="newPlayer.first_name" />
      </div>
      <div class="field">
        <label for="new-player-position">Position</label>
        <select id="new-player-position" v-model="newPlayer.position">
          <option value="">– keine Angabe –</option>
          <option v-for="p in POSITIONS" :key="p" :value="p">{{ p }}</option>
        </select>
      </div>
      <div class="field-checkbox">
        <input id="new-player-libero" v-model="newPlayer.is_libero" type="checkbox" />
        <label for="new-player-libero">Libero</label>
      </div>
      <div class="field-checkbox">
        <input id="new-player-youth" v-model="newPlayer.is_youth_player" type="checkbox" />
        <label for="new-player-youth">Jugendspieler</label>
      </div>
      <div class="field-checkbox">
        <input id="new-player-primary-setter" v-model="newPlayer.is_primary_setter" type="checkbox" />
        <label for="new-player-primary-setter" title="Bestimmt bei zwei Zuspielern im Kader den Rotationscode (Z1–Z6) im Live-Scouting">
          Referenz-Zuspieler
        </label>
      </div>
      <button type="submit">Spieler hinzufügen</button>
    </form>
  </div>
</template>
