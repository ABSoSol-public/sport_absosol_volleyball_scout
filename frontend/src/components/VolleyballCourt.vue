<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  label: { type: String, default: "" },
});
const emit = defineEmits(["select"]);

// Kanonisches Zonenraster (Draufsicht auf die EIGENE Feldhälfte, 9x9 m,
// Netz oben): Netzreihe 4-3-2, Mittelreihe 7-8-9, Grundlinie 5-6-1 — verifiziert
// gegen docs/DVW-FORMAT.md/PROGRESS.md UND das openvolley/datavolley-R-Paket
// (R/plot.R: dv_xy() Zonen-Koordinatentabelle). Jede Zone ist in 4 Subzonen
// A-D unterteilt; Eck-Zuordnung ebenfalls aus derselben Quelle (dv_xy()
// Subzonen-Offsets): A=unten-rechts, B=oben-rechts, C=oben-links, D=unten-links
// (im Uhrzeigersinn ab unten-rechts). Die Rotation um 180° (Button unten)
// ergibt exakt das Zonenraster der gegnerischen Feldhälfte, da die Zonen dort
// laut Quelle punktgespiegelt sind — deshalb reicht ein einziges Raster,
// per CSS-Transform gedreht, statt zweier separater Tabellen.
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
            rowBoundary: subRowIdx === 1 && zoneRowIdx < ZONE_ROWS.length - 1,
            colBoundary: subColIdx === 1 && zoneColIdx < zoneRow.length - 1,
          });
        });
      });
      result.push(row);
    });
  });
  return result;
});

const rotated = ref(false);
const selected = ref(null);

function select(cell) {
  selected.value = { zone: cell.zone, subzone: cell.subzone };
  emit("select", { ...selected.value });
}
</script>

<template>
  <div class="volleyball-court">
    <div class="court-toolbar">
      <span v-if="label" class="court-label">{{ label }}</span>
      <button type="button" class="secondary" @click="rotated = !rotated">⟲ Drehen</button>
    </div>
    <div class="court-grid" :class="{ rotated }">
      <template v-for="(row, r) in cells" :key="r">
        <button
          v-for="(cell, c) in row"
          :key="c"
          type="button"
          class="court-cell"
          :class="{
            'zone-border-bottom': cell.rowBoundary,
            'zone-border-right': cell.colBoundary,
            selected: selected && selected.zone === cell.zone && selected.subzone === cell.subzone,
          }"
          @click="select(cell)"
        >
          <span class="cell-label" :class="{ rotated }">
            <strong>{{ cell.zone }}</strong
            ><small>{{ cell.subzone }}</small>
          </span>
        </button>
      </template>
    </div>
    <p class="court-net-hint">↑ Netzseite</p>
    <p v-if="selected" class="court-selection">
      Gewählt: Zone {{ selected.zone }}{{ selected.subzone }}
    </p>
  </div>
</template>

<style scoped>
.volleyball-court {
  max-width: 20rem;
  margin: 0 auto;
}

.court-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.court-label {
  font-weight: 600;
}

.court-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  grid-template-rows: repeat(6, 1fr);
  aspect-ratio: 1;
  border: 2px solid #33475b;
  border-radius: 6px;
  overflow: hidden;
  transition: transform 0.4s ease;
}

.court-grid.rotated {
  transform: rotate(180deg);
}

.court-cell {
  background: #f7e6c4;
  border: 1px solid #e0c890;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: background-color 0.12s ease;
}

.court-cell:hover {
  background: #f0d9a8;
}

.court-cell.selected {
  background: #b3202c;
  border-color: #931a24;
}

.court-cell.selected .cell-label {
  color: #fff;
}

.court-cell.zone-border-right {
  border-right: 2px solid #33475b;
}

.court-cell.zone-border-bottom {
  border-bottom: 2px solid #33475b;
}

.cell-label {
  display: flex;
  align-items: baseline;
  gap: 0.1rem;
  color: #33475b;
  transition: transform 0.4s ease;
}

.cell-label.rotated {
  transform: rotate(180deg);
}

.cell-label strong {
  font-size: 1.1rem;
}

.cell-label small {
  font-size: 0.7rem;
  opacity: 0.8;
}

.court-net-hint {
  text-align: center;
  font-size: 0.75rem;
  color: #5b6b7b;
  margin: 0.3rem 0 0;
}

.court-selection {
  text-align: center;
  font-weight: 600;
  margin: 0.3rem 0 0;
}
</style>
