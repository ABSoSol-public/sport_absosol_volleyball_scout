/**
 * Transponiert ein 2D-Raster (Zeilen/Spalten vertauscht, Spiegelung an der
 * Hauptdiagonale). Reine Hilfsfunktion für rotate90() unten — für sich genommen
 * KEINE 90°-Drehung (das war ein Fehler in einer früheren Fassung dieser Datei:
 * die Netzreihen-Spalte landete zwar korrekt an der Netzleiste, aber Position 1
 * auf der falschen Seite/Zeile, siehe PROGRESS.md).
 */
export function transpose(matrix) {
  return matrix[0].map((_, col) => matrix.map((row) => row[col]));
}

/**
 * Echte 90°-Drehung eines 2D-Rasters (Transpose + Zeilenreihenfolge umkehren).
 * Wird von VolleyballCourt.vue und RotationCourt.vue genutzt, um aus dem
 * horizontalen Zonenraster (Netz oben, Teams untereinander) das vertikale
 * (Netz seitlich, Teams nebeneinander) abzuleiten, statt eine zweite Tabelle
 * von Hand zu pflegen. Nutzerfeedback nach dem Dogfooding: reines transpose()
 * (ohne Zeilenumkehr) setzt Position 1 auf die falsche Seite — anhand der
 * konkreten Nutzerbeschreibung („links unten links, rechts oben rechts")
 * durchgerechnet und mit reverse() korrigiert; die bereits zuvor verifizierte
 * Netzreihen-Spaltenzuordnung bleibt davon unberührt (reverse() ändert nur die
 * Zeilen-, nicht die Spaltenreihenfolge).
 */
export function rotate90(matrix) {
  return transpose(matrix).reverse();
}
