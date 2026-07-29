# Das DVW-Dateiformat (DataVolley Scout File)

Referenzdokumentation für den Aufbau von `.dvw`-Dateien, als Grundlage für den Parser
(`src/dv_reader.py`, Ausbaustufe Roadmap-Version 1.1, siehe `docs/ROADMAP.md`).

**Quellen:**

- `../recherche/DataVolleyMedia_handbook.pdf` (71 Seiten, aktuelles Handbuch zu DataVolley 4
  Media, Release 4.2024.01) — Primärquelle, vollständig gelesen.
- `../recherche/dvwin2007_handbook.pdf` (66 Seiten, Handbuch zu Data Volley 2007 Media,
  Release 3.2013.05) — Sekundärquelle für Historie/Abweichungen, vollständig gelesen.
- `protocol/*.json` (bestehende Feldbeschreibungen für `3match`, `3players`, `3scout`, `3set`,
  `3teams`) und `src/dv_reader.py` (bestehender Sektions-Parser) — als Ausgangsbasis übernommen
  und hier gegen die Handbücher abgeglichen.
- Stichprobenartige Sichtung von 4 realen `.dvw`-Dateien aus
  `../volleyscout_2/scoutdata/` (nicht Teil des Git-Repos, DSGVO-sensibel) zur Verifikation
  der rohen Zeilenformate, da **keines der beiden Handbücher den rohen Dateiaufbau
  (Sektionsmarker, Spaltenlayout) dokumentiert** — beide sind reine Anwender-/UI-Handbücher.
  Stellen, die ausschließlich aus dieser Stichprobe stammen (nicht aus einem Handbuch), sind
  explizit als „anhand realer Dateien verifiziert" gekennzeichnet.

Wichtiger Befund vorab: **Beide Handbücher beschreiben die Data-Volley-Scout-Code-Syntax
(die Zeichenkette pro Aktion, z. B. `05SQ+16`) sehr detailliert, aber nicht das rohe
Zeilenformat der `.dvw`-Datei selbst** (Sektionsmarker `[3XXX]`, Semikolon-getrennte Spalten,
Zeilenumbrüche je Sektion). Dieses Wissen stammt aus dem bestehenden `dv_reader.py` und den
`protocol/*.json`-Dateien, ergänzt und verifiziert anhand echter Beispieldateien.

---

## 1. Überblick

Eine `.dvw`-Datei ist eine **zeilenbasierte Textdatei** mit folgenden Eigenschaften:

- **Encoding**: In den untersuchten Beispieldateien (DataVolley 3.x / "Basic"/"Media",
  Jahrgänge 2009–2010) **ISO-8859-1 / Windows-1252 (Latin-1)** — bestätigt durch
  `dv_reader.py` (`open(..., encoding="Latin-1")`) und funktionierendes Einlesen der
  Beispieldateien mit `iconv -f ISO-8859-1`. Das aktuelle DataVolleyMedia-Handbuch
  (Abschnitt 5.4 „Language Settings" / „Compatibility", S. 61) bestätigt das Prinzip: **Data
  Volley 4 speichert Notizen/Team-/Spielernamen intern als Unicode**, ältere Versionen
  (Data Volley 2007, Click & Scout) benutzen dagegen die **Codepage der Windows-Installation**
  (Default in Deutschland/Westeuropa: 1252). Ein Parser sollte also **nicht blind UTF-8
  voraussetzen**, sondern defensiv mit Latin-1/CP1252 einlesen bzw. bei Bedarf eine
  Encoding-Erkennung vorsehen (offene Frage, siehe Abschnitt 6).
- **Zeilenende**: klassische Windows-Zeilenumbrüche (CRLF in den Originaldateien).
- **Struktur**: Die Datei ist in **Sektionen** unterteilt, jede eingeleitet durch eine
  Markerzeile der Form `[3XXX]`. Alle Zeilen bis zur nächsten `[3XXX]`-Markerzeile (oder
  Dateiende) gehören zur jeweiligen Sektion.
- **Feldtrennzeichen innerhalb einer Sektionszeile**: Semikolon (`;`). Leere Felder bleiben
  als aufeinanderfolgende `;;` erhalten (feste Spaltenanzahl pro Zeile, keine "sparsame"
  Auslassung).
- **Kopfzeilen-Metadaten**: Die erste Sektion `[3DATAVOLLEYSCOUT]` enthält kein
  Semikolon-Tabellenformat, sondern `SCHLÜSSEL: WERT`-Zeilen (siehe 2.1).

Beispiel für den Dateianfang (aus einer realen Datei, gekürzt):

```
[3DATAVOLLEYSCOUT]
FILEFORMAT: 2.0
GENERATOR-DAY: 17/10/2010 19.19.02
GENERATOR-IDP: DVW
GENERATOR-PRG: Data Volley
GENERATOR-REL: Release 3.2.7
GENERATOR-VER: Basic
GENERATOR-NAM: VC Stuttgart
LASTCHANGE-DAY: 17/10/2010 21.29.46
LASTCHANGE-IDP: DVW
LASTCHANGE-PRG: Data Volley
LASTCHANGE-REL: Release 3.2.7
LASTCHANGE-VER: Basic
LASTCHANGE-NAM: VC Stuttgart
[3MATCH]
17/10/2010;19.30.00;2010/2011;Oberliga;Vorrunde;Zuhause;So;;1;1;Z;0;
;;40468;
[3TEAMS]
OL07;TSV G.A. Stuttgart;2;Max Mustermann;;16777215;
OL04;TV Rottenburg;3;Erika Musterfrau;Peter Beispiel;16777215;
...
[3SCOUT]
*P05>LUp;;;;;;;19.29.47;1;5;6;;;;5;10;6;1;11;3;13;10;6;1;11;3;
...
```

Der bestehende `Data_Volley_Parser` in `src/dv_reader.py` kennt bereits alle 13
Sektionsmarker (`[3DATAVOLLEYSCOUT]`, `[3MATCH]`, `[3TEAMS]`, `[3MORE]`, `[3COMMENTS]`,
`[3SET]`, `[3PLAYERS-H]`, `[3PLAYERS-V]`, `[3ATTACKCOMBINATION]`, `[3SETTERCALL]`,
`[3WINNINGSYMBOLS]`, `[3RESERVE]`, `[3SCOUT]`) und zerlegt die Datei anhand von Start-/End-IDs
in ein Dictionary pro Sektion — das ist die Grundlage, auf der die feldweise Interpretation
(Gegenstand dieses Dokuments) aufsetzt.

---

## 2. Sektionen im Detail

### 2.1 `[3DATAVOLLEYSCOUT]` — Metainformationen zur Datei

Kein Semikolon-Format, sondern `SCHLÜSSEL: WERT` pro Zeile. Beobachtete Schlüssel (anhand
realer Dateien; von keinem Handbuch tabellarisch dokumentiert):

