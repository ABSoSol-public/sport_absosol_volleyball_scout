<script setup>
import { onMounted, ref, watch } from "vue";
import { api } from "../api";

const props = defineProps({
  teamId: { type: [String, Number], required: true },
  number: { type: [String, Number], required: true },
});

const CATEGORY_LABELS = {
  serve: "Aufschlag",
  reception: "Annahme",
  attack: "Angriff",
  block: "Block",
};

const disciplines = ref([]);
const seasons = ref([]);
const discipline = ref("hall_6");
const seasonId = ref("");

const profile = ref(null);
const card = ref(null);
const error = ref("");
const loading = ref(true);

function pct(value) {
  return value === null || value === undefined ? "–" : `${value.toFixed(1)} %`;
}

function num(value, digits = 2) {
  return value === null || value === undefined ? "–" : value.toFixed(digits);
}

function effClass(value) {
  if (value === null || value === undefined) return "";
  if (value >= 0.3) return "stat-good";
  if (value < 0) return "stat-bad";
  return "";
}

function zoneLabel(t) {
  if (t.start_zone === null && t.end_zone === null) return "–";
  if (t.end_zone === null) return `${t.start_zone}`;
  return `${t.start_zone ?? "–"} → ${t.end_zone}`;
}

function ratingClass(rating) {
  if (rating === null || rating === undefined) return "";
  if (rating >= 65) return "stat-good";
  if (rating < 35) return "stat-bad";
  return "";
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const filters = { discipline: discipline.value, seasonId: seasonId.value || undefined };
    [profile.value, card.value] = await Promise.all([
      api.getPlayerProfile(props.teamId, props.number, filters),
      api.getPlayerCard(props.teamId, props.number, filters),
    ]);
  } catch (e) {
    error.value = e.message;
    profile.value = null;
    card.value = null;
  } finally {
    loading.value = false;
  }
}

async function loadFilters() {
  [disciplines.value, seasons.value] = await Promise.all([
    api.listDisciplines(),
    api.listSeasons(),
  ]);
}

onMounted(async () => {
  await loadFilters();
  await load();
});

watch([discipline, seasonId], load);
</script>

