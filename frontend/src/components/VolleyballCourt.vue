<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  homeLabel: { type: String, default: "Heim" },
  awayLabel: { type: String, default: "Gast" },
});
const emit = defineEmits(["select"]);

// Kanonisches Zonenraster (Draufsicht auf die EIGENE/Heim-Feldhälfte, 9x9 m,
// Netz oben): Netzreihe 4-3-2, Mittelreihe 7-8-9, Grundlinie 5-6-1 — verifiziert
// gegen docs/DVW-FORMAT.md/PROGRESS.md UND das openvolley/datavolley-R-Paket
// (R/plot.R: dv_xy() Zonen-Koordinatentabelle). Jede Zone ist in 4 Subzonen
// A-D unterteilt; Eck-Zuordnung ebenfalls aus derselben Quelle (dv_xy()
// Subzonen-Offsets): A=unten-rechts, B=oben-rechts, C=oben-links, D=unten-links
// (im Uhrzeigersinn ab unten-rechts). Für die Gastseite reicht dieselbe
// Zellliste, per CSS 180°-Transform gedreht — die Gegenfeld-Zonen sind laut
// Quelle exakt punktgespiegelt, keine zweite Tabelle nötig.
const ZONE_ROWS = [
  [4, 3, 2],
  [7, 8, 9],
  [5, 6, 1],
];

// Pro Zonen-Zelle die 2x2-Subzonen, zeilenweise oben->unten, links->rechts.
const SUBZONE_QUADRANTS = [
  ["C", "B"],
  ["D", "A"],
];

const cells = computed(() => {
  const result = [];
  ZONE_ROWS.forEach((zoneRow, zoneRowIdx) => {
    SUBZONE_QUADRANTS.forEach((subRow, subRowIdx) => {
      const row = [];
      zoneRow.forEach((zone, zoneColIdx) => {
        subRow.forEach((subzone, subColIdx) => {
          row.push({
            zone,
            subzone,
            // Nur die Grenze zwischen Netzreihe und Mittelreihe entspricht einer
            // echten Feldlinie (3-Meter-/Angriffslinie); die übrigen Zonen-
            // grenzen sind reine Auswertungs-Hilfslinien, dezent dargestellt.
            attackLine: subRowIdx === 1 && zoneRowIdx === 0,
            zoneLine: subRowIdx === 1 && zoneRowIdx === 1,
            colLine: subColIdx === 1 && zoneColIdx < zoneRow.length - 1,
          });
        });
      });
      result.push(row);
    });
  });
  return result;
});

// Start/Ziel rückt nach jedem Klick automatisch weiter (erster Klick = Start,
// zweiter = Ziel+Subzone) — im Live-Betrieb reicht das für den Normalfall ohne
// weiteren Klick auf einen Umschalter. Für Sonderfälle (z. B. Block ohne
// Startzone) lässt sich der Modus manuell überschreiben.
const nextTarget = ref("start"); // "start" | "end"
const selected = ref(null);

function select(cell) {
  selected.value = { zone: cell.zone, subzone: cell.subzone, target: nextTarget.value };
  emit("select", { zone: cell.zone, subzone: cell.subzone, target: nextTarget.value });
  nextTarget.value = nextTarget.value === "start" ? "end" : "start";
}
</script>