| Schlüssel | Bedeutung |
|---|---|
| `FILEFORMAT` | Versionsnummer des Dateiformats selbst (beobachtet: `2.0`, sowohl in alten als auch neueren Dateien — **kein zuverlässiger Indikator** für Encoding oder Software-Version) |
| `GENERATOR-DAY` | Erstellungszeitpunkt (`TT/MM/JJJJ HH.MM.SS`) |
| `GENERATOR-IDP` | Immer `DVW` beobachtet |
| `GENERATOR-PRG` | Programmname, z. B. `Data Volley` |
| `GENERATOR-REL` | Release-Nummer der erzeugenden Software, z. B. `Release 3.2.7`, `Release 3.2009.3` |
| `GENERATOR-VER` | Produktvariante: `Basic`, `Media`, `Professional`, `Lite` (siehe Versionsmatrix DVWin2007-Handbook S. 7) |
| `GENERATOR-NAM` | Freitext, meist Vereins-/Verbandsname |
| `LASTCHANGE-*` | Gleiche Felder wie `GENERATOR-*`, aber zum letzten Bearbeitungszeitpunkt |

### 2.2 `[3MATCH]` — Spielinformationen

Laut `protocol/3match.json` und verifiziert an echten Daten, **zwei Zeilen** pro Datei:

Zeile 1 (Feldindex → `sp_*`-Name aus `3match.json`):

| Index | Feld (`protocol/3match.json`) | Beobachteter Wert | Anmerkung |
|---|---|---|---|
| 0 | `sp_date` | `17/10/2010` | Format `TT/MM/JJJJ` |
| 1 | `sp_time` | `19.30.00` | Format `HH.MM.SS` |
| 2 | `sp_season` | `2010/2011` | |
| 3 | `sp_league` | `Oberliga` | entspricht „Competition" im Match-notes-Fenster |
| 4 | `sp_phase` | `Vorrunde` | |
| 5 | `sp_home_away` | `Zuhause` | **Unklar**, siehe Abschnitt 6 — passt inhaltlich nicht sauber zu den im Handbuch gezeigten Match-notes-Feldern (Competition/Phase/Match N./Day N./Type/Regulation); evtl. Freitext-Feld ohne feste Dropdown-Werte in älteren/regionalen Ligen |
| 6 | `sp_day_number` | `So` | **Unklar** — beobachteter Wert ist eine Wochentagsabkürzung („Sonntag"), nicht wie der Feldname suggeriert eine Spieltag-Nummer; Feldname aus `3match.json` evtl. irreführend, siehe Abschnitt 6 |
| 7 | `sp_match_number` | (leer) | |
| 8 | `sp_text_encoding` | `1` | vermutlich Verweis auf Codepage/Sprache |
| 9 | `sp_regulation` | `1` | vermutlich Regelwerk-Enum (Rally Point etc.) |
| 10 | `zones_or_cones` | `Z` | `Z` = Zonen (vs. Cones/Kegel, siehe DataVolleyMedia-Handbook 6.1 Combination-Analyse) |
| 11 | *(kein Protokollfeld)* | `0` | in Beispieldaten zusätzlich vorhanden, nicht in `3match.json` erfasst |

Zeile 2: in Beispieldaten `;;40468;` — **nicht in `protocol/3match.json` abgebildet**. Das
dritte Feld enthält eine numerische ID (vermutlich interne Media-Plugin-/Wettbewerbs-ID des
Spiels). Offene Frage, siehe Abschnitt 6.

### 2.3 `[3TEAMS]` — Teams

Zwei Zeilen (Heim, Gast). Laut `protocol/3teams.json`, ergänzt um ein zusätzliches, real
beobachtetes Feld:

| Index | Feld | Beobachteter Wert | Anmerkung |
|---|---|---|---|
| 0 | `sp_team_id` | `OL07` | Team-Code (siehe DataVolleyMedia-Handbook 2.3.3.1: 3-stelliger Code) |
| 1 | `sp_team` | `TSV G.A. Stuttgart` | Vollständiger Teamname |
| 2 | `sp_sets_won` | `2` | Anzahl gewonnener Sätze |
| 3 | `sp_coach` | `Max Mustermann` | |
| 4 | `sp_assistant` | *(leer möglich)* | |
| 5 | *(kein Protokollfeld)* | `16777215` | Dezimale RGB-Farbe (Trikotfarbe, `16777215` = `0xFFFFFF` = Weiß) — passt zu „Choose the color of the shirt" im Match-notes-Fenster (DataVolleyMedia-Handbook S. 34) |

### 2.4 `[3MORE]` — Austragungsort/Schiedsrichter

**Kein `protocol/*.json` vorhanden** — Feldlayout ausschließlich aus realen Beispieldateien
abgeleitet, unter Abgleich mit dem „Match notes"-Fenster (Bereich „Other": Referees,
Spectators, Income, City, Hall, Scouts):

Zeile 1 (6 Felder, vermutete Zuordnung):

`Referees;Spectators;Income;City;Hall;Scouts`

Beispiel (anonymisiert): `;;;;;Mustermann "Max";` → nur „Scouts" (Scoutman-Name) gefüllt.