<template>
  <div v-if="loading" class="empty-state">Lädt …</div>
  <p v-else-if="error" class="error">{{ error }}</p>
  <div v-else-if="profile">
    <div class="match-header">
      <h1>{{ profile.last_name }} {{ profile.first_name }} — Nr. {{ profile.number }}</h1>
    </div>
    <p class="muted">
      {{ profile.position || "Position unbekannt" }}
      <span v-if="profile.season"> · Saison {{ profile.season.label }}</span>
      <span v-else> · Gesamte Karriere</span>
    </p>

    <div class="form-row">
      <div class="field">
        <label for="profile-discipline">Disziplin</label>
        <select id="profile-discipline" v-model="discipline">
          <option v-for="d in disciplines" :key="d.code" :value="d.code">{{ d.label }}</option>
        </select>
      </div>
      <div class="field">
        <label for="profile-season">Saison</label>
        <select id="profile-season" v-model="seasonId">
          <option value="">Gesamte Karriere</option>
          <option v-for="s in seasons" :key="s.id" :value="s.id">{{ s.label }}</option>
        </select>
      </div>
    </div>

    <!-- FIFA-Style Skill-Karte: Perzentilrang gegen alle Spieler derselben
         Disziplin in der Datenbank (siehe app/player_card.py) — dynamisch
         berechnet, keine feste Notenskala. -->
    <div v-if="card" class="card">
      <h2>Skill-Karte</h2>
      <p class="muted">
        Bewertung 0–100 relativ zu allen Spieler:innen mit ausreichend Aktionen in
        „{{ disciplines.find((d) => d.code === card.discipline)?.label ?? card.discipline }}"
        (Perzentilrang, keine feste Notenskala).
      </p>
      <div class="skill-card-overall">
        <span class="skill-card-overall-label">Gesamt</span>
        <span class="skill-card-overall-value" :class="ratingClass(card.overall)">
          {{ card.overall ?? "–" }}
        </span>
      </div>
      <div v-for="(name, key) in CATEGORY_LABELS" :key="key" class="meter-row">
        <span class="meter-label">{{ name }}</span>
        <div class="meter">
          <span :style="{ width: (card.categories[key].rating ?? 0) + '%' }"></span>
        </div>
        <span
          class="meter-value"
          :class="ratingClass(card.categories[key].rating)"
          :title="`${card.categories[key].sample_size} Aktionen erfasst`"
        >
          {{ card.categories[key].rating ?? "–" }}
        </span>
      </div>
      <p class="muted">
        Kategorien ohne Wertung: zu wenig erfasste Aktionen (unter dem Mindestwert für eine
        verlässliche Einschätzung), keine erfundene Note.
      </p>
    </div>

    <!-- NFL-Style Playbook: welche Angriffs-/Aufschlagzonen dieser Spieler am
         häufigsten nutzt und wie erfolgreich (siehe app/engine/player_profile.py). -->
    <div class="stat-grid">
      <div class="card">
        <h2>Angriffstendenzen</h2>
        <table class="compact stat-table">
          <thead>
            <tr><th>Zone</th><th>Versuche</th><th>Kills</th><th>Fehler</th><th>Geblockt</th><th>Eff.</th></tr>
          </thead>
          <tbody>
            <tr v-for="t in profile.attack_tendencies" :key="`${t.start_zone}-${t.end_zone}`">
              <td>{{ zoneLabel(t) }}</td>
              <td>{{ t.attempts }}</td>
              <td>{{ t.positive }}</td>
              <td>{{ t.errors }}</td>
              <td>{{ t.blocked }}</td>
              <td :class="effClass(t.efficiency)">{{ num(t.efficiency) }}</td>
            </tr>
            <tr v-if="profile.attack_tendencies.length === 0">
              <td colspan="6" class="muted">Keine Angriffe mit Zonenangabe erfasst.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="card">
        <h2>Aufschlagtendenzen</h2>
        <table class="compact stat-table">
          <thead>
            <tr><th>Zone</th><th>Versuche</th><th>Asse</th><th>Fehler</th><th>Pos%</th></tr>
          </thead>
          <tbody>
            <tr v-for="t in profile.serve_tendencies" :key="`${t.start_zone}-${t.end_zone}`">
              <td>{{ zoneLabel(t) }}</td>
              <td>{{ t.attempts }}</td>
              <td>{{ t.positive }}</td>
              <td>{{ t.errors }}</td>
              <td>{{ pct(t.positive_pct) }}</td>
            </tr>
            <tr v-if="profile.serve_tendencies.length === 0">
              <td colspan="5" class="muted">Keine Aufschläge mit Zonenangabe erfasst.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <h2>Karriere — Saisonverlauf</h2>
      <div class="table-scroll">
        <table class="compact stat-table">
          <thead>
            <tr>
              <th rowspan="2">Saison</th>
              <th rowspan="2">Matches</th>
              <th colspan="3">Aufschlag</th>
              <th colspan="2">Annahme</th>
              <th colspan="3">Angriff</th>
              <th colspan="2">Block</th>
            </tr>
            <tr>
              <th>Tot</th><th>Ass</th><th>Err</th>
              <th>Tot</th><th>Pos%</th>
              <th>Tot</th><th>Eff</th><th>Pkt%</th>
              <th>Tot</th><th>Pkt</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Gesamt</strong></td>
              <td>{{ profile.career.matches }}</td>
              <td>{{ profile.career.serve.total }}</td>
              <td>{{ profile.career.serve.aces }}</td>
              <td>{{ profile.career.serve.errors }}</td>
              <td>{{ profile.career.reception.total }}</td>
              <td>{{ pct(profile.career.reception.positive_pct) }}</td>
              <td>{{ profile.career.attack.total }}</td>
              <td :class="effClass(profile.career.attack.efficiency)">{{ num(profile.career.attack.efficiency) }}</td>
              <td>{{ pct(profile.career.attack.kill_pct) }}</td>
              <td>{{ profile.career.block.total }}</td>
              <td>{{ profile.career.block.points }}</td>
            </tr>
            <tr v-for="entry in profile.by_season" :key="entry.season.id">
              <td>{{ entry.season.label }}</td>
              <td>{{ entry.stats.matches }}</td>
              <td>{{ entry.stats.serve.total }}</td>
              <td>{{ entry.stats.serve.aces }}</td>
              <td>{{ entry.stats.serve.errors }}</td>
              <td>{{ entry.stats.reception.total }}</td>
              <td>{{ pct(entry.stats.reception.positive_pct) }}</td>
              <td>{{ entry.stats.attack.total }}</td>
              <td :class="effClass(entry.stats.attack.efficiency)">{{ num(entry.stats.attack.efficiency) }}</td>
              <td>{{ pct(entry.stats.attack.kill_pct) }}</td>
              <td>{{ entry.stats.block.total }}</td>
              <td>{{ entry.stats.block.points }}</td>
            </tr>
            <tr v-if="profile.by_season.length === 0">
              <td colspan="12" class="muted">Keine Saison zugeordnet.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
