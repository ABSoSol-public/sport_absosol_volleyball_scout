<script setup>
import { computed, ref } from "vue";
import { rotate90 } from "../lib/court-grid.js";

const props = defineProps({
  homeLabel: { type: String, default: "Heim" },
  awayLabel: { type: String, default: "Gast" },
  // "90°"/"Seitenwechsel" werden vom Elternteil gesteuert (gemeinsam mit dem
  // Rotations-Helfer, Nutzerwunsch: „Buttons müssen für beide Grafiken gelten").
  vertical: { type: Boolean, default: false },
  swapped: { type: Boolean, default: false },
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
// Start- und Zielzone bleiben beide markiert, bis eine neue Aktion beginnt —
// der zweite Klick darf die Startzonen-Markierung nicht verändern/löschen.
const startSelection = ref(null);
const endSelection = ref(null);

// Pfeil Start→Ziel: Position wird direkt beim Klick aus der tatsächlich
// gerenderten Zellen-/Container-Geometrie gemessen (Prozent relativ zum
// Feld), statt aus dem Zonenraster zu rechnen — funktioniert dadurch
// unabhängig von der Netzleisten-Höhe (fix in rem) vs. den quadratischen,
// mitskalierenden Feldhälften.
const courtRef = ref(null);
const startPoint = ref(null);
const endPoint = ref(null);

function pointFromEvent(event) {
  const courtRect = courtRef.value.getBoundingClientRect();
  const cellRect = event.currentTarget.getBoundingClientRect();
  const x = cellRect.left + cellRect.width / 2 - courtRect.left;
  const y = cellRect.top + cellRect.height / 2 - courtRect.top;
  return { x: (x / courtRect.width) * 100, y: (y / courtRect.height) * 100 };
}

function select(cell, event) {
  const target = nextTarget.value;
  const point = pointFromEvent(event);
  if (target === "start") {
    startSelection.value = { zone: cell.zone, subzone: cell.subzone };
    startPoint.value = point;
    endSelection.value = null; // neue Aktion beginnt, altes Ziel verwerfen
    endPoint.value = null;
  } else {
    endSelection.value = { zone: cell.zone, subzone: cell.subzone };
    endPoint.value = point;
  }
  emit("select", { zone: cell.zone, subzone: cell.subzone, target });
  nextTarget.value = target === "start" ? "end" : "start";
}

function isSelected(cell, selection) {
  return selection && selection.zone === cell.zone && selection.subzone === cell.subzone;
}

// "90°": dieselbe Umschaltung horizontal/vertikal wie beim Rotations-Helfer
// (RotationCourt.vue) — Netz läuft waagerecht bzw. senkrecht. Das 6x6-Raster
// bleibt quadratisch in beiden Fällen, nur um 90° gedreht (`rotate90()`,
// court-grid.js); eine Randlinie, die horizontal unten lag (border-bottom),
// liegt nach der Drehung an derselben Zelle rechts (border-right) und
// umgekehrt (Spaltenreihenfolge bleibt unberührt, siehe rotate90()-Doku).
const activeGrid = computed(() => (props.vertical ? rotate90(cells.value) : cells.value));

const STRONG_LINE = "2px solid #fff";
const WEAK_LINE = "1px dashed rgba(255, 255, 255, 0.45)";
const WEAK_LINE_COL = "1px dashed rgba(255, 255, 255, 0.3)";

// Beim Transponieren tauschen Zeilen- und Spaltengrenzen die Seite: attackLine
// und zoneLine waren horizontale Grenzen zwischen Zonen-Zeilen (border-bottom) und
// werden nach dem Transponieren zu vertikalen Grenzen zwischen Zonen-Spalten
// (border-right) — und umgekehrt für colLine. Empirisch anhand der
// transponierten Zellindizes durchgerechnet (siehe PROGRESS.md), nicht geraten.
function cellLineStyle(cell) {
  if (props.vertical) {
    return {
      borderRight: cell.attackLine ? STRONG_LINE : cell.zoneLine ? WEAK_LINE : undefined,
      borderBottom: cell.colLine ? WEAK_LINE_COL : undefined,
    };
  }
  return {
    borderBottom: cell.attackLine ? STRONG_LINE : cell.zoneLine ? WEAK_LINE : undefined,
    borderRight: cell.colLine ? WEAK_LINE_COL : undefined,
  };
}
</script>

<template>
  <div class="volleyball-court" :style="{ width: vertical ? '34rem' : '18rem' }">
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

    <!-- Die Zellliste ist teamunabhängig (Zonen sind symmetrisch) — "away"/"home"
         in den Klassen unten bezeichnen nur die physische Position (oben/unten
         bzw. links/rechts je Ausrichtung, für die 180°-Drehung), nicht welches
         Team dort angezeigt wird. Bei "Seitenwechsel" (swapped) tauschen nur
         die Team-Label-Texte, nicht die Zellen/Klassen. -->
    <div ref="courtRef" class="full-court" :class="{ vertical }">
      <svg
        v-if="startPoint && endPoint"
        class="arrow-overlay"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
      >
        <defs>
          <marker
            id="zone-arrowhead"
            markerWidth="8"
            markerHeight="8"
            refX="4"
            refY="4"
            orient="auto-start-reverse"
            markerUnits="userSpaceOnUse"
          >
            <path d="M0,0 L8,4 L0,8 Z" fill="#1c2733" />
          </marker>
        </defs>
        <line
          :x1="startPoint.x"
          :y1="startPoint.y"
          :x2="endPoint.x"
          :y2="endPoint.y"
          stroke="#1c2733"
          stroke-width="1.6"
          marker-end="url(#zone-arrowhead)"
        />
      </svg>
      <div class="court-half-wrap">
        <div class="team-label">{{ swapped ? homeLabel : awayLabel }}</div>
        <div class="court-half away">
          <template v-for="(row, r) in activeGrid" :key="r">
            <button
              v-for="(cell, c) in row"
              :key="c"
              type="button"
              class="court-cell"
              :style="cellLineStyle(cell)"
              :class="{
                'selected-start': isSelected(cell, startSelection),
                'selected-end': isSelected(cell, endSelection),
              }"
              @click="select(cell, $event)"
            >
              <span class="cell-label rotated">
                <strong>{{ cell.zone }}</strong><small>{{ cell.subzone }}</small>
              </span>
            </button>
          </template>
        </div>
      </div>

      <div class="net-bar" :class="{ vertical }">NETZ</div>

      <div class="court-half-wrap">
        <div class="court-half home">
          <template v-for="(row, r) in activeGrid" :key="r">
            <button
              v-for="(cell, c) in row"
              :key="c"
              type="button"
              class="court-cell"
              :style="cellLineStyle(cell)"
              :class="{
                'selected-start': isSelected(cell, startSelection),
                'selected-end': isSelected(cell, endSelection),
              }"
              @click="select(cell, $event)"
            >
              <span class="cell-label">
                <strong>{{ cell.zone }}</strong><small>{{ cell.subzone }}</small>
              </span>
            </button>
          </template>
        </div>
        <div class="team-label">{{ swapped ? awayLabel : homeLabel }}</div>
      </div>
    </div>

    <p v-if="startSelection || endSelection" class="court-selection">
      <span v-if="startSelection">Start: Zone {{ startSelection.zone }}</span>
      <span v-if="endSelection">
        · Ziel: Zone {{ endSelection.zone }}{{ endSelection.subzone }}
      </span>
      <span class="muted"> — nächster Klick: {{ nextTarget === "start" ? "Startzone" : "Zielzone" }}</span>
    </p>
  </div>
