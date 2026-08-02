<script setup>
import { computed, ref } from "vue";

// Click-path alternative to typing the scout main code by hand (Roadmap 2.5):
// Team -> Player -> Skill -> Type (optional) -> Evaluation, each step locked
// until the previous one has a valid selection. Emits the finished main-code
// chunk (e.g. "a14AH+") so the parent can append it to the same free-text
// buffer the zone helper already writes into — zone/subzone digits typed or
// clicked afterwards attach directly to this chunk, no separator needed.
const props = defineProps({
  homeLabel: { type: String, default: "Heim" },
  awayLabel: { type: String, default: "Gast" },
  homePlayers: { type: Array, default: () => [] },
  awayPlayers: { type: Array, default: () => [] },
});
const emit = defineEmits(["append"]);

// Matches backend/app/engine/scout_code.py exactly (SKILLS/HIT_TYPES/EVALUATIONS).
const SKILLS = [
  { code: "S", label: "Aufschlag" },
  { code: "R", label: "Annahme" },
  { code: "A", label: "Angriff" },
  { code: "B", label: "Block" },
  { code: "D", label: "Abwehr" },
  { code: "E", label: "Zuspiel" },
  { code: "F", label: "Freeball" },
];
const HIT_TYPES = ["H", "M", "Q", "T", "U", "N", "O"];
const EVALUATIONS = ["#", "+", "!", "-", "/", "="];

const side = ref(null); // "home" | "away"
const playerNumber = ref(null);
const skill = ref(null);
const hitType = ref(null);

const players = computed(() => (side.value === "home" ? props.homePlayers : props.awayPlayers));
const skillLabel = computed(() => SKILLS.find((s) => s.code === skill.value)?.label ?? null);

const previewCode = computed(() => {
  if (!side.value || !playerNumber.value) return "";
  const prefix = side.value === "away" ? "a" : "";
  return `${prefix}${playerNumber.value}${skill.value ?? ""}${hitType.value ?? ""}`;
});

function selectSide(value) {
  side.value = value;
  playerNumber.value = null;
  skill.value = null;
  hitType.value = null;
}

function selectPlayer(number) {
  playerNumber.value = number;
  skill.value = null;
  hitType.value = null;
}

function selectSkill(code) {
  skill.value = code;
  hitType.value = null;
}

function selectHitType(code) {
  hitType.value = hitType.value === code ? null : code;
}

function finish(evaluation) {
  const prefix = side.value === "away" ? "a" : "";
  const code = `${prefix}${playerNumber.value}${skill.value}${hitType.value ?? ""}${evaluation ?? ""}`;
  emit("append", code);
  reset();
}

function reset() {
  side.value = null;
  playerNumber.value = null;
  skill.value = null;
  hitType.value = null;
}

defineExpose({ reset });
</script>

<template>
  <div class="clickpath">
    <div class="clickpath-row">
      <span class="clickpath-label">Team</span>
      <button
        type="button"
        :class="{ secondary: side !== 'home' }"
        @click="selectSide('home')"
      >
        {{ homeLabel }}
      </button>
      <button
        type="button"
        :class="{ secondary: side !== 'away' }"
        @click="selectSide('away')"
      >
        {{ awayLabel }}
      </button>
    </div>

    <div class="clickpath-row">
      <span class="clickpath-label">Spieler</span>
      <button
        v-for="p in players"
        :key="p.number"
        type="button"
        :disabled="!side"
        :class="{ secondary: playerNumber !== p.number }"
        @click="selectPlayer(p.number)"
      >
        {{ p.number }}{{ p.is_libero ? " (L)" : "" }}
      </button>
      <span v-if="side && players.length === 0" class="muted">Keine Aufstellung.</span>
    </div>

    <div class="clickpath-row">
      <span class="clickpath-label">Aktion</span>
      <button
        v-for="s in SKILLS"
        :key="s.code"
        type="button"
        :disabled="!playerNumber"
        :class="{ secondary: skill !== s.code }"
        @click="selectSkill(s.code)"
      >
        {{ s.label }}
      </button>
    </div>

    <div class="clickpath-row">
      <span class="clickpath-label">Typ (optional)</span>
      <button
        v-for="t in HIT_TYPES"
        :key="t"
        type="button"
        :disabled="!skill"
        :class="{ secondary: hitType !== t }"
        @click="selectHitType(t)"
      >
        {{ t }}
      </button>
    </div>

    <div class="clickpath-row">
      <span class="clickpath-label">Wertung</span>
      <button
        v-for="e in EVALUATIONS"
        :key="e"
        type="button"
        :disabled="!skill"
        @click="finish(e)"
      >
        {{ e }}
      </button>
      <button type="button" class="secondary" :disabled="!skill" @click="finish(null)">
        ohne Wertung
      </button>
    </div>

    <div class="clickpath-footer">
      <span class="clickpath-preview">
        Code: <code>{{ previewCode || "–" }}</code>
        <template v-if="skillLabel">&nbsp;({{ skillLabel }})</template>
      </span>
      <button type="button" class="secondary" @click="reset">Zurücksetzen</button>
    </div>
  </div>
</template>
