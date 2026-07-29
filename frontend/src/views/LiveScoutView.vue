<script setup>
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import VolleyballCourt from "../components/VolleyballCourt.vue";

const props = defineProps({ id: { type: String, required: true } });

const match = ref(null);
const state = ref(null);
const error = ref("");

const lineupInput = ref({ serving: "home", home: "", away: "" });
const actionCodes = ref("");
const sub = ref({ side: "home", player_out: null, player_in: null });

function appendZone(selection) {
  actionCodes.value += selection.zone;
}

const setRunning = computed(() => state.value?.set_running);
const current = computed(() => state.value?.current_set);

// Anzeige-Reihenfolge des Courts: vorne Zonen 4-3-2, hinten 5-6-1.
// Engine-Lineup ist [Zone1, Zone2, ..., Zone6] → Index = Zone - 1.
const ZONE_ORDER = [4, 3, 2, 5, 6, 1];

function courtZones(side) {
  const lineup = current.value?.lineups?.[side] ?? [];
  return ZONE_ORDER.map((zone) => ({ zone, player: lineup[zone - 1] }));
}

async function refresh() {
  [match.value, state.value] = await Promise.all([
    api.getMatch(props.id),
    api.liveState(props.id),
  ]);
}

async function run(action) {
  error.value = "";
  try {
    state.value = await action();
    match.value = await api.getMatch(props.id);
  } catch (e) {
    error.value = e.message;
  }
}

function parseLineup(text) {
  return text
    .split(/[\s,;]+/)
    .filter(Boolean)
    .map(Number);
}

const startSet = () =>
  run(() =>
    api.startSet(props.id, {
      serving: lineupInput.value.serving,
      home_lineup: parseLineup(lineupInput.value.home),
      away_lineup: parseLineup(lineupInput.value.away),
    })
  );

const rally = (winner) =>
  run(() => {
    const actions = actionCodes.value.split(/\s+/).filter(Boolean);
    actionCodes.value = "";
    return api.rally(props.id, { winner, actions });
  });

const timeout = (side) => run(() => api.timeout(props.id, { side }));
const undo = () => run(() => api.undo(props.id));
const substitute = () =>
  run(() =>
    api.substitution(props.id, {
      side: sub.value.side,
      player_out: sub.value.player_out,
      player_in: sub.value.player_in,
    })
  );

onMounted(refresh);
</script>

