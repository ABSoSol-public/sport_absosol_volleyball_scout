<script setup>
import { computed, ref } from "vue";
import { transpose } from "../lib/court-grid.js";

const props = defineProps({
  homeLineup: { type: Array, default: () => [] }, // [Zone1..Zone6]
  awayLineup: { type: Array, default: () => [] },
  homeRoster: { type: Array, default: () => [] },
  awayRoster: { type: Array, default: () => [] },
  homeLabel: { type: String, default: "Heim" },
  awayLabel: { type: String, default: "Gast" },
  serving: { type: String, default: null }, // "home" | "away" | null
});
const emit = defineEmits(["save-lineup"]);

// Standard-6-Zonen-Rotationsraster (Netzreihe 4-3-2 im vorderen 3-m-Band,
// Grundlinie 5-6-1 im hinteren 6-m-Band — Netzreihe/Grundlinie daher bewusst
// 1:2 statt 1:1 in der Rasterhöhe, siehe Recherche/CSS). Vertikale Ausrichtung
// (Netz läuft senkrecht statt waagerecht) ist dieselbe Rotation um 90°, per
// Matrixformel abgeleitet (transpose + Spiegeln), nicht von Hand geraten.
const HORIZONTAL_ROWS = [
  [4, 3, 2],
  [5, 6, 1],
];
const VERTICAL_ROWS = transpose(HORIZONTAL_ROWS);

// "90°": DataVolleys eigener `ROT`-Befehl schaltet die Rotationsanzeige
// zwischen horizontal/vertikal um (kein freier Winkel) — siehe
// ../../../../recherche/Data_Volley_4_Funktionsanalyse.md Abschnitt 4.2.
const vertical = ref(false);
// "INV": welches Team auf welcher Seite angezeigt wird, unabhängig von der
// Ausrichtung — für den eigenen Sitzplatz/Seitenwechsel im echten Spiel.
const swapped = ref(false);

const editing = ref(false);
const editLineups = ref({ home: [], away: [] });

const rows = computed(() => (vertical.value ? VERTICAL_ROWS : HORIZONTAL_ROWS));
const gridStyle = computed(() =>
  vertical.value
    ? { gridTemplateColumns: "1fr 2fr", gridTemplateRows: `repeat(${rows.value.length}, 1fr)` }
    : { gridTemplateColumns: `repeat(${rows.value[0].length}, 1fr)`, gridTemplateRows: "1fr 2fr" }
);

function lineupFor(side) {
  return side === "home" ? props.homeLineup : props.awayLineup;
}

function rosterFor(side) {
  return side === "home" ? props.homeRoster : props.awayRoster;
}

function playerAt(side, zone) {
  const number = lineupFor(side)[zone - 1];
  const player = rosterFor(side).find((p) => p.number === number);
  return { number, isLibero: !!player?.is_libero };
}

function startEdit() {
  editLineups.value = { home: [...props.homeLineup], away: [...props.awayLineup] };
  editing.value = true;
}

function cancelEdit() {
  editing.value = false;
}

function duplicateNumbers(side) {
  const values = editLineups.value[side];
  return new Set(values).size !== values.length;
}

function save(side) {
  emit("save-lineup", { side, lineup: [...editLineups.value[side]] });
  editing.value = false;
}
</script>

