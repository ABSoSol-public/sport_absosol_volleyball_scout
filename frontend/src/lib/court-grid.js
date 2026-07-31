/**
 * Transponiert ein 2D-Raster (Zeilen/Spalten vertauscht). Wird von
 * VolleyballCourt.vue und RotationCourt.vue genutzt, um aus dem horizontalen
 * Zonenraster (Netz oben) das vertikale (Netz seitlich) abzuleiten, statt eine
 * zweite Tabelle von Hand zu pflegen. Empirisch gegen den gerenderten
 * RotationCourt verifiziert (Netzreihe landet korrekt in der netzseitigen
 * Spalte) — siehe PROGRESS.md.
 */
export function transpose(matrix) {
  return matrix[0].map((_, col) => matrix.map((row) => row[col]));
}
