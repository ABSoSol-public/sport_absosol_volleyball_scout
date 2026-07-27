# Roadmap

**Aktuelle Version: noch keine — in Entwicklung Richtung 1.0.**

## Versionsschema

- **1.0** = erste abgeschlossene Funktionalität. Jede weitere abgeschlossene Funktionalität
  erhöht die Version fortlaufend (1.1, 1.2, 1.3, …) — kein thematisches Bündeln, keine Lücken.
- **2.0** kommt erst nach dem **allerersten Livegang auf der Synology**. Bis dahin läuft alles
  unter 1.x, danach beginnt die 2.x-Reihe für alles, was nach dem ersten produktiven Betrieb
  entsteht.
- Scope laut Nutzerentscheidung (2026-07-27): **Analyse bestehender `.dvw`-Dateien und
  Live-Scouting neuer Spiele sind gleichwertige Kernfunktionen**, keine der beiden ist
  nachrangig. Die Versionen unten wechseln sich deshalb zwischen beiden Strängen ab, statt
  einen Strang komplett vor dem anderen abzuschließen.

## Geplante Versionen (Entwurf, nichts begonnen)

### Version 1.0 — Fundament: Datenmodell & lokale Infrastruktur
- [ ] Domänenmodell (Match, Team, Player, Set, Rally, Action) — Vorbild: `volleyscout/models.py`
      aus dem Prototyp `../volleyball_scout/`, aber Ziel-DB MariaDB statt SQLite
- [ ] MariaDB-Schema (Migrations-Tooling festlegen)
- [ ] Backend-Grundgerüst (Framework-Entscheidung noch offen) + Projektstruktur
- [ ] Docker-Compose **lokal**: Backend-Container + MariaDB-Container, lauffähig ohne Synology

### Version 1.1 — DVW-Import (Analyse-Strang, Start)
- [ ] `src/dv_reader.py` zum vollständigen Parser ausbauen (Basis: `protocol/*.json`,
      `../recherche/DataVolleyMedia_handbook.pdf`, `../recherche/dvwin2007_handbook.pdf`)
- [ ] Import einer einzelnen `.dvw`-Datei in die MariaDB
- [ ] Batch-Import über einen ganzen Ordner (Testquelle lokal: `../volleyscout_2/scoutdata/` —
      **nie einchecken**, siehe DSGVO-Hinweis in `PROGRESS.md`)

### Version 1.2 — Statistik-Auswertung (Analyse-Strang)
- [ ] Spieler-Statistiken (Asse/Aufschlagfehler, Annahme-Positivquote, Angriffseffizienz,
      Blockpunkte) — Vorbild: `volleyscout/stats.py`
- [ ] Team-Statistiken (Side-Out-/Break-Quote, Punktquellen)
- [ ] Rotationsanalyse
- [ ] Erste REST-API-Endpunkte zum Abfragen importierter Matches/Statistiken

### Version 1.3 — Web-Frontend: Match-Browser (Analyse-Strang)
- [ ] Liste importierter Matches
- [ ] Match-Detailansicht (Teams, Sätze, Ergebnis, Statistik-Panel)

### Version 1.4 — Live-Scouting-Engine (Live-Strang, Start)
- [ ] Scout-Code-Parser für Direkteingabe (`<Team><Nummer><Skill><Typ?><Bewertung><Zonen?>`)
- [ ] Match-Engine: Punkte, Rotation, Sätze/Match, Side-Out, Auszeiten, Wechsel, Undo —
      Vorbild: `volleyscout/engine.py`

### Version 1.5 — Live-Scouting-Frontend
- [ ] Web-UI fürs Live-Scouten: Scoreboard, Rotationsdarstellung beider Felder, Klickpfad
      (Team → Spieler → Skill → Bewertung) **und** Direkteingabe, Undo, Auszeit-/Wechsel-Bedienung
- [ ] Autosave nach jeder Eingabe (kein Datenverlust bei Absturz)

### Version 1.6 — Zeitstempel & DVW-Export
- [ ] Zeitstempel je Aktion (Wanduhrzeit + Zeitcode seit Satzbeginn) — gilt für Import **und**
      Live-Scouting einheitlich, Grundlage für spätere Video-Synchronisation
- [ ] Export im DVW-kompatiblen Stil (Anschlussfähigkeit an bestehende Tools/DataVolley)

### Version 1.7 — Zusammenführung Analyse- & Live-Strang
- [ ] Live-gescoutete Spiele erscheinen in derselben Match-Übersicht/Statistik wie importierte
- [ ] Validierung/Fehlerbehandlung, Protokoll unbekannter/nicht erkannter Codes (Vorbild:
      `unknown_tokens.csv` aus `../volleyscout_2/scout_app/`)

### Version 1.8 — Synology-Deployment-Vorbereitung
- [ ] Docker-Compose für Synology (Volumes, Env-Vars, MariaDB-Anbindung — eigenständiges
      NAS-Paket vs. Container ist hier noch zu entscheiden)
- [ ] Backup-Strategie für die Datenbank
- [ ] Reverse-Proxy/HTTPS-Vorbereitung

### Version 1.9 — Erster Livegang auf der Synology
- [ ] Deployment durchgeführt, Health-Check, End-to-End live verifiziert

**→ Version 2.0 beginnt erst hier**, mit allem, was nach dem ersten produktiven Betrieb als
Nächstes angegangen wird (noch nicht geplant).

## Hinweis zur Nummerierung

Diese Liste ist ein **Entwurf** zum jetzigen Zeitpunkt (2026-07-27) — Reihenfolge/Schnitt der
Versionen 1.0–1.9 kann sich beim tatsächlichen Zuschnitt noch verschieben, das
**Nummerierungsprinzip** (fortlaufend 1.x bis zum ersten Livegang, danach 2.0) steht aber fest.
Sobald eine Version tatsächlich abgeschlossen ist, wird der Eintrag hier mit `[x]` abgehakt und
in `PROGRESS.md` mit Details zur Umsetzung dokumentiert.