Zeile 2: in Beispieldaten `;0;0;` — Bedeutung unklar (evtl. Zuschauerzahl/Einnahmen numerisch
dupliziert oder End-Zeit-bezogen, das Match-notes-Fenster zeigt zusätzlich ein Feld „End
Time"). Offene Frage, siehe Abschnitt 6.

### 2.5 `[3COMMENTS]` — Kommentare

Wenn keine Kommentare vorhanden: wörtlich die Zeile `no comments`.
Andernfalls eine Zeile mit (vermutlich) 4 Semikolon-getrennten Feldern, passend zum
„Match comments"-Fenster (DataVolleyMedia-Handbook S. 35): `Summary comments;Match
description;Coach comments (Heim);Coach comments (Gast)`.

Beispiel real: `;;;Rottenburg 13 Zuspieler` (nur das vierte Feld gefüllt).

### 2.6 `[3SET]` — Satzergebnisse

5 Zeilen (eine je möglichem Satz, unabhängig davon ob gespielt). Laut `protocol/3set.json`:

| Index | Feld | Beispielwert | Anmerkung |
|---|---|---|---|
| 0 | `sp_played` | `True` | **Vorsicht**: Name ist ggf. irreführend — in unbespielten/abgebrochenen Testdateien stand ebenfalls `True` bei leeren Score-Feldern. Passt eher zu „wird dieser Satz im Rally-Point-System gescoutet" (Checkbox „Tie-Break"-Regulation im Match-notes-Fenster, DataVolleyMedia-Handbook S. 34), nicht zwingend zu „wurde tatsächlich gespielt". Siehe Abschnitt 6. |
| 1 | `sp_score_intermediate1` | `8 -6` | Zwischenstand (laut Handbook automatisch bei Punkt 8 eingetragen) |
| 2 | `sp_score_intermediate2` | `14-16` | Zwischenstand bei Punkt 16 |
| 3 | `sp_score_intermediate3` | `15-21` | Zwischenstand bei Punkt 21 |
| 4 | `sp_score` | `21-25` | Satzendstand |
| 5 | `sp_duration` | `26` | Satzdauer in Minuten (vom Scoutman am Satzende eingegeben, DataVolleyMedia-Handbook 3.10) |

Unbespielte Sätze (z. B. Satz 5 bei einem 3:1-Ergebnis) erscheinen mit `True;;;;;;` (Flag
gesetzt, alle Score-Felder leer).

### 2.7 `[3PLAYERS-H]` / `[3PLAYERS-V]` — Spielerlisten Heim/Gast

Eine Zeile pro Spieler. Laut `protocol/3players.json`, ergänzt um real beobachtete
Zusatzfelder:

| Index | Feld | Beispielwert | Anmerkung |
|---|---|---|---|
| 0 | `sp_unknown_0` | `0` bzw. `1` | **Verifiziert**: `0` in `[3PLAYERS-H]`, `1` in `[3PLAYERS-V]` — vermutlich Team-Flag (Heim/Gast), redundant zur Sektionszugehörigkeit |
| 1 | `sp_number` | `1` | Trikotnummer |
| 2 | `sp_unknown_2` | `11` | laufender Index/interne ID innerhalb der Datei (fortlaufend 1..n über beide Teams? in Beispiel eigenständig je Team hochgezählt) |
| 3–7 | `sp_starting_position_set1`…`set5` | `4`, `4`, `4`, `5`, *(leer)* | Zone (1–6) in der Startaufstellung des jeweiligen Satzes; `*` wenn der Spieler **nicht** in der Startsechs war, aber im Satz eingewechselt wurde; leer wenn er im Satz gar nicht spielte |
| 8 | `sp_player_id` | `MUSERI` | Spieler-Code (Handbook-Konvention: erste 3 Buchstaben Nachname + erste 3 Buchstaben Vorname); anonymisiertes Beispiel |
| 9 | `sp_lastname` | `Mustermann` | anonymisiertes Beispiel |
| 10 | `sp_firstname` | `Erika` | anonymisiertes Beispiel |
| 11 | `sp_nickname` | *(meist leer)* | |
| 12 | `sp_special_role` | `L` / `C` / leer | `L` = Libero, `C` = Captain (Handbook: „Id: L=Libero, C=Captain") |
| 13 | `sp_role` | `2` | Positions-Enum, vermutlich `1`=Setter, weitere Werte für Außen/Mitte/Dia/Libero — **exakte Enum-Zuordnung nicht durch Handbuch dokumentiert**, offene Frage |
| 14 | `sp_foreign` | `False` | Ausländer-Flag (Handbook: „For." = foreign) |
| 15–17 | *(kein Protokollfeld)* | leer | 3 weitere Felder in Beispieldaten immer leer beobachtet, Bedeutung unklar |

### 2.8 `[3ATTACKCOMBINATION]` — Angriffskombinationen

Definiert die im Advanced Code (Feld „Cmb", Positionen 7–9, siehe Abschnitt 3.2) verwendbaren
2-stelligen Kombinationscodes (z. B. `X5`, `V0`, `CB`). Kein `protocol/*.json` vorhanden.
Beispielzeile:

```
XF;2;L;Q;Quick lower set behind;;16711680;4976;C;;
```

Grob zuordenbar (nicht im Handbuch tabellarisch dokumentiert, aus Kontext der UI-Screenshots
in DataVolleyMedia-Handbook 3.5.2 „Modify code" abgeleitet): Code; Zuspielzone; Seite
(`L`/`R`/`C` = Links/Rechts/Center); Balltyp (`H`/`M`/`Q`/`T`/`U`/`N`/`O`, siehe Abschnitt
3.1); Beschreibung; *(unbenutzt)*; Farbe (dezimales RGB); *(unbenutzt)*; Zielbereich-Kürzel
(`C`/`F`/`B`/`P`/`S`/`-`); *(unbenutzt)*; *(unbenutzt)*. Diese Zuordnung ist eine
Interpretation und **keine gesicherte Spezifikation** — siehe Abschnitt 6.

Anmerkung zu den Standard-Codes (aus DataVolleyMedia-Handbook „Code syntax"-Tabelle, S. 27):
Zielbuchstaben `W`, `Y`, `G`, `P`, `.` als Combo-Präfixe für „Attk", `K.` für Setter Calls
sowie numerische Cone-Codes 1–8 für „Cone Attk" (nur Professional-Version, siehe Abschnitt
3.2).

### 2.9 `[3SETTERCALL]` — Zuspieler-Ansagen

Analog zu `[3ATTACKCOMBINATION]`, aber für Setter-Call-Codes (`K1`, `K2`, `K7`, `KC`, `KM`,
`KP`, `KE` laut DVWin2007-Handbook S. 12, dort auch mit Klartext-Beschreibung: „First Tempo
Forward/Behind", „Super in 3/4", „Shift in 2/4", „No First Tempo"). In beiden Stichproben-Dateien leer
(keine Setter-Calls gescoutet) — Feldlayout daher nicht anhand echter Daten verifizierbar,
nur aus dem DVWin2007-Handbook-Screenshot (Spalten: Code; Color; Description) grob ableitbar.

### 2.10 `[3WINNINGSYMBOLS]` — Gewinnsymbol-Konfiguration

Eine Zeile, offenbar ein Tilde-gepolstertes Muster, z. B.:

```
=~~~#~~~=~~~~~~~=/~~#~~~=/~~#~~~=~~~~~~~=~~~~~~~=~~~~~~~
```

Entspricht der Tabelle „Winning symbols" (DataVolleyMedia-Handbook 2.3.4.2): pro Skill
(Serve, Reception, Attack, Block, Dig, Set, Free ball) wird definiert, welches
Bewertungssymbol Punktgewinn (`#`) bzw. -verlust (`=`) bedeutet. Die exakte
Segmentierung/Blocklänge dieser Zeile in einzelne Skill-Abschnitte ist **nicht verifiziert**
(offene Frage).

### 2.11 `[3RESERVE]` — unbekannt

In beiden Stichproben-Dateien leer. Weder Handbuch noch reale Daten geben Aufschluss über
Zweck/Format. `dv_reader.py` markiert diese Sektion bereits treffend als `"desc":"unknown"`.
Offene Frage.

### 2.12 `[3SCOUT]` — die eigentliche Spielaufzeichnung

Die zentrale Sektion: eine Zeile pro Aktion/Code (Aufschlag, Annahme, Angriff, Block, Abwehr,
Zuspiel, Punktvergabe, Wechsel, Auszeit, Rotationswechsel, Satzende …). Laut
`protocol/3scout.json`, **vollständig verifiziert** anhand realer Zeilen (siehe Beispiel
unten):

| Index | Feld (`protocol/3scout.json`) | Beispielwert | Anmerkung |
|---|---|---|---|
| 0 | `sp_game_code` | `*10AH#~~~~~~H` | Der (ggf. tilde-gepolsterte) normalisierte Code, siehe Abschnitt 3 |
| 1 | `sp_point_phase` | `s` | Beobachtete Werte: `s`, `p`, leer — **Bedeutung nicht durch Handbuch dokumentiert**, siehe Abschnitt 6 |
| 2 | `sp_attack_phase` | `r` | Beobachtete Werte: `r`, `s`, `p`, leer — meist nur bei Angriffscodes gefüllt; **Bedeutung nicht gesichert**, siehe Abschnitt 6 |
| 3 | `sp_unknown_3` | leer | in Stichprobe durchgehend leer |
| 4 | `sp_start_coordinate` | leer/numerisch | Pixel-/Klick-Koordinate aus der maus-basierten Trajektorien-Eingabe (DataVolleyMedia-Handbook 3.5.2, „click start + end points"), nur gefüllt wenn im Court-Fenster eingezeichnet wurde |
| 5 | `sp_mid_coordinate` | leer/numerisch | dritter Punkt bei „Ctrl+Klick" (Deflection/Block-Ablenkung), siehe Handbook S. 44 |
| 6 | `sp_end_coordinate` | leer/numerisch | Landepunkt-Koordinate |
| 7 | `sp_timestamp_input` | `19.31.21` | Uhrzeit der Eingabe (`HH.MM.SS`) — Basis für Video-Synchronisation |
| 8 | `sp_set_number` | `1` | laufender Satz |
| 9 | `sp_home_setter_pos` | `1` | Rotationsposition (1–6) des Heim-Zuspielers zum Zeitpunkt der Aktion |
| 10 | `sp_guest_setter_pos` | `1` | dito Gast |
| 11 | `sp_video_file_number` | `1` | Video-Dateinummer (Media-Player-Feature) |
| 12 | `sp_time_ticks_video` | `793` | Zeitcode-Ticks für Video-Sync (DataVolleyMedia-Handbook 2.5.3 „time code creation for video sync") |
| 13 | `sp_unknown_13` | leer | in Stichprobe durchgehend leer |
| 14–19 | `sp_player_home_pos_1`…`_6` | `2;1;16;7;11;9` | Trikotnummern der 6 Heim-Spieler auf dem Feld, **positionsgebunden** (Index 14 = Zone 1, Index 19 = Zone 6 — verifiziert anhand der Rotationslogik: bei Rotationswechsel `*z6` verschieben sich die Werte zyklisch) |
| 20–25 | `sp_player_guest_pos_1`…`_6` | `2;7;12;4;17;16` | dito Gastteam |
| 26 | `sp_unknown_26` | leer | in Stichprobe durchgehend leer (bzw. entfällt als letztes leeres Feld vor dem Zeilenende-Semikolon) |

Beispielzeilen (real, aus `&vor08 allianz vo-usc münster.dvw`):

```
*P02>LUp;;;;;;;;1;5;3;;;;2;1;16;7;11;9;2;7;12;4;17;16;
*z1>LUp;;;;;;;;1;1;3;;;;2;1;16;7;11;9;2;7;12;4;17;16;
*02ST!~~~16;;;;;;;19.31.21;1;1;1;1;788;;2;1;16;7;11;9;2;7;12;4;17;16;
a01RT!~~~16;;;;;;;19.31.21;1;1;1;1;788;;2;1;16;7;11;9;2;7;12;4;17;16;
a07AH+~~~24~H;;r;;;;;19.31.27;1;1;1;1;793;;2;1;16;7;11;9;2;7;12;4;17;16;
*16BH-~~~~4;;;;;;;19.31.27;1;1;1;1;793;;2;1;16;7;11;9;2;7;12;4;17;16;
a17AH-~~~85~H;;s;;;;;19.31.27;1;1;1;1;797;;2;1;16;7;11;9;2;7;12;4;17;16;
*18DH#~~~85;;;;;;;19.31.27;1;1;1;1;798;;2;1;16;7;11;9;2;7;12;4;17;16;
*01AH=~~~41~H;s;p;;;;;19.31.32;1;1;1;1;799;;2;1;16;7;11;9;2;7;12;4;17;16;
a$$&H#;s;;;;;;19.31.32;1;1;1;1;799;;2;1;16;7;11;9;2;7;12;4;17;16;
ap00:01;;;;;;;19.31.37;1;1;1;1;804;;2;1;16;7;11;9;2;7;12;4;17;16;
az6;;;;;;;19.31.37;1;1;6;1;804;;2;1;16;7;11;9;7;12;4;17;16;2;
```

**Wichtiger, nur anhand echter Daten verifizierter Befund — feste Feldbreite im
`sp_game_code`-Feld (Feld 0):**

Der normalisierte Code in Feld 0 wird intern **mit `~` (Tilde) auf feste Breite aufgefüllt**,
sofern optionale Felder des Advanced/Extended Codes (siehe Abschnitt 3.2/3.3) fehlen. Das
Padding reicht dabei genau bis zum letzten tatsächlich belegten Feld — komplett leere
Folgefelder werden nicht mehr angehängt. Beispiel `a07AH+~~~24~H` zerlegt sich exakt in die
Code-Syntax-Tabelle (DataVolleyMedia-Handbook S. 27) wie folgt:

| Zeichen(gruppe) | Code-Position | Bedeutung |
|---|---|---|
| `a07AH+` | 1–6 (Main Code) | Team `a`, Spieler `07`, Skill `A` (Attack), Typ `H` (High), Bewertung `+` |
| `~~~` | 7–9 (Cmb) | leer (keine Angriffskombination gescoutet) |
| `2` | 10 (Start zone) | Startzone 2 |
| `4` | 11 (End zone) | Zielzone 4 |
| `~` | 12 (End zone+) | leer (keine Subzone A–D) |
| `H` | 13 (Skill type, Extended Code) | `H` = Hard Spike |

Für Block-Codes fehlt die Startzone grundsätzlich (Blocker hat keine Ausgangszone), daher ein
Zeichen weniger: `*16BH-~~~~4` = Main(6) + Cmb `~~~` (leer) + Start `~` (leer) + End `4`.
**Diese Zusatzerkenntnis steht in keinem der beiden Handbücher und wurde ausschließlich durch
Abgleich der Code-Syntax-Tabelle mit rohen Dateizeilen rekonstruiert** — beim Parser-Bau
unbedingt mit weiteren, diverseren Beispieldateien gegenprüfen (siehe Abschnitt 6).

---

## 3. Die Scout-Code-Sprache in `[3SCOUT]`

### 3.1 Aufbau des Main Code (Positionen 1–6, immer vorhanden)

Schema: `<Team><Spielernummer><Skill><Typ><Bewertung>`

| Position | Länge | Feld | Werte |
|---|---|---|---|
| 1 | 1 | Team | `*` = Heimteam (wird von der Software automatisch vorangestellt, muss beim manuellen Eintippen **nicht** eingegeben werden), `a` = Gastteam (**muss** explizit eingegeben werden) |
| 2–3 | 2 | Spielernummer | `00`–`99`, führende Null bei einstelligen Nummern im normalisierten Code |
| 4 | 1 | Skill | siehe Tabelle unten |
| 5 | 1 | Typ (Type of Hit) | siehe Tabelle unten, skill-abhängige Bedeutung |
| 6 | 1 | Bewertung (Evaluation) | siehe Tabelle unten, skill-abhängige Bedeutung |

**Skill-Codes** (DataVolleyMedia-Handbook S. 28, identisch in DVWin2007-Handbook S. 19):

| Code | Skill |
|---|---|
| `S` | Serve (Aufschlag) |
| `R` | Reception (Annahme) |
| `A` | Attack (Angriff) |
| `B` | Block |
| `D` | Dig (Abwehr/Feldabwehr) |
| `E` | sEt (Zuspiel) |
| `F` | Free ball (Freiball) |

**Typ-Codes** (Bedeutung je Skill unterschiedlich — der Buchstabe bleibt gleich, die
Bedeutung wechselt je nach Skill, DataVolleyMedia-Handbook S. 28–29):

| Code | Bezeichnung | Serve | Reception | Attack | Block |
|---|---|---|---|---|---|
| `H` | High | Floating serve | auf Floating-Aufschlag | High ball | auf High-Ball-Angriff |
| `M` | Medium | Jump float serve | auf Jump-Float-Aufschlag | Half ball | auf Half-Ball-Angriff |
| `Q` | Quick | Jump serve | auf Jump-Aufschlag | Quick ball | auf Quick-Angriff |
| `T` | Tense | *(Standard: nicht verwendet)* | *(Standard: nicht verwendet)* | Head ball | auf Tense-Angriff |
| `U` | sUper | *(Standard: nicht verwendet)* | *(Standard: nicht verwendet)* | Super ball | auf Super-Ball-Angriff |
| `N` | Fast | *(Standard: nicht verwendet)* | *(Standard: nicht verwendet)* | Fast ball | auf Fast-Ball-Angriff |
| `O` | Other | *(Standard: nicht verwendet)* | *(Standard: nicht verwendet)* | Other (custom) | auf sonstigen Angriffstyp |

Für Block/Reception/Dig gilt laut Handbook: „the type of hit is equal to that of the skill
performed immediately before" — d. h. der Typ referenziert den Typ der **vorangegangenen**
Aktion (z. B. eine „High"-Annahme bezieht sich auf einen als „High" klassifizierten
Aufschlag, nicht auf die Flugbahn der Annahme selbst). Bei sEt variiert der Typ je nach dem
nachfolgenden Angriff.

**Wichtiger Praxis-Befund (anhand echter Daten):** Obwohl das Handbuch T/U/N/O für Serve und
Reception als „not used in standard scouting" kennzeichnet, wurden in einer realen
Vereins-Datei tatsächlich Serve-/Reception-Codes mit Typ `T` beobachtet
(`*02ST!`, `a01RT!`). Ein Parser sollte daher **immer alle 7 Typ-Codes (H/M/Q/T/U/N/O) für
jeden Skill akzeptieren**, unabhängig von der „Standard"-Einschränkung des Handbuchs.

**Bewertungscodes** (Evaluation, DataVolleyMedia-Handbook S. 30–32, inhaltlich identisch zu
DVWin2007-Handbook S. 20–21):

| Code | Bedeutung allgemein | Serve | Reception | Attack | Block | Dig | Set | Free Ball |
|---|---|---|---|---|---|---|---|---|
| `=` | Fehler | Netz/Aus/Fußfehler | Fehler (Annahme unmöglich/Rotationsfehler) | Fehler (Aus/Netz/Übertritt) | Fehler (Netz/Aus/eigene Seite) | Ball nicht abgewehrt/Rallye-Ende | Fehler (Netz/Aus/Fußfehler) | Fehler (Boden/Aus) |
| `/` | sehr schlecht/geblockt | Annahme des Gegners „sehr schlecht" | Ball direkt beim Gegner/erzwungener Freiball | Angriff geblockt (Punkt Gegner) | Invasion (Netz-/Antennenberührung, Punkt Gegner) | Ball direkt zum Gegner gespielt | Ball geht direkt zum Gegner | direkt zum Gegner gespielt/erzwungener Freiball |
| `-` | schwach | Annahme des Gegners „positiv/perfekt" | nur Pflichtangriff möglich | leicht verteidigt, Gegenangriff möglich | Block lässt einfache Abwehr zu | Abwehr/Cover ohne Angriffsmöglichkeit | technisch ungenau, kein Angriff möglich | nur Pflichtangriff möglich |
| `!` | unzureichend/individuell | Annahme des Gegners „gut" | Annahme „gut" (außerhalb 3-m-Linie, nicht alle Kombis möglich) | geblockt, aber vom Angriffsteam gerettet | vom Gegner „covered" | positive Abwehr nach Block, Angriff möglich | frei belegbar (kundenspezifisch) | ausreichend (außerhalb 3-m-Linie) |
| `+` | positiv | Annahme des Gegners „schwach" | Annahme „positiv" (innerhalb 3-m-Linie) | Gegner verteidigt schwer, kein Gegenangriff | lässt positive Abwehr zu | einfache Abwehr, Angriff möglich | Folgeangriff mit 2–3-fach-Block | positiv (innerhalb 3-m-Linie) |
| `#` | Punkt/perfekt | Ass (direkter Punkt) | perfekte Annahme (alle Kombis möglich) | Punkt (direkter Angriffserfolg) | Blockpunkt | perfekte Abwehr (auch nach Finte) | Folgeangriff ohne/mit 1er-Block | perfekt (alle Kombis möglich) |

### 3.2 Advanced Code (Positionen 7–12, optional)

| Position(en) | Feld | Bedeutung |
|---|---|---|
| 7–9 (`Cmb`, 3 Zeichen) | Angriffskombination / Setter-Ansage / Ziel-Angriff / Cone | Für Angriffe: 2-stelliger Kombinationscode aus `[3ATTACKCOMBINATION]` (z. B. `X5`, `V0`) — Präfixe `W`, `Y`, `G`, `P` als Sammelkategorien. Für Zuspiel: Setter-Call-Code aus `[3SETTERCALL]` (`K.` + Ziffer/Kürzel). Für Ziel-Angriff („Targ Attk"): `Front`/`Center`/`Back`/`Pipe`/`Setter`. Für Cone-Angriffe (nur Professional-Version, siehe DVWin2007-Handbook S. 12): numerisch `1`–`8` |
| 10 | Startzone | `1`–`9` für Attack; für Serve nur `1`,`9`,`6`,`7`,`5` (siehe Abschnitt 3.4) |
| 11 | Zielzone (Endzone) | `1`–`9`, für alle Skills mit Landepunkt (Rec/Set/Dig/Blk/FrB analog) |
| 12 | Zielzone+ / Subzone | `A`–`D` (verfeinerte Unterteilung der Zielzone in 4 Subzonen, siehe Rotation-und-Direction-Fenster im Handbuch, z. B. S. 43) |

**Umgesetzt (Version 2.6)**: alle drei Felder (Cmb/Ziel-Angriff/Subzone) werden vom Parser
ausgelesen (`app/dvw/parser.py`, `DvwScoutRow.attack_combination/target_attack/subzone`) und
landen in `scout_actions` (Migration `0005`). Die Subzone ist auch in der Live-Scouting-
Direkteingabe erfassbar (`app/engine/scout_code.py`, z. B. `14AH+45B`), inkl. drehbarem
Zonen-/Subzonen-Helfer im Frontend (`VolleyballCourt.vue`). Kombinationscodes/Setter-Calls
bleiben in der Direkteingabe bewusst unterstützt nur beim Import (Live-Erfassung wäre in der
kompakten Kurzeingabe mehrdeutig ohne Trennzeichen) — Details und Beispielcodes (`X5`, `V6`,
`K1` …) in `../recherche/Data_Volley_4_Funktionsanalyse.md` Abschnitt 3.2.

### 3.3 Extended Code (Positionen 13–15, optional, nur wenn Zusatzdetails erfasst wurden)

| Position | Feld | Werte je Skill |
|---|---|---|
| 13 (Skill type) | Ausführungsart | **Attack**: `H` Hard Spike, `P` Soft Spike, `T` Tip. **Block**: `0` no Block, `1`/`2`/`3` Spieler am Block, `4` hole Block. **Reception**: `L` on Left, `R` on Right, `W` low, `O` Overhead, `M` Middleline. **Set**: `1` 1 Hand, `2` 2 Hands, `3` Bump, `4` Other, `5` Underhand. **Dig**: `S` on Spike, `C` spike Cover, `B` after Block, `E` Emergency |
| 14 (Players) | Anzahl Blockspieler bei Angriff | `0` kein Block, `1`–`3` Spieler am Block, `4` hole Block (Loch im Block) |
| 15 (Special) | Zusatzinfo, u. a. Fehlerarten und Punktarten, skill-abhängig, z. B.: **Attack Points**: `S` Block Out Side, `O` Block Out Long, `F` Block on Floor, `X` Direct on Floor, `N` Let, `C` Continue Block Control. **Attack Errors**: `5` Attack out side, `O` Attack out long, `N` Attack in Net, `I` Net contact, `A` Antenna, `Z` Referee call. **Block Errors**: `5` Ball out side, `O` Ball out long, `F` Ball on floor, `X` between hands, `N` hands-Net, `I` Net contact, `A` Antenna, `P` No jump, `T` Position error, `Z` Referee call. **Reception Errors**: `U` Unplayable, `P` position error, `E` Lack of effort, `Z` Referee call. **Serve Points/Errors**: `N` Let/Continue, `O` Ball out long, `L` Ball out left, `R` Ball out right, `N` Ball in Net, `Z` Referee call. **Set Errors**: `U` Unhitable, `I` Net touch, `Z` Referee call. **Dig Errors**: `U` Unplayable, `X` body error, `P` position error, `Z` Referee call, `B` Ball on floor, `O` Ball out, `E` Lack of effort. **Free Ball Errors**: `U` Unplayable, `X` body error, `P` position error, `Z` Referee call |

(Quelle für 3.3: DataVolleyMedia-Handbook, „Code syntax"-Tabelle S. 27, Spalte „Extended
code".)

### 3.4 Zonen-/Koordinatensystem

**Wichtige Klarstellung/Korrektur gegenüber der bisherigen Notiz in
`volleyscout_2/prompt - erklärung.md`**: Diese frühere Notiz beschreibt ein einheitliches
9-Zonen-Raster (Netzreihe 4-3-2, Mitte 7-8-9, Grundlinie 5-6-1, im Uhrzeigersinn), das für
**Angriffs-, Block-, Abwehr- und Zuspielzonen (Zielzone, Position 11) korrekt ist** — das
Handbuch bestätigt für diese Skills durchgängig Zonenwerte `1`–`9`.

**Für den Aufschlag (Serve-Startzone, Position 10) gilt jedoch ein Sonderfall**, der von
DataVolleyMedia-Handbook Abschnitt 6.2 „Serve Starting zone" (S. 64) **explizit als
eigenständige Regel** beschrieben wird und nicht das volle 9er-Raster nutzt: Die
Grundlinie wird beim Aufschlag in **5 Startzonen** unterteilt, benannt (von links nach
rechts aus Sicht des Aufschlägers) `5, 7, 6, 9, 1`:

| Zone | Bedeutung |
|---|---|
| `5` | Aufschlag aus Zone 5 (links) |
| `7` | Aufschlag aus dem Bereich zwischen Zone 6 und 5 |
| `6` | Aufschlag aus Zone 6 (Mitte) |
| `9` | Aufschlag aus dem Bereich zwischen Zone 1 und 6 |
| `1` | Aufschlag aus Zone 1 (rechts) |

Diese 5 Werte (`1`, `9`, `6`, `7`, `5`) sind identisch mit den in der Code-Syntax-Tabelle (S.
27) unter „Srv" im Feld „Start zone" gelisteten Werten (`561 79`) — die Tabelle ist an dieser
Stelle nur kompakt/unsortiert dargestellt, inhaltlich deckungsgleich mit Abschnitt 6.2.

**Was das Handbuch nicht liefert**: eine explizite grafische Darstellung des vollen
9-Zonen-Rasters (Zuordnung `1`–`9` zu Feldbereichen für Angriff/Zielzonen) — die einzige
konkrete Zonengrafik im Handbuch betrifft ausschließlich die 5 Serve-Startzonen. Die
9-Zonen-Zuordnung aus `prompt - erklärung.md` (Netzreihe 4-3-2 / Mitte 7-8-9 / Grundlinie
5-6-1, gegnerische Seite gespiegelt) ist **plausibel und konsistent** mit der Serve-Regel
(Zone `1`/`6`/`5` = Grundlinie, in derselben Reihenfolge rechts-Mitte-links), aber **nicht
durch eine Handbuch-Grafik für die übrigen Skills verifiziert** — siehe offene Frage in
Abschnitt 6.

**Koordinatenfelder (`sp_start_coordinate`, `sp_mid_coordinate`, `sp_end_coordinate`,
Positionen 4–6 in `3scout.json`)**: Diese sind **zusätzlich** zum Zonensystem vorhanden und
stammen aus der maus-basierten Trajektorien-Eingabe im „Rotation and direction"-Fenster
(DataVolleyMedia-Handbook 3.5.2, S. 43–44: „click end points", bei gedrückter Ctrl-Taste ein
dritter Punkt für die Ablenkung/„deflection"). Die konkrete Wertespanne/Auflösung dieser
Koordinaten ist nicht dokumentiert — offene Frage.

### 3.5 Automatik-Codes (vom Programm selbst erzeugt, DataVolleyMedia-Handbook 3.5.1 / S. 41–42)

| Code | Bedeutung |
|---|---|
| `*zn` / `azn` | Position des Zuspielers (`n` = Rotationsposition 1–6) zum aktuellen Zeitpunkt, Heim (`*`) bzw. Gast (`a`) |
| `*p` / `ap` | Punktvergabe an Heim/Gast, gefolgt von `:` und dem Punktestand (z. B. `*p01:00`) — **verifiziert**: Trennzeichen im normalisierten Code ist `:`, nicht `.` (das `.` wird nur bei manueller Eingabe im Command-Window verwendet, z. B. `C6.7`) |
| `*P` / `aP` | Wechsel des Zuspielers (Setter-Substitution), gefolgt vom neuen Zuspieler (z. B. bei Doppelwechsel) |
| `*c` / `ac` | Spielerwechsel, Format `<raus>:<rein>` (verifiziert: `*c02:10` = Spieler 2 raus, Spieler 10 rein) |
| `*T` / `aT` | Auszeit Heim/Gast |
| Grüne Codes: `*$$&<Typ><Bewertung>` / `a$$&<Typ><Bewertung>` | Punktgewinn/-verlust ohne zuordenbaren Skill/Spieler (z. B. wenn der Gegner nach einem gegnerischen Angriffspunkt keinen eigenen Aktionscode benötigt). Verifiziert: `a$$&H#` (Gastteam gewinnt Punkt „perfekt" nach Aktion des Heimteams) |
| `>LUp` (Suffix) | Kennzeichnet Codes, die aus dem LINEUP-Kommando (Start-Sechs-Eingabe) stammen (verifiziert: `*z1>LUp`, `*P02>LUp`) |
| `**Nset` | Satzende-Marker, `N` = Satznummer (verifiziert exakt wie im Handbuch beschrieben: `**1set`, `**2set`, …) |

### 3.6 Sonder-/Platzhaltercodes

- `a$$` / `*$$` — Platzhalter für „Spieler nicht sicher zugeordnet" (z. B. bei schneller
  Aktion, die für die spätere Video-Synchronisation zunächst nur zeitlich markiert wird). Aus
  `prompt - erklärung.md` übernommen und durch reale Daten (`a$$&H#`, s. o.) bestätigt — dort
  allerdings im Kontext der automatisch generierten „grünen Codes" (Abschnitt 3.5), nicht als
  eigenständiger manuell eingegebener Skill-Code. **Ob `a$$` auch als Platzhalter innerhalb
  eines regulären Skill-Codes (z. B. `a$$AH+`) vorkommen kann, ist anhand der Stichprobe
  nicht verifiziert** — offene Frage.

### 3.7 Compound Code (Dot-Coding)

Zur Beschleunigung der Eingabe können zwei fachlich korrelierte Codes (Serve↔Reception,
Attack↔Block, Attack↔Dig) mit einem Punkt (`.`) verkürzt kombiniert eingegeben werden, z. B.
`5SQ+15 a3RQ-15` → `5SQ+1.3-5` (Beispiel aus DataVolleyMedia-Handbook 6.3, S. 70). Der
Compound Code wird beim Speichern **immer in zwei separate normalisierte Codes** zerlegt
(DataVolleyMedia-Handbook 3.5.1: „The Compound Codes are always normalized in two separate
codes, with complementary effects"). Für den Parser ist das **nicht relevant**, da in der
gespeicherten `.dvw`-Datei ohnehin nur die bereits normalisierten Einzelcodes stehen — Dot
Coding ist reine Eingabe-Abkürzung der Anwendungssoftware, keine Persistenzform.

---

## 4. Regelwerk (parsing-relevant, knapp)

- **Rally-Point-System**: Standard-Modus (DataVolleyMedia-Handbook 2.5.4 „Regulation"). Ein
  Satz endet bei ≥ 25 Punkten (Sätze 1–4) bzw. ≥ 15 Punkten (Satz 5, Tie-Break) mit
  mindestens 2 Punkten Vorsprung — konfigurierbar (Standard-Werte editierbar, siehe
  Regulation-Fenster S. 21/46f.). Beach Volleyball abweichend: 2 Spieler, 3 Sätze, erste 2
  Sätze bis 21, dritter Satz bis 15.
- **Rotation**: 6 Positionen (Zonen 1–6) im Standard-Indoor-Regelwerk, gegen den Uhrzeigersinn
  rotierend bei jedem Side-Out (verifiziert an `az6`/`*z6`-Automatikcodes, die bei jedem
  Team-Rotationsvorgang die Spielerpositionen zyklisch verschieben, siehe
  Beispielzeilen Abschnitt 2.12).
  Standard-Rotationsreihenfolge 1-2-3-4-5-6 (DVWin2007-Handbook S. 30, „normal volley ball
  rotation system").
  Bei Side-Out (Wechsel des Aufschlagrechts) rotiert **nur das aufschlagberechtigte Team** um
  eine Position weiter.
- **Satz-Seitenwechsel**: Nach jedem Satz sowie im 5. Satz bei 8 Punkten der führenden
  Mannschaft Feldseitenwechsel (`INV`-Kommando, DataVolleyMedia-Handbook 3.6 „Command
  Window").
  Der Regulation-Reiter bietet dafür eine Option „Invert court automatically at point 8 of
  Set 5".
  **Achtung für den Parser**: Der Seitenwechsel betrifft nur die Bildschirmdarstellung
  (Court-Orientierung), nicht die Team-Zuordnung in den Datenzeilen (`*`/`a` bleiben stabil
  Heim/Gast über das gesamte Spiel).
- **Libero**: nimmt nicht an der regulären Rotation für Aufschlag/Angriff-vorne teil, wird im
  Datenmodell über `sp_special_role = L` markiert; eigene Ein-/Auswechsel-Regel (nicht über
  reguläre Substitutions-Codes `*c`/`ac`, sondern automatisch bei Positionswechsel des
  Liberos in/aus der Hinterfeld-Position — im Handbuch nicht als eigener Scout-Code
  dokumentiert; die Libero-Handhabung im rohen `.dvw` ist nicht abschließend geklärt, siehe
  Abschnitt 6).
- **Auszeiten/Wechsel**: pro Satz maximal konfigurierbare Anzahl (Standard-Indoor: 6
  Wechsel pro Satz laut Regulation-Fenster, DataVolleyMedia-Handbook S. 21).

---

## 5. Unterschiede/Historie gegenüber DVWin2007

Beide Handbücher beschreiben inhaltlich (Scout-Code-Syntax, Sektions-Workflow) **fast
identische** Software — DataVolleyMedia (Release 4.x, 2024) ist der direkte Nachfolger von
Data Volley 2007 Media (Release 3.x). Für Parsing/Kompatibilität relevante Unterschiede, die
DVWin2007-Handbook Abschnitt 1.7 „Introduction to the changes" explizit als **Neuerung ab
2007 gegenüber der noch älteren Vorgängerversion** (vor 2007, dort nur „previous version"
genannt) beschreibt:

1. **Spielernummerierung / Team-Präfix (DVWin2007-Handbook S. 11 und S. 27, „Users of the
   previous version, please note")**: Ab Data Volley 2007 werden Spielernummern `0`–`99` für
   beide Teams gleich vergeben, unterschieden durch das Präfix `*` (Heim) / `a` (Gast). **In
   der Version vor 2007** mussten Gastteam-Nummern stattdessen **um 50 erhöht** werden (kein
   Präfix-Zeichen). Dateien aus dieser Vor-2007-Ära (falls sie je im Datenbestand auftauchen
   sollten) würden vom heutigen Parser-Modell (Präfix-basiert) falsch interpretiert — in den
   für dieses Projekt vorliegenden Beispieldateien (2009–2010, `FILEFORMAT: 2.0`) ist bereits
   durchgehend das Präfix-Schema (`*`/`a`) im Einsatz, betrifft also unser Test-/Produktivmaterial nicht.
2. **Internationalisierung der Codes (DVWin2007-Handbook S. 11)**: Ab 2007 sind alle
   Scout-Codes einheitlich Englisch (zuvor ggf. lokalisiert/übersetzt) — für unseren Parser
   nicht relevant, da alle vorliegenden/zukünftigen Dateien bereits die englische Codebasis
   verwenden.
3. **Neue Skill-/Typ-Codes (DVWin2007-Handbook S. 11)**: Free-Ball-Skill (`F`) sowie die
   Ball-Typen „Super" (`U`) und „Quick" (`Q`) wurden mit der 2007-Version eingeführt; der
   Balltyp „L" (Backrow-Attack) wurde entfernt, da diese Information seither automatisch aus
   der Spielerposition auf dem Feld abgeleitet wird, statt explizit codiert zu werden.
4. **Encoding**: DataVolleyMedia (DV4) verwendet intern Unicode für Notizen/Team-/
   Spielernamen; Data Volley 2007 und ältere Versionen (inkl. „Click & Scout", „Data Video
   2007") verwenden die Codepage der Windows-Installation. Ein „Compatibility"-Setting im DV4
   erlaubt die explizite Wahl der Codepage beim Einlesen älterer Dateien mit
   Nicht-Latin-Zeichen (DataVolleyMedia-Handbook 5.4, S. 61).
5. **Scout-Code-Syntax selbst** (Main/Advanced/Extended Code, Skill-/Typ-/Bewertungstabellen,
   Zonensystem, Compound Code): **inhaltlich identisch** zwischen beiden Handbüchern (Wort-
   für-Wort dieselben Tabellen in DataVolleyMedia-Handbook S. 26–32 und DVWin2007-Handbook S.
   19–25) — keine Änderung zu beachten.
6. **UI-/Workflow-Änderungen** (Startbildschirm, Fenster-Layout, Media-Plugin-Integration,
   Rosters-Validation-Wizard, Attack-by-Cones statt Zonen in der Professional-Version) sind
   für das reine Dateiformat **nicht relevant**, da sie ausschließlich die Erfassungs-Software
   betreffen, nicht die gespeicherten `.dvw`-Inhalte.

---

## 6. Offene Fragen / zu verifizieren beim Parser-Bau (Version 1.1)

Diese Punkte sind durch keines der beiden Handbücher (reine Anwender-/UI-Dokumentation ohne
Datei-Spezifikation) eindeutig geklärt. Vor dem produktiven Parser-Ausbau empfiehlt sich eine
Verifikation anhand einer **größeren und diverseren Stichprobe** realer `.dvw`-Dateien aus
`../volleyscout_2/scoutdata/` (unterschiedliche Software-Versionen/`GENERATOR-REL`,
unterschiedliche Vereine/Ligen) sowie ggf. Abgleich mit öffentlich dokumentierten
Open-Source-Parsern (z. B. R-Paket `datavolley`, Python-Paket `py-datavolley`), die dieses
Format bereits produktiv parsen.

1. **`[3MATCH]` Feld 5/6** (`sp_home_away`, `sp_day_number`): beobachtete reale Werte
   (`Zuhause`, `So`) passen nicht sauber zu den im Handbuch gezeigten Match-notes-Feldern.
   Mögliche Fehlbenennung im bestehenden `protocol/3match.json` — mit mehreren Dateien
   gegenprüfen, ggf. Feldnamen korrigieren.
2. **`[3MATCH]` zweite Zeile** (Beispiel: `;;40468;`): Struktur/Bedeutung komplett offen, nicht
   in `protocol/3match.json` erfasst.
3. **`[3MORE]` zweite Zeile** (Beispiel: `;0;0;`): Bedeutung offen.
4. **`[3SET]` Feld 0** (`sp_played`): Verdacht, dass es eher „Rally-Point-System aktiv" als
   „Satz wurde gespielt" bedeutet — mit Dateien gegenprüfen, die nachweislich mit altem
   Sideout-Zählsystem gescoutet wurden (bzw. mit unvollständigen/abgebrochenen Sätzen).
5. **`[3PLAYERS-H/-V]` Felder 0, 2, 13, 15–17**: `sp_unknown_0` (Team-Flag, wahrscheinlich
   redundant), `sp_unknown_2` (laufender Index, Zählweise unklar), `sp_role`-Enum (welche
   Zahl = welche Position: Zuspieler/Außen/Mitte/Dia/Libero?), sowie drei durchgehend leere
   Felder am Zeilenende — Bedeutung/Wertebereich unklar.
6. **`[3SCOUT]` Felder 1/2** (`sp_point_phase`, `sp_attack_phase`): beobachtete Kleinbuchstaben
   `s`/`r`/`p`, primär (aber nicht ausschließlich) bei Angriffscodes gefüllt — exakte
   Bedeutung und vollständige Werteliste nicht gesichert. Vermutung: Kennzeichnung von
   Rally-Phase (Breakpoint/Sideout) bzw. Angriffs-Phase (Erstangriff nach Annahme/Transition/
   Pipe) — vor Nutzung im Statistik-Modul verifizieren.
7. **`[3SCOUT]` Feld 0 Padding-Regel**: die in Abschnitt 2.12 rekonstruierte
   Tilde-Padding-Logik wurde nur an wenigen Beispielzeilen verifiziert (Attack, Block). Für
   Serve/Reception/Dig/Set/Free-Ball sowie für Fälle mit Feldern 14 (Players) und 15
   (Special) befüllt sollte die Regel an weiteren Beispielen bestätigt werden, bevor sich der
   Parser darauf verlässt (Alternative: Feld 0 grundsätzlich zeichenweise anhand der
   Code-Syntax-Tabelle parsen und dabei `~` konsequent als „leer" interpretieren, unabhängig
   von der genauen Padding-Regel).
8. **Koordinatenfelder** (`sp_start_coordinate`, `sp_mid_coordinate`, `sp_end_coordinate`):
   Wertebereich/Auflösung/Ursprung (0/0 = welche Ecke des Feldes?) nicht dokumentiert.
9. ~~**9-Zonen-Grafik für Nicht-Serve-Skills**~~ **Gelöst (2026-07-30)**: keine
   Handbuch-Grafik vorhanden, aber die Zuordnung (Netz 4-3-2 / Mitte 7-8-9 /
   Grundlinie 5-6-1, Gegenseite exakt punktgespiegelt) ist unabhängig gegen den
   Quellcode von `openvolley/datavolley` (R-Paket, Funktion `dv_xy()`,
   `R/plot.R`) verifiziert — deckt sich exakt mit der hier übernommenen
   Zuordnung. Ebenso die Subzonen-Eckzuordnung (A unten-rechts, dann gegen den
   Uhrzeigersinn B/C/D), zusätzlich durch einen zweiten unabhängigen Community-
   Quellenfund bestätigt. Details: `../recherche/Data_Volley_4_Funktionsanalyse.md`
   Abschnitt 3.2. Umgesetzt in `backend/app/dvw/parser.py`, `backend/app/engine/
   scout_code.py` und `frontend/src/components/VolleyballCourt.vue`.
10. **`[3ATTACKCOMBINATION]` / `[3SETTERCALL]` Spaltenlayout**: nur aus UI-Screenshots grob
    abgeleitet, nicht anhand einer real befüllten `[3SETTERCALL]`-Sektion verifiziert (in
    beiden Stichprobendateien leer).
11. **`[3WINNINGSYMBOLS]`-Zeile**: exakte Segmentierung in Skill-Blöcke nicht verifiziert.
12. **`[3RESERVE]`**: Zweck komplett unbekannt.
13. **Libero-Sonderbehandlung im `[3SCOUT]`-Strom**: nicht dokumentiert, ob/wie
    Libero-Ein-/Auswechslungen einen eigenen Code-Typ erzeugen oder ob sie wie normale `*c`/
    `ac`-Substitutionen behandelt werden.
14. **`a$$`/`*$$` als Bestandteil regulärer Skill-Codes** (nicht nur als „grüner Code"):
    anhand der Stichprobe nicht beobachtet, laut `prompt - erklärung.md` aber als generelles
    Konzept beschrieben — mit weiteren Dateien prüfen.
15. **Encoding-Erkennung**: aktuelle Annahme (Latin-1/CP1252 als Default, siehe Abschnitt 1)
    sollte für Dateien aus DataVolleyMedia (DV4, ggf. UTF-8/Unicode-basiert) gegengeprüft
    werden, sobald reale DV4-Exportdateien verfügbar sind — die für dieses Dokument
    untersuchten Beispieldateien stammen alle aus der DV3.x-Ära (`GENERATOR-REL: Release
    3.2.7` / `3.2009.3`).
