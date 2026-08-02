<script setup>
import { computed, ref } from "vue";

// Click-path alternative to typing the scout main code by hand (Roadmap 2.5):
// Team -> Player -> Skill -> Type (optional) -> Evaluation, each step locked
// until the previous one has a valid selection. Emits the finished main-code
// chunk (e.g. "a14AH+") so the parent can append it to the same free-text
// buffer the zone helper already writes into — zone/subzone digits typed or
// clicked afterwards attach directly to this chunk, no separator needed.
//
// Serve (S) is special-cased into its own combination-code sub-flow, per
// domain rules from the user (2026-08-02):
// - Home actions always start with "*", away always with lowercase "a" (no
//   omitted prefix, unlike the lenient direct-entry parser which still
//   defaults a bare number to home).
// - A serve's own evaluation is *not* written directly — DataVolley encodes
//   the serve-reception pair as "<server>S<startZone><endZone>.<receiver>
//   <receptionEval>", where the trailing evaluation character rates the
//   RECEPTION (as actually observed), and the serve's own quality is only
//   implied by a fixed mapping: reception "=" (ace/no play) <-> serve "#";
//   reception "-" <-> serve "+"; reception "/" <-> serve "/"; reception "#"
//   or "+" <-> serve "-" (scout picks whichever matches the real reception).
//   A serve that never reaches the opponent (net/out) has no receiver at
//   all and is just "<server>S<startZone><endZone>=".
// - When unsure what really happened, "+" is always a safe default rating
//   (used as a generic placeholder) — so there's no separate "no rating"
//   button, "+" already covers that case.
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
const ZONES = [1, 2, 3, 4, 5, 6, 7, 8, 9];

// Reception evaluation the scout actually observed -> the serve rating it
// implies (never written into the code, shown only as a hint). "!" isn't
// part of this mapping (not used for serve/reception in the domain rules).
const RECEPTION_OPTIONS = [
  { code: "=", label: "Ass / kein Zugriff", servesAs: "#" },
  { code: "-", label: "schwache Annahme", servesAs: "+" },
  { code: "/", label: "unkontrolliert", servesAs: "/" },
  { code: "#", label: "perfekte Annahme", servesAs: "-" },
  { code: "+", label: "gute Annahme", servesAs: "-" },
];

const side = ref(null); // "home" | "away"
const playerNumber = ref(null);
const skill = ref(null);
const hitType = ref(null);
const startZone = ref(null);
const endZone = ref(null);
const receiverNumber = ref(null);

const players = computed(() => (side.value === "home" ? props.homePlayers : props.awayPlayers));
// The receiving side is always the opponent of the server.
const opponents = computed(() => (side.value === "home" ? props.awayPlayers : props.homePlayers));
const skillLabel = computed(() => SKILLS.find((s) => s.code === skill.value)?.label ?? null);
const isServe = computed(() => skill.value === "S");
const prefix = computed(() => (side.value === "away" ? "a" : "*"));

const previewCode = computed(() => {
  if (!side.value || !playerNumber.value) return "";
  if (isServe.value) {
    return `${prefix.value}${playerNumber.value}S${startZone.value ?? ""}${endZone.value ?? ""}`;
  }
  return `${prefix.value}${playerNumber.value}${skill.value ?? ""}${hitType.value ?? ""}`;
});

function resetDeeperThanSide() {
  playerNumber.value = null;
  resetDeeperThanPlayer();
}

function resetDeeperThanPlayer() {
  skill.value = null;
  resetDeeperThanSkill();
}

function resetDeeperThanSkill() {
  hitType.value = null;
  startZone.value = null;
  endZone.value = null;
  receiverNumber.value = null;
}

function selectSide(value) {
  side.value = value;
  resetDeeperThanSide();
}

function selectPlayer(number) {
  playerNumber.value = number;
  resetDeeperThanPlayer();
}

function selectSkill(code) {
  skill.value = code;
  resetDeeperThanSkill();
}

function selectHitType(code) {
  hitType.value = hitType.value === code ? null : code;
}

function selectZone(which, zone) {
  if (which === "start") {
    startZone.value = startZone.value === zone ? null : zone;
  } else {
    endZone.value = endZone.value === zone ? null : zone;
  }
}

function selectReceiver(number) {
  receiverNumber.value = receiverNumber.value === number ? null : number;
}

function finish(evaluation) {
  const code = `${prefix.value}${playerNumber.value}${skill.value}${hitType.value ?? ""}${evaluation ?? ""}`;
  emit("append", code);
  reset();
}

// Serve never reached the opponent (net or out) — no receiver combo needed,
// so this stays a plain main code (evaluation right after the skill letter,
// zones after that) and — unlike the reception combo below — parses cleanly
// with the existing strict grammar.
function finishServeFault() {
  const code = `${prefix.value}${playerNumber.value}S=${startZone.value ?? ""}${endZone.value ?? ""}`;
  emit("append", code);
  reset();
}

// Serve reached the opponent — reception combo with the observed reception
// evaluation (the serve's own rating is only implied, see header comment).
function finishServeReception(receptionEval) {
  const code = `${prefix.value}${playerNumber.value}S${startZone.value ?? ""}${endZone.value ?? ""}.${receiverNumber.value}${receptionEval}`;
  emit("append", code);
  reset();
}

function reset() {
  side.value = null;
  resetDeeperThanSide();
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

    <template v-if="isServe">
      <div class="clickpath-row">
        <span class="clickpath-label">Start-Zone</span>
        <button
          v-for="z in ZONES"
          :key="z"
          type="button"
          :class="{ secondary: startZone !== z }"
          @click="selectZone('start', z)"
        >
          {{ z }}
        </button>
      </div>

      <div class="clickpath-row">
        <span class="clickpath-label">Ziel-Zone</span>
        <button
          v-for="z in ZONES"
          :key="z"
          type="button"
          :class="{ secondary: endZone !== z }"
          @click="selectZone('end', z)"
        >
          {{ z }}
        </button>
      </div>

      <div class="clickpath-row">
        <span class="clickpath-label">Annahme-Spieler</span>
        <button
          v-for="p in opponents"
          :key="p.number"
          type="button"
          :class="{ secondary: receiverNumber !== p.number }"
          @click="selectReceiver(p.number)"
        >
          {{ p.number }}{{ p.is_libero ? " (L)" : "" }}
        </button>
        <span v-if="opponents.length === 0" class="muted">Keine Aufstellung.</span>
      </div>

      <div class="clickpath-row">
        <span class="clickpath-label">Annahme-Wertung</span>
        <button
          v-for="r in RECEPTION_OPTIONS"
          :key="r.code"
          type="button"
          :disabled="!receiverNumber"
          :title="`${r.label} (Aufschlag entspricht: ${r.servesAs})`"
          @click="finishServeReception(r.code)"
        >
          {{ r.code }}
        </button>
        <button
          type="button"
          class="secondary"
          title="Aufschlag hat den Gegner nicht erreicht — Netz oder Aus"
          @click="finishServeFault"
        >
          Fehler (Netz/Aus)
        </button>
      </div>
    </template>

    <template v-else>
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
          :title="e === '+' ? 'Auch Standardwert, wenn unklar/nicht genau gesehen' : ''"
          @click="finish(e)"
        >
          {{ e }}
        </button>
      </div>
    </template>

    <div class="clickpath-footer">
      <span class="clickpath-preview">
        Code: <code>{{ previewCode || "–" }}</code>
        <template v-if="skillLabel">&nbsp;({{ skillLabel }})</template>
      </span>
      <button type="button" class="secondary" @click="reset">Zurücksetzen</button>
    </div>
  </div>
</template>
