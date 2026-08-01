<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { api } from "../api";
import VolleyballCourt from "../components/VolleyballCourt.vue";
import RotationCourt from "../components/RotationCourt.vue";

const props = defineProps({ id: { type: String, required: true } });

const match = ref(null);
const state = ref(null);
const error = ref("");
const roster = ref({ home: [], away: [] });

// Aufstellungs-Eingabe je Zone (statt Freitext-Nummernliste): Nutzer wählt pro
// Zone einen Spieler aus dem hinterlegten Kader, ähnlich der "Classic Mode"-
// Nummernmaske in DataVolley (Zonen-Boxen), aber kaderbasiert statt Blindeingabe.
function blankLineup() {
  return { 1: null, 2: null, 3: null, 4: null, 5: null, 6: null };
}
const lineupInput = ref({ serving: "home" });
const lineupSelection = ref({ home: blankLineup(), away: blankLineup() });

const actionCodes = ref("");
const sub = ref({ side: "home", player_out: null, player_in: null });

// "90°" (Netzausrichtung) und "Seitenwechsel" (welches Team wo angezeigt wird)
// gelten für Rotations- und Zonen-Helfer gemeinsam (Nutzerfeedback: „die
// Buttons drehen und Seitenwechsel müssen immer für beide Grafiken gelten") —
// daher hier zentral statt je Komponente einzeln gehalten.
const helperVertical = ref(false);
const helperSwapped = ref(false);

// VolleyballCourt entscheidet selbst (auto-fortschreitend), ob ein Klick gerade
// Start- oder Zielzone meint, und liefert das per `target` mit.
function appendZone(selection) {
  actionCodes.value +=
    selection.target === "end" ? selection.zone + selection.subzone : selection.zone;
}

const setRunning = computed(() => state.value?.set_running);
const current = computed(() => state.value?.current_set);

// Anzeige-Reihenfolge des Courts: vorne Zonen 4-3-2, hinten 5-6-1.
// Engine-Lineup ist [Zone1, Zone2, ..., Zone6] → Index = Zone - 1.
const ZONE_ORDER = [4, 3, 2, 5, 6, 1];

const correctLineup = ({ side, lineup }) =>
  run(() => api.correctLineup(props.id, { side, lineup }));

function duplicateNumbers(side) {
  const values = Object.values(lineupSelection.value[side]).filter((v) => v !== null);
  return values.length !== new Set(values).size;
}

// Spieler, die aktuell laut Aufstellung auf dem Feld stehen (für die
// Wechsel-Auswahl "raus"), bzw. Kadermitglieder, die es nicht sind ("rein").
function onCourt(side) {
  const numbers = current.value?.lineups?.[side] ?? [];
  return roster.value[side].filter((p) => numbers.includes(p.number));
}

function onBench(side) {
  const numbers = current.value?.lineups?.[side] ?? [];
  return roster.value[side].filter((p) => !numbers.includes(p.number));
}

// Letzte bekannte Aufstellung je Team (inkl. während des Satzes gemachter
// Wechsel) — kommt aus dem zuletzt gespielten Satz in `set_scores`, nicht nur
// aus der laufenden Session, damit der Vorschlag auch nach einem Reload/
// Wiederöffnen (z. B. in der Satzpause) funktioniert.
const lastLineups = computed(() => {
  const scores = state.value?.set_scores ?? [];
  return scores.length ? scores[scores.length - 1].lineups : null;
});

function prefillLineupIfEmpty() {
  if (!lastLineups.value) return;
  for (const side of ["home", "away"]) {
    const alreadyChosen = Object.values(lineupSelection.value[side]).some((v) => v !== null);
    if (alreadyChosen) continue;
    const selection = blankLineup();
    lastLineups.value[side].forEach((number, index) => {
      selection[index + 1] = number;
    });
    lineupSelection.value[side] = selection;
  }
}

// Direkt nach dem Laden (auch bei Reload zwischen den Sätzen) sowie beim
// Übergang "Satz läuft" → "kein Satz läuft" die zuletzt bekannte Aufstellung
// als Vorschlag übernehmen (nur solange der Nutzer noch nichts gewählt hat).
watch(
  setRunning,
  (running) => {
    if (!running) prefillLineupIfEmpty();
  },
  { immediate: true }
);

async function loadRoster() {
  const [home, away] = await Promise.all([
    api.getTeam(match.value.home_team.id),
    api.getTeam(match.value.away_team.id),
  ]);
  roster.value = { home: home.players, away: away.players };
}

