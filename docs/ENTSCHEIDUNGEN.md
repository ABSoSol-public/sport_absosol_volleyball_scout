# Anforderungen & Entscheidungen (Session-Protokoll)

Chronologisches, öffentliches Protokoll: jede substantielle Nutzeranfrage an
eine KI-Session **wörtlich**, die daraus getroffene Entscheidung/Abgrenzung,
und wo sie umgesetzt/dokumentiert ist. Ziel: eine komplett neue Session (mit
Claude oder einem anderen KI-Tool) soll allein aus Repo + diesem Protokoll
nachvollziehen können, *warum* der Code so aussieht, wie er aussieht — nicht
nur *was* er tut (das steht in `docs/ARCHITEKTUR.md` & Co.).

Unabhängig von der privaten `docs/ROADMAP.md` (siehe `.gitignore`,
Nutzerentscheidung 2026-07-30 „nicht mehr öffentlich") — dieses Protokoll
beginnt bewusst neu und rührt die alte Datei nicht an. Rückwirkend erfasst:
die aktuelle Session (2026-09-26); alles davor ist nur noch über
`docs/ARCHITEKTUR.md`s verstreute „Nutzerwunsch"-/„Nutzerentscheidung"-Zitate
und die Commit-Historie rekonstruierbar.

**Konvention für neue Einträge**: wörtliches Zitat (keine Paraphrase — wenn
eine Anfrage über mehrere Nachrichten verteilt war, alle Teile zitieren),
kurz was entschieden/abgegrenzt wurde, Verweis auf Commit(s) + das Fach-Dokument
mit den Details. Wenn die KI selbst etwas vorschlägt und der Nutzer nur
zustimmt („weiter bitte", „ja"), das explizit so vermerken (siehe 2026-09-26,
Eintrag 3) — das ist ein wichtiger Unterschied für die Nachvollziehbarkeit.

---

## 2026-09-26

### 1. Auftrag zur Weiterentwicklung

> „bearbeite das ausgewählte repository selbstständig um einen "data volley"
> clone von "data project" am ende zu haben der in einem webbrowser läuft ...
> einiges geht schon aber sehr vieles auch nich nicht"

Kein konkretes Einzelfeature benannt — offener Auftrag, den größten
funktionalen Mangel selbst zu identifizieren. Nach Durchsicht von
`docs/ARCHITEKTUR.md` als größte Lücke identifiziert: live-gescoutete
Matches lieferten nie Statistik/Match-Browser-Daten (nur DVW-Importe taten
das) — der Live-Strang schrieb ausschließlich `live_events`, nie den
Analyse-Strang. Umgesetzt als `app/analyse_sync.py` (Roadmap 2.7 laut
bestehender Doku-Nomenklatur). Details: `docs/ARCHITEKTUR.md` Abschnitt
„Zusammenführung von Live- und Analyse-Strang". Commit `5b2eb55`.

Danach zwei Zwischenfragen des Nutzers ohne fachliche Konsequenz: „was ist
denn PR erstellen?" (Erklärung) und „nene gleich in master rein, fertig aus
:D" (explizite Anweisung, direkt auf `master` zu pushen statt einen Pull
Request zu erstellen — seither in dieser Session als Standardvorgehen
beibehalten, siehe `CLAUDE.md`).

### 2. Spielerprofile, Skill-Karte, Mehrfach-Formate

> „ja mach weiter und erweitere das projekt auch nach sinnvollen dingen ...
> das scouting tool soll auch nach dem vorbild von NFL ein spielerbasierendes
> playbook erstellen können (profiling von spielern über mehrere saisons) und
> wie bei fifa eine spieler fähigkeiten kachel erstellen ... mit bewertung
> über die komplette datenbank als referenz über alle spieler hinweg ... das
> muss dynamisch berechnet werden und mit daten natürlich angereichert
> werden ... die datenbank soll entsprechend dem kontext vollumfänglich
> verbessert und erweitert werden"