<template>
  <div class="rotation-court" :style="{ width: vertical ? '38rem' : '20rem' }">
    <div class="rotation-toolbar">
      <button type="button" class="secondary" @click="vertical = !vertical">⟳ 90° drehen</button>
      <button type="button" class="secondary" @click="swapped = !swapped">⇄ Seitenwechsel</button>
      <button v-if="!editing" type="button" class="secondary" @click="startEdit">
        Aufstellung korrigieren
      </button>
      <button v-else type="button" class="secondary" @click="cancelEdit">Abbrechen</button>
    </div>

    <div class="rotation-full-court" :class="{ vertical }">
      <div class="rotation-half-wrap">
        <div class="team-label">
          <span
            v-if="serving === (swapped ? 'home' : 'away')"
            class="serve-dot"
            title="Aufschlag"
          ></span>
          {{ swapped ? homeLabel : awayLabel }}
        </div>
        <div class="rotation-half away" :style="gridStyle">
          <div v-for="(row, r) in rows" :key="r" class="rotation-row" :class="{ vertical }">
            <div v-for="zone in row" :key="zone" class="rotation-cell">
              <template v-if="editing">
                <select v-model.number="editLineups[swapped ? 'home' : 'away'][zone - 1]">
                  <option v-for="p in rosterFor(swapped ? 'home' : 'away')" :key="p.id" :value="p.number">
                    {{ p.number }}
                  </option>
                </select>
              </template>
              <template v-else>
                <strong>{{ playerAt(swapped ? "home" : "away", zone).number ?? "–" }}</strong>
                <small v-if="playerAt(swapped ? 'home' : 'away', zone).isLibero" class="libero-badge">L</small>
              </template>
              <small class="zone-tag">{{ zone }}</small>
            </div>
          </div>
        </div>
      </div>

      <div class="net-bar" :class="{ vertical }">NETZ</div>

      <div class="rotation-half-wrap">
        <div class="rotation-half home" :style="gridStyle">
          <div v-for="(row, r) in rows" :key="r" class="rotation-row" :class="{ vertical }">
            <div v-for="zone in row" :key="zone" class="rotation-cell">
              <template v-if="editing">
                <select v-model.number="editLineups[swapped ? 'away' : 'home'][zone - 1]">
                  <option v-for="p in rosterFor(swapped ? 'away' : 'home')" :key="p.id" :value="p.number">
                    {{ p.number }}
                  </option>
                </select>
              </template>
              <template v-else>
                <strong>{{ playerAt(swapped ? "away" : "home", zone).number ?? "–" }}</strong>
                <small v-if="playerAt(swapped ? 'away' : 'home', zone).isLibero" class="libero-badge">L</small>
              </template>
              <small class="zone-tag">{{ zone }}</small>
            </div>
          </div>
        </div>
        <div class="team-label">
          <span
            v-if="serving === (swapped ? 'away' : 'home')"
            class="serve-dot"
            title="Aufschlag"
          ></span>
          {{ swapped ? awayLabel : homeLabel }}
        </div>
      </div>
    </div>

    <div v-if="editing" class="edit-actions">
      <p v-if="duplicateNumbers(swapped ? 'away' : 'home') || duplicateNumbers(swapped ? 'home' : 'away')" class="error">
        Ein Spieler ist mehrfach zugeordnet.
      </p>
      <button @click="save('home')">{{ homeLabel }} speichern</button>
      <button @click="save('away')">{{ awayLabel }} speichern</button>
    </div>
  </div>
</template>

<style scoped>
.rotation-court {
  margin: 0 auto;
  max-width: 100%;
  transition: width 0.2s ease;
}

.rotation-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
  margin-bottom: 0.6rem;
}

.rotation-full-court {
  display: flex;
  flex-direction: column;
  border: 3px solid #fff;
  outline: 1px solid #c7cdd3;
  border-radius: 4px;
  overflow: hidden;
  background: #d98e4a;
}

.rotation-full-court.vertical {
  flex-direction: row;
}

.rotation-half-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.rotation-full-court.vertical .rotation-half-wrap {
  flex-direction: row;
}

.team-label {
  text-align: center;
  font-weight: 600;
  font-size: 0.85rem;
  padding: 0.3rem 0;
  color: #33475b;
  background: #f4f6f8;
}

.rotation-half {
  display: grid;
  gap: 2px;
  aspect-ratio: 1;
  padding: 4px;
}

/* Im vertikalen Modus liegt der Team-Wrap in einer Reihe (Team-Label + Feld
   nebeneinander) — ohne flex-Wachstum bliebe das Feld auf seine Inhaltsgröße
   beschränkt (viel kleiner als im horizontalen Modus, wo das Block-Element
   per Default-Stretch die volle Wrap-Breite bekommt). flex:1 gleicht das an,
   damit die Zellengröße unabhängig von der Ausrichtung gleich bleibt. */
.rotation-full-court.vertical .rotation-half {
  flex: 1;
  min-width: 0;
}

.rotation-half.away {
  transform: rotate(180deg);
}

.rotation-row {
  display: contents;
}

.rotation-cell {
  position: relative;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 2.4rem;
  color: #fff;
}

.rotation-half.away .rotation-cell {
  transform: rotate(180deg);
}

.rotation-cell strong {
  font-size: 1.1rem;
}

.rotation-cell select {
  width: 3.2rem;
  padding: 0.1rem;
  font-size: 0.9rem;
}

.rotation-cell .zone-tag {
  position: absolute;
  bottom: 1px;
  right: 3px;
  font-size: 0.55rem;
  opacity: 0.7;
}

.libero-badge {
  position: absolute;
  top: 1px;
  left: 3px;
  font-size: 0.6rem;
  font-weight: 700;
  background: #1c2733;
  color: #fff;
  border-radius: 3px;
  padding: 0 0.2rem;
}

.net-bar {
  flex-shrink: 0;
  height: 1.4rem;
  background: #1c2733;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  border-top: 2px solid #fff;
  border-bottom: 2px solid #fff;
}

.net-bar.vertical {
  height: auto;
  width: 1.4rem;
  border-top: none;
  border-bottom: none;
  border-left: 2px solid #fff;
  border-right: 2px solid #fff;
  writing-mode: vertical-rl;
}

.edit-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.6rem;
}
</style>