async function refresh() {
  [match.value, state.value] = await Promise.all([
    api.getMatch(props.id),
    api.liveState(props.id),
  ]);
  await loadRoster();
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

const startSet = () =>
  run(() =>
    api.startSet(props.id, {
      serving: lineupInput.value.serving,
      home_lineup: [1, 2, 3, 4, 5, 6].map((zone) => lineupSelection.value.home[zone]),
      away_lineup: [1, 2, 3, 4, 5, 6].map((zone) => lineupSelection.value.away[zone]),
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

    <!-- Haupteingabepunkt: bleibt beim Scrollen sichtbar, statt mit den
         Feld-Helfern weiter unten mitzuscrollen. -->
    <div v-if="setRunning" class="scout-code-anchor">
      <div class="field">
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
      <div style="display: flex; gap: 2rem; justify-content: center; flex-wrap: wrap">
        <div v-for="side in ['home', 'away']" :key="side">
          <h3 style="text-align: center">{{ match[`${side}_team`].name }}</h3>
          <p v-if="roster[side].length === 0" class="error" style="max-width: 16rem">
            Kader ist leer — zuerst unter „Teams" Spieler anlegen.
          </p>
          <div v-else class="court court-wide">
            <div v-for="zone in ZONE_ORDER" :key="zone" class="zone">
              <select v-model.number="lineupSelection[side][zone]" style="width: 100%">
                <option :value="null">–</option>
                <option v-for="p in roster[side]" :key="p.id" :value="p.number">
                  {{ p.number }} · {{ p.last_name }}{{ p.is_libero ? " (L)" : "" }}
                </option>
              </select>
              <small>Zone {{ zone }}</small>
            </div>
          </div>
          <p v-if="duplicateNumbers(side)" class="error" style="text-align: center">
            Ein Spieler ist mehrfach zugeordnet.
          </p>
        </div>
      </div>
      <button style="margin-top: 1rem" @click="startSet">Satz starten</button>
    </div>

    <!-- Laufender Satz -->
    <div v-if="setRunning" class="card">
      <div class="helper-shared-toolbar">
        <button type="button" class="secondary" @click="helperVertical = !helperVertical">
          ⟳ 90° drehen
        </button>
        <button type="button" class="secondary" @click="helperSwapped = !helperSwapped">
          ⇄ Seitenwechsel
        </button>
      </div>
      <div class="field-helpers">
        <div class="field-helper">
          <h3 class="field-helper-title">Rotation</h3>
          <RotationCourt
            :vertical="helperVertical"
            :swapped="helperSwapped"
            :home-lineup="current.lineups.home"
            :away-lineup="current.lineups.away"
            :home-roster="roster.home"
            :away-roster="roster.away"
            :home-label="match.home_team.code"
            :away-label="match.away_team.code"
            :serving="current.serving"
            @save-lineup="correctLineup"
          />
        </div>
        <div class="field-helper">
          <h3 class="field-helper-title">Zonen & Richtung</h3>
          <VolleyballCourt
            :vertical="helperVertical"
            :swapped="helperSwapped"
            :home-label="match.home_team.code"
            :away-label="match.away_team.code"
            @select="appendZone"
          />
          <p class="muted court-selection-hint" style="text-align: center">
            Erster Klick = Startzone, zweiter Klick = Zielzone + Subzone (Richtung) —
            rückt automatisch weiter, bei Bedarf oben manuell umschaltbar.
          </p>
        </div>
      </div>

      <div style="display: flex; gap: 2rem; justify-content: center; flex-wrap: wrap; margin-top: 0.6rem">
        <div>Auszeiten {{ match.home_team.code }}: {{ current.timeouts.home }} · Wechsel: {{ current.substitutions.home }}</div>
        <div>Auszeiten {{ match.away_team.code }}: {{ current.timeouts.away }} · Wechsel: {{ current.substitutions.away }}</div>
      </div>

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
          <select id="sub-out" v-model.number="sub.player_out">
            <option :value="null">–</option>
            <option v-for="p in onCourt(sub.side)" :key="p.id" :value="p.number">
              {{ p.number }} · {{ p.last_name }}{{ p.is_libero ? " (L)" : "" }}
            </option>
          </select>
        </div>
        <div class="field">
          <label for="sub-in">Rein</label>
          <select id="sub-in" v-model.number="sub.player_in">
            <option :value="null">–</option>
            <option v-for="p in onBench(sub.side)" :key="p.id" :value="p.number">
              {{ p.number }} · {{ p.last_name }}{{ p.is_libero ? " (L)" : "" }}
            </option>
          </select>
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