<template>
  <div v-if="match && state">
    <h1>{{ match.home_team.name }} – {{ match.away_team.name }}</h1>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="card scoreboard">
      <div>
        <div class="team">
          <span v-if="current && current.serving === 'home'" class="serve-dot" title="Aufschlag"></span>
          {{ match.home_team.name }}
        </div>
        <div class="points">{{ current ? current.points.home : "–" }}</div>
        <div class="sets">Sätze: {{ state.sets_won.home }}</div>
      </div>
      <div>
        <div v-if="current">Satz {{ current.number }}</div>
        <div v-for="s in state.set_scores" :key="s.number" class="sets">
          Satz {{ s.number }}: {{ s.home }}:{{ s.away }}
        </div>
        <strong v-if="state.match_finished">Match beendet</strong>
      </div>
      <div>
        <div class="team">
          <span v-if="current && current.serving === 'away'" class="serve-dot" title="Aufschlag"></span>
          {{ match.away_team.name }}
        </div>
        <div class="points">{{ current ? current.points.away : "–" }}</div>
        <div class="sets">Sätze: {{ state.sets_won.away }}</div>
      </div>
    </div>

    <!-- Satz starten -->
    <div v-if="!setRunning && !state.match_finished" class="card">
      <h2>Satz {{ state.set_scores.length + 1 }} starten</h2>
      <div class="form-row">
        <div class="field">
          <label for="serving-select">Aufschlag</label>
          <select id="serving-select" v-model="lineupInput.serving">
            <option value="home">{{ match.home_team.name }}</option>
            <option value="away">{{ match.away_team.name }}</option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="field" style="flex: 1">
          <label for="lineup-home">Aufstellung Heim (Zonen 1–6)</label>
          <input
            id="lineup-home"
            v-model="lineupInput.home"
            placeholder="z. B. 7 12 4 9 2 15"
            style="width: 100%"
          />
        </div>
      </div>
      <div class="form-row">
        <div class="field" style="flex: 1">
          <label for="lineup-away">Aufstellung Gast (Zonen 1–6)</label>
          <input
            id="lineup-away"
            v-model="lineupInput.away"
            placeholder="z. B. 3 8 11 6 1 10"
            style="width: 100%"
          />
        </div>
      </div>
      <button @click="startSet">Satz starten</button>
    </div>

    <!-- Laufender Satz -->
    <div v-if="setRunning" class="card">
      <div style="display: flex; gap: 2rem; justify-content: center; flex-wrap: wrap">
        <div>
          <h3 style="text-align: center">{{ match.home_team.code }}</h3>
          <div class="court">
            <div v-for="cell in courtZones('home')" :key="cell.zone" class="zone">
              {{ cell.player }}
              <small>Zone {{ cell.zone }}</small>
            </div>
          </div>
          <div style="text-align: center">
            Auszeiten: {{ current.timeouts.home }} · Wechsel: {{ current.substitutions.home }}
          </div>
        </div>
        <div>
          <h3 style="text-align: center">{{ match.away_team.code }}</h3>
          <div class="court">
            <div v-for="cell in courtZones('away')" :key="cell.zone" class="zone">
              {{ cell.player }}
              <small>Zone {{ cell.zone }}</small>
            </div>
          </div>
          <div style="text-align: center">
            Auszeiten: {{ current.timeouts.away }} · Wechsel: {{ current.substitutions.away }}
          </div>
        </div>
      </div>

      <div class="form-row" style="margin-top: 1rem">
        <div class="field" style="flex: 1">
          <label for="action-codes">Scout-Codes (optional)</label>
          <input
            id="action-codes"
            v-model="actionCodes"
            placeholder="z. B. 5SQ- a11RQ+ a14AH#"
            style="width: 100%"
            @keyup.enter="null"
          />
        </div>
      </div>

      <details class="card">
        <summary>Zonen-Helfer (Netz oben, drehbar für die Gegenseite)</summary>
        <VolleyballCourt @select="appendZone" />
        <p class="muted" style="text-align: center">
          Klick fügt die Zonen-Ziffer ans Ende der Scout-Code-Zeile an; die Subzone (A–D)
          dient nur zur Orientierung.
        </p>
      </details>

      <div class="actions-bar">
        <button @click="rally('home')">+ Punkt {{ match.home_team.code }}</button>
        <button @click="rally('away')">+ Punkt {{ match.away_team.code }}</button>
        <button class="secondary" @click="timeout('home')">Auszeit {{ match.home_team.code }}</button>
        <button class="secondary" @click="timeout('away')">Auszeit {{ match.away_team.code }}</button>
        <button class="secondary" @click="undo">↩ Undo</button>
      </div>

      <div class="form-row" style="margin-top: 1rem">
        <div class="field">
          <label for="sub-side">Team</label>
          <select id="sub-side" v-model="sub.side">
            <option value="home">{{ match.home_team.code }}</option>
            <option value="away">{{ match.away_team.code }}</option>
          </select>
        </div>
        <div class="field">
          <label for="sub-out">Raus</label>
          <input id="sub-out" v-model.number="sub.player_out" type="number" style="width: 6rem" />
        </div>
        <div class="field">
          <label for="sub-in">Rein</label>
          <input id="sub-in" v-model.number="sub.player_in" type="number" style="width: 6rem" />
        </div>
        <button class="secondary" @click="substitute">Wechsel</button>
      </div>
    </div>

    <div v-if="state.match_finished" class="card">
      <h2>Endstand</h2>
      <p>
        Sätze {{ state.sets_won.home }}:{{ state.sets_won.away }}
        (<span v-for="(s, i) in state.set_scores" :key="s.number"
          >{{ i > 0 ? ", " : "" }}{{ s.home }}:{{ s.away }}</span
        >)
      </p>
      <button class="secondary" @click="undo">↩ Letzte Aktion zurücknehmen</button>
    </div>
  </div>
</template>