</template>

<style scoped>
.volleyball-court {
  margin: 0 auto;
  max-width: 100%;
  transition: width 0.2s ease;
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
  position: relative;
  display: flex;
  flex-direction: column;
  border: 3px solid #fff;
  outline: 1px solid #c7cdd3;
  border-radius: 4px;
  overflow: hidden;
  background: #d98e4a;
}

.full-court.vertical {
  flex-direction: row;
}

.court-half-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.full-court.vertical .court-half-wrap {
  flex-direction: row;
}

.arrow-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.court-half {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  grid-template-rows: repeat(6, 1fr);
  aspect-ratio: 1;
}

/* Siehe RotationCourt.vue: im vertikalen Modus liegt der Team-Wrap in einer
   Reihe, das Feld bräuchte ohne flex-Wachstum nur seine Inhaltsgröße — das
   ließ die Zellen beim Drehen sichtbar schrumpfen. flex:1 lässt das Feld auf
   dieselbe Größe wachsen wie im horizontalen Modus. */
.full-court.vertical .court-half {
  flex: 1;
  min-width: 0;
}

/* Gastfeld = dieselbe Zellliste, aber 180° gedreht (siehe Skript-Kommentar
   oben) — Zellen UND Beschriftung drehen sich mit, die Beschriftung wird pro
   Zelle wieder zurückgedreht, damit der Text aufrecht bleibt. Gilt unabhängig
   von der 90°-Ausrichtung (horizontal/vertikal). */
.court-half.away {
  transform: rotate(180deg);
}

.net-bar {
  flex-shrink: 0;
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

.net-bar.vertical {
  height: auto;
  width: 1.5rem;
  border-top: none;
  border-bottom: none;
  border-left: 2px solid #fff;
  border-right: 2px solid #fff;
  writing-mode: vertical-rl;
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

.court-cell.selected-start {
  background: #33475b;
}

.court-cell.selected-start .cell-label {
  color: #fff;
}

.court-cell.selected-end {
  background: #b3202c;
}

.court-cell.selected-end .cell-label {
  color: #fff;
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