Mitten in der Bearbeitung dieser Anfrage traf eine zweite Nachricht ein, die
denselben Auftrag um eine Dimension erweiterte:

> „beachte das im volleyball auch spieler in verschiedenen standards spielen
> können (beach 2 vs 2, halle jugend 2 vs. 2, 3vs3 4vs4 6vs6 mit
> verschiedenen systemen: 5:1, 4:2 das beschreibt die zuspieler situation)
> nehm das mit auf recherchiere die systeme und bringe und dokumentiere das
> mit ein ... erweitere entsprechend das tool und dokumentiere alles sauber"

Beide zusammen führten zu vier Bausteinen (Reihenfolge der Umsetzung, nicht
der Anfrage — die Formate wurden zuerst gebaut, weil Spielerprofile sie als
Vergleichsdimension brauchen):
1. Mehrfach-Formate (Halle 6:6/4:4/3:3/2:2, Beach 2:2) + Zuspielsysteme
   (5-1/6-2/4-2/6-6) — recherchiert (FIVB-Regelwerk für Beach verifiziert,
   deutsche Jugend-Kleinfeldformen bewusst als „nicht bundeseinheitlich
   verifiziert" gekennzeichnet). Details + Quellen: `docs/SPIELFORMATE.md`.
   Commit `0861767`.
2. `Season`-Modell (1. Jul.–30. Jun.) als die „Datenbank vollumfänglich
   erweitern"-Vorgabe für die Mehrsaison-Profile.
3. Karriereprofil je Spieler (Team+Trikotnummer über alle Matches/Saisons).
4. FIFA-Style Skill-Karte (Perzentilrang gegen alle Spieler derselben
   Disziplin in der Datenbank, dynamisch berechnet, keine Note unter
   Mindeststichprobe) + NFL-Style Zonentendenzen („Playbook"-Äquivalent aus
   den ohnehin vorhandenen Zonendaten).
   Details + bewusste Lücken (kein Leaderboard, keine DV4-Noten):
   `docs/SPIELERPROFILE.md`. Commit `66e645e`.

### 3. Rückwechsel-Regel & Libero-Wechsel — Auswahl der KI, nicht des Nutzers

> „weiter bitte"

Keine fachliche Einzelanforderung — Zustimmung zu einem vom Assistenten
selbst vorgeschlagenen Themenkatalog (Rückwechsel-Regel, Libero-
Sonderregeln, Setter-Tracking, Spieler-Leaderboard). Der Assistent wählte
die ersten beiden aus, weil sie reale, in `docs/ARCHITEKTUR.md` seit
Projektbeginn als offen markierte Regellücken schließen (nicht, weil der
Nutzer sie benannt hätte). Recherchiert gegen FIVB-Regelwerk + weitere
Quellen. Details: `docs/ARCHITEKTUR.md` Abschnitt „Match-Engine". Commit
`f458625`.

### 4. Dieses Protokoll + CLAUDE.md

> „hast du alles ordentlich dokumentierst und ki anforderungen auch erfasst
> und dokmentiert? damit man das mit anderen ki tool oder mit dir in einer
> komplett neuen session vollständig reproduzieren kann?"

Bei der Selbstprüfung zwei Lücken gefunden und behoben (Commit `1416e55`):
`docs/SPIELFORMATE.md` hatte gar kein wörtliches Zitat, `docs/SPIELERPROFILE.md`s
war eine unvollständige Paraphrase. Strukturelle Lücke — `docs/ROADMAP.md`
wird im Code referenziert, ist aber nicht Teil des öffentlichen Repos, und es
gab keine `CLAUDE.md` — dem Nutzer zur Entscheidung vorgelegt (`AskUserQuestion`):
Ergebnis dieses Dokument (öffentliches Protokoll ab jetzt, rührt die private
ROADMAP.md nicht an) sowie `CLAUDE.md` im Repo-Root.
