# Ablaufdiagramm (Gesamtübersicht Projektverlauf)

Stand: Version 2.6 (2026-08-09) — verdichtet aus `PROGRESS.md` (37 Session-Einträge),
siehe `docs/ROADMAP.md` für den vollständigen Versionsverlauf mit Details.

Zeigt den Gesamtablauf des Projekts von der ersten Bestandsaufnahme über den
Livegang auf der Synology bis zu den beiden parallel laufenden
Entwicklungssträngen (Analyse vs. Live-Scouting).

```mermaid
flowchart TD
    A["Projektstart 2026-07-27<br/>Bestandsaufnahme & Architekturentscheidung<br/>(Prototypen verworfen, alles neu)"] --> B["Version 1.0<br/>FastAPI + Vue 3 + MariaDB + Docker<br/>Event-Sourcing Match-Engine (live_events)"]
    B --> C["Doku & Absicherung<br/>MIT-Lizenz, ARCHITEKTUR/API/DATENBANK.md"]
    C --> D["Synology-DB angebunden<br/>(Session 6-7)"]
    D --> E["Deployment-Umbau auf yugioh-Muster<br/>Source-Build auf der NAS, festes Docker-Netz<br/>(Session 10-11)"]
    E --> F(("🚀 Livegang — Roadmap 1.9<br/>volleyball.absosol.myds.me<br/>(Session 12)"))
    F --> G["Version 2.0<br/>Login & Rollen (viewer / scout)"]
    G --> H{"Ab hier zwei parallele Stränge"}

    subgraph AN ["Analyse-Strang"]
        direction TB
        I1["2.1 DVW-Import<br/>Parser + Importer, 120 echte Dateien verifiziert"]
        I2["2.2 Statistik-Auswertung<br/>Spieler-/Team-Stats, Rotationsanalyse"]
        I3["2.3 Match-Browser<br/>+ Frontend-Politur (Bug-Fix Status-Routing)"]
        I1 --> I2 --> I3
    end

    subgraph LI ["Live-Strang"]
        direction TB
        J1["2.4 Kaderverwaltung<br/>& Zonen-/Richtungs-Helfer"]
        J2["2.5 Live-Scouting-UX<br/>Rotationsfeld, Aufstellungskorrektur,<br/>Klickpfad-Eingabe, Historylog, Compound-Codes"]
        J3["2.6 Zeitstempel + DVW-Export<br/>(Re-Export & Live-Export, Round-Trip getestet)"]
        J1 --> J2 --> J3
    end

    H --> I1
    H --> J1

    I3 --> K["Aktueller Stand:<br/>Version 2.6 ✅ (74/74 Tests grün)"]
    J3 --> K
    K --> L["Nächste geplante Version: 2.7 Betrieb<br/>DB-Backup, Batch-Import, Setter-Tracking,<br/>Angriff+Block/-Abwehr Compound-Codes"]

    style F fill:#b3202c,color:#fff
    style K fill:#1c2733,color:#fff
```