<template>
  <div class="volleyball-court">
    <div class="target-toggle">
      <button
        type="button"
        :class="nextTarget === 'start' ? '' : 'secondary'"
        @click="nextTarget = 'start'"
      >
        Startzone
      </button>
      <button
        type="button"
        :class="nextTarget === 'end' ? '' : 'secondary'"
        @click="nextTarget = 'end'"
      >
        Zielzone (+ Richtung)
      </button>
    </div>

    <div class="full-court">
      <div class="team-label">{{ awayLabel }}</div>
      <div class="court-half away">
        <template v-for="(row, r) in cells" :key="r">
          <button
            v-for="(cell, c) in row"
            :key="c"
            type="button"
            class="court-cell"
            :class="{
              'attack-line': cell.attackLine,
              'zone-line': cell.zoneLine,
              'col-line': cell.colLine,
              selected: selected && selected.zone === cell.zone && selected.subzone === cell.subzone,
            }"
            @click="select(cell)"
          >
            <span class="cell-label rotated">
              <strong>{{ cell.zone }}</strong><small>{{ cell.subzone }}</small>
            </span>
          </button>
        </template>
      </div>

      <div class="net-bar">NETZ</div>

      <div class="court-half home">
        <template v-for="(row, r) in cells" :key="r">
          <button
            v-for="(cell, c) in row"
            :key="c"
            type="button"
            class="court-cell"
            :class="{
              'attack-line': cell.attackLine,
              'zone-line': cell.zoneLine,
              'col-line': cell.colLine,
              selected: selected && selected.zone === cell.zone && selected.subzone === cell.subzone,
            }"
            @click="select(cell)"
          >
            <span class="cell-label">
              <strong>{{ cell.zone }}</strong><small>{{ cell.subzone }}</small>
            </span>
          </button>
        </template>
      </div>
      <div class="team-label">{{ homeLabel }}</div>
    </div>

    <p v-if="selected" class="court-selection">
      Gewählt: Zone {{ selected.zone }}{{ selected.subzone }}
      ({{ selected.target === "start" ? "Start" : "Ziel" }}) — nächster Klick:
      {{ nextTarget === "start" ? "Startzone" : "Zielzone" }}
    </p>
  </div>
</template>

<style scoped>
.volleyball-court {
  max-width: 18rem;
  margin: 0 auto;
}

.target-toggle {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  margin-bottom: 0.6rem;
}

.team-label {
  text-align: center;
  font-weight: 600;
  font-size: 0.85rem;
  padding: 0.2rem 0;
  color: #33475b;
}

.full-court {
  border: 3px solid #fff;
  outline: 1px solid #c7cdd3;
  border-radius: 4px;
  overflow: hidden;
  background: #d98e4a;
}

.court-half {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  grid-template-rows: repeat(6, 1fr);
  aspect-ratio: 1;
}

/* Gastfeld = dieselbe Zellliste, aber 180° gedreht (siehe Skript-Kommentar
   oben) — Zellen UND Beschriftung drehen sich mit, die Beschriftung wird pro
   Zelle wieder zurückgedreht, damit der Text aufrecht bleibt. */
.court-half.away {
  transform: rotate(180deg);
}

.net-bar {
  height: 1.5rem;
  background: #1c2733;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  border-top: 2px solid #fff;
  border-bottom: 2px solid #fff;
}

.court-cell {
  background: transparent;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: background-color 0.12s ease;
}

.court-cell:hover {
  background: rgba(255, 255, 255, 0.25);
}

.court-cell.selected {
  background: #b3202c;
}

.court-cell.selected .cell-label {
  color: #fff;
}

/* Echte Feldlinie: 3-Meter-/Angriffslinie zwischen Netz- und Mittelreihe */
.court-cell.attack-line {
  border-bottom: 2px solid #fff;
}

/* Reine Auswertungs-Hilfslinien (keine echten Feldlinien), dezent */
.court-cell.zone-line {
  border-bottom: 1px dashed rgba(255, 255, 255, 0.45);
}

.court-cell.col-line {
  border-right: 1px dashed rgba(255, 255, 255, 0.3);
}

.cell-label {
  display: flex;
  align-items: baseline;
  gap: 0.1rem;
  color: rgba(28, 39, 51, 0.75);
}

.cell-label.rotated {
  transform: rotate(180deg);
}

.cell-label strong {
  font-size: 1rem;
}

.cell-label small {
  font-size: 0.65rem;
  opacity: 0.8;
}

.court-selection {
  text-align: center;
  font-weight: 600;
  margin: 0.5rem 0 0;
  font-size: 0.9rem;
}
</style>
