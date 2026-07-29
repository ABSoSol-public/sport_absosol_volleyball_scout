<script setup>
import { computed, onMounted, ref } from "vue";
import { api } from "../api";

const props = defineProps({ id: { type: String, required: true } });

const match = ref(null);
const sets = ref([]);
const stats = ref(null);
const playerNames = ref({}); // "home:7" -> "Musterfrau"
const error = ref("");
const loading = ref(true);

const STATUS_LABEL = { scheduled: "geplant", live: "läuft", finished: "beendet" };

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

const setsWon = computed(() => {
  let home = 0;
  let away = 0;
  for (const s of sets.value) {
    if (s.home_points > s.away_points) home += 1;
    else if (s.away_points > s.home_points) away += 1;
  }
  return { home, away };
});

function playerLabel(side, number) {
  const name = playerNames.value[`${side}:${number}`];
  return name ? `${number} · ${name}` : `${number}`;
}

async function loadRoster(teamId, side) {
  try {
    const team = await api.getTeam(teamId);
    for (const player of team.players) {
      playerNames.value[`${side}:${player.number}`] = player.last_name;
    }
  } catch {
    /* Kader nicht ladbar – Anzeige fällt auf reine Nummern zurück */
  }
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    match.value = await api.getMatch(props.id);
    [sets.value] = await Promise.all([
      api.getMatchSets(props.id),
      loadRoster(match.value.home_team.id, "home"),
      loadRoster(match.value.away_team.id, "away"),
    ]);
    if (sets.value.length > 0) {
      stats.value = await api.getMatchStatistics(props.id);
    }
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div v-if="loading" class="empty-state">Lädt …</div>
  <p v-else-if="error" class="error">{{ error }}</p>
  <div v-else-if="match">
    <div class="match-header">
      <h1>{{ match.home_team.name }} – {{ match.away_team.name }}</h1>
      <span class="badge" :class="`badge-${match.status}`">{{ STATUS_LABEL[match.status] }}</span>
    </div>
    <p class="muted">
      {{ match.match_date }}<span v-if="match.competition"> · {{ match.competition }}</span>
    </p>

    <div v-if="sets.length === 0" class="card empty-state">
      <p>Für dieses Match liegen noch keine Analyse-Daten vor.</p>
      <p class="muted">
        Vermutlich ein live gescoutetes Match, dessen Ballwechsel noch nicht in den
        Statistik-Strang übernommen wurden.
      </p>
      <RouterLink :to="`/matches/${match.id}/live`"><button>Zur Live-Ansicht</button></RouterLink>
    </div>

    <template v-else>
      <div class="card">
        <div class="final-score">
          <div class="score-side">
            <div class="team-name">{{ match.home_team.name }}</div>
            <div class="sets-won">{{ setsWon.home }}</div>
          </div>
          <div class="score-vs">:</div>
          <div class="score-side">
            <div class="team-name">{{ match.away_team.name }}</div>
            <div class="sets-won">{{ setsWon.away }}</div>
          </div>
        </div>
        <div class="score-chips">
          <span v-for="s in sets" :key="s.number" class="score-chip">
            Satz {{ s.number }}: {{ s.home_points }}:{{ s.away_points }}
            <small v-if="s.duration_minutes"> ({{ s.duration_minutes }} min)</small>
          </span>
        </div>
      </div>

      <div v-if="stats" class="stat-grid">
        <div class="card" v-for="side in ['home', 'away']" :key="side">
          <h2>{{ match[`${side}_team`].name }}</h2>
          <div class="meter-row">
            <span class="meter-label">Break-Quote</span>
            <div class="meter">
              <span :style="{ width: (stats[`${side}_team`].break_rate ?? 0) + '%' }"></span>
            </div>
            <span class="meter-value">{{ pct(stats[`${side}_team`].break_rate) }}</span>
          </div>
          <div class="meter-row">
            <span class="meter-label">Side-Out-Quote</span>
            <div class="meter">
              <span :style="{ width: (stats[`${side}_team`].side_out_rate ?? 0) + '%' }"></span>
            </div>
            <span class="meter-value">{{ pct(stats[`${side}_team`].side_out_rate) }}</span>
          </div>
          <table class="compact">
            <thead>
              <tr><th>Punktquelle</th><th>Anzahl</th></tr>
            </thead>
            <tbody>
              <tr>
                <td>Aufschlag (Ass)</td>
                <td>{{ stats[`${side}_team`].point_sources.serve }}</td>
              </tr>
              <tr>
                <td>Angriff</td>
                <td>{{ stats[`${side}_team`].point_sources.attack }}</td>
              </tr>
              <tr>
                <td>Block</td>
                <td>{{ stats[`${side}_team`].point_sources.block }}</td>
              </tr>
              <tr>
                <td>Gegnerfehler</td>
                <td>{{ stats[`${side}_team`].point_sources.opponent_errors }}</td>
              </tr>
              <tr class="total-row">
                <td>Gesamt</td>
                <td>{{ stats[`${side}_team`].points_total }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="stats" class="card" v-for="side in ['home', 'away']" :key="`players-${side}`">
        <h2>Spieler-Statistik — {{ match[`${side}_team`].name }}</h2>
        <div class="table-scroll">
          <table class="compact stat-table">
            <thead>
              <tr>
                <th rowspan="2">Nr.</th>
                <th colspan="3">Aufschlag</th>
                <th colspan="2">Annahme</th>
                <th colspan="3">Angriff</th>
                <th colspan="2">Block</th>
              </tr>
              <tr>
                <th title="Gesamtzahl Aufschläge">Tot</th>
                <th title="Asse">Ass</th>
                <th title="Aufschlagfehler">Err</th>
                <th title="Gesamtzahl Annahmen">Tot</th>
                <th title="Positivquote (+/#)">Pos%</th>
                <th title="Gesamtzahl Angriffe">Tot</th>
                <th title="Effizienz (Kills-Err-Blocked)/Tot">Eff</th>
                <th title="Punktquote">Pkt%</th>
                <th title="Gesamtzahl Blockaktionen">Tot</th>
                <th title="Blockpunkte">Pkt</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in stats[`${side}_players`]" :key="p.player_number">
                <td>{{ playerLabel(side, p.player_number) }}</td>
                <td>{{ p.serve.total }}</td>
                <td>{{ p.serve.aces }}</td>
                <td>{{ p.serve.errors }}</td>
                <td>{{ p.reception.total }}</td>
                <td>{{ pct(p.reception.positive_pct) }}</td>
                <td>{{ p.attack.total }}</td>
                <td :class="effClass(p.attack.efficiency)">{{ num(p.attack.efficiency) }}</td>
                <td>{{ pct(p.attack.kill_pct) }}</td>
                <td>{{ p.block.total }}</td>
                <td>{{ p.block.points }}</td>
              </tr>
              <tr v-if="stats[`${side}_players`].length === 0">
                <td colspan="11" class="muted">Keine Aktionen erfasst.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="stats" class="stat-grid">
        <div class="card" v-for="side in ['home', 'away']" :key="`rotation-${side}`">
          <h2>Rotation — {{ match[`${side}_team`].name }}</h2>
          <table class="compact">
            <thead>
              <tr>
                <th>Pos.</th>
                <th title="Break-Quote bei eigenem Aufschlag">Break%</th>
                <th title="Side-Out-Quote bei eigener Annahme">SO%</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in stats[`${side}_rotations`]" :key="r.position">
                <td>{{ r.position }}</td>
                <td>{{ pct(r.break_rate) }}</td>
                <td>{{ pct(r.side_out_rate) }}</td>
              </tr>
              <tr v-if="stats[`${side}_rotations`].length === 0">
                <td colspan="3" class="muted">Keine Rotationsdaten.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>
