# Deployment auf der Synology — Schritt-für-Schritt

Ziel: die App läuft auf der NAS und ist unter **https://volleyball.absosol.myds.me**
erreichbar. Die Container kommen fertig gebaut aus der GitHub-Registry (GHCR),
die Datenbank ist die MariaDB der Synology (Schema ist dort bereits eingespielt).

```
Browser ──HTTPS──► DSM Reverse Proxy (volleyball.absosol.myds.me)
                        │ HTTP
                        ▼
                  frontend-Container (nginx, Port 8080)
                        │ /api
                        ▼
                  backend-Container (FastAPI, intern)
                        │ mysql 3307
                        ▼
                  MariaDB der Synology (DB "volleyball")
```

## Voraussetzungen

- DSM 7.2+ mit installiertem Paket **Container Manager**.
- MariaDB-Paket läuft, DB `volleyball` + User `volleyball_database` existieren
  (✅ erledigt, Schema per Alembic eingespielt am 2026-07-27).
- DDNS `absosol.myds.me` aktiv; Router leitet Port 443 auf die NAS weiter
  (besteht i. d. R. schon für DSM/andere Dienste).
- Die GitHub-Action „Build & Push Container Images" ist auf `master` durchgelaufen
  (GitHub → Repo → Actions) — sie baut `…-backend` und `…-frontend` für
  amd64 + arm64.

## Schritt 1 — Einmalig: GHCR-Images öffentlich schalten

Die Images liegen unter `ghcr.io/absosol-public/sport_absosol_volleyball_scout-{backend,frontend}`.
GitHub legt Packages standardmäßig **privat** an, auch bei öffentlichen Repos:

1. github.com → Organisation `ABSoSol-public` → **Packages** →
   `sport_absosol_volleyball_scout-backend` → **Package settings** →
   Danger Zone → **Change visibility** → *Public*.
2. Dasselbe für `…-frontend`.

(Alternative, falls die Images privat bleiben sollen: auf der NAS einmalig per
SSH `docker login ghcr.io -u <github-user>` mit einem PAT mit `read:packages`.)

## Schritt 2 — Projektordner auf der NAS anlegen

1. **File Station**: Ordner anlegen, z. B. `docker/volleyball`
   (→ `/volume1/docker/volleyball`).
2. Zwei Dateien dorthin hochladen:
   - `docker-compose.synology.yml` (aus dem Repo)
   - `.env` — **nicht** die aus dem Repo-Root kopieren müssen: es reichen die
     Synology-Zeilen. Minimal:

     ```ini
     SYNOLOGY_DB_HOST=<siehe Hinweis unten>
     SYNOLOGY_DB_PORT=3307
     SYNOLOGY_DB_NAME=volleyball
     SYNOLOGY_DB_USER=volleyball_database
     SYNOLOGY_DB_PASSWORD=!!!VolleyBall2026!!!
     FRONTEND_PORT=8080
     ```

> **Hinweis `SYNOLOGY_DB_HOST`:** Der Backend-Container läuft auf derselben NAS
> wie die MariaDB. `absosol.myds.me` funktioniert nur, wenn der Router
> „Hairpin NAT" beherrscht. Robuster ist die **LAN-IP der NAS** (z. B.
> `192.168.1.x`) oder — da MariaDB auf allen Interfaces lauscht — die
> Docker-Bridge-Gateway-Adresse `172.17.0.1`. Im Zweifel zuerst mit der LAN-IP
> testen.

## Schritt 3 — Projekt im Container Manager anlegen

1. **Container Manager** → **Projekt** → **Erstellen**.
2. Projektname: `volleyball`, Pfad: `docker/volleyball`,
   Quelle: *docker-compose.yml erstellen → vorhandene auswählen* →
   `docker-compose.synology.yml`.
3. Weiter → Erstellen. Der Container Manager zieht die Images und startet beide
   Container. (Die `.env` im selben Ordner wird automatisch eingelesen.)

Alternative per SSH:

```bash
cd /volume1/docker/volleyball
sudo docker compose -f docker-compose.synology.yml up -d
```

## Schritt 4 — Interner Funktionstest (vor dem Reverse Proxy)

Im LAN-Browser: `http://<NAS-IP>:8080` → die App muss laden;
`http://<NAS-IP>:8080/health` → `{"status":"ok"}`.

Der Backend-Container führt beim Start automatisch `alembic upgrade head` aus —
bei künftigen Updates ziehen Migrationen also von selbst nach. Logs bei
Problemen: Container Manager → Container → `volleyball-backend-1` → Protokoll
(typisch: DB-Host nicht erreichbar → Schritt-2-Hinweis).

## Schritt 5 — Reverse Proxy für volleyball.absosol.myds.me

DSM → **Systemsteuerung** → **Anmeldeportal** → **Erweitert** → **Reverse Proxy**
→ **Erstellen**:

| Feld | Wert |
|---|---|
| Beschreibung | `volleyball` |
| Quelle: Protokoll | HTTPS |
| Quelle: Hostname | `volleyball.absosol.myds.me` |
| Quelle: Port | 443 |
| Ziel: Protokoll | HTTP |
| Ziel: Hostname | `localhost` |
| Ziel: Port | `8080` (= `FRONTEND_PORT`) |

Unter *Benutzerdefinierte Kopfzeile* → **Erstellen → WebSocket** die beiden
Header hinzufügen (schadet nicht und ist für spätere Live-Updates nötig).

> **DNS:** Subdomains von Synology-DDNS (`*.absosol.myds.me`) zeigen automatisch
> auf dieselbe IP. Test: `nslookup volleyball.absosol.myds.me` muss die gleiche
> Adresse liefern wie `absosol.myds.me`.

## Schritt 6 — Zertifikat (Let's Encrypt)

DSM → **Systemsteuerung** → **Sicherheit** → **Zertifikat** → **Hinzufügen**:

1. *Neues Zertifikat hinzufügen* → *Zertifikat von Let's Encrypt abrufen*.
2. Domainname: `absosol.myds.me`, **Alternativer Name (SAN)**:
   `volleyball.absosol.myds.me` — oder direkt ein Wildcard-Zertifikat
   `*.absosol.myds.me` (bei Synology-DDNS möglich, DSM erledigt die
   DNS-Challenge selbst).
3. Danach unter **Zertifikat → Einstellungen** dem Eintrag
   `volleyball.absosol.myds.me` (Reverse-Proxy-Endpoint) das neue Zertifikat
   zuweisen.

## Schritt 7 — End-to-End-Verifikation

1. `https://volleyball.absosol.myds.me` → App lädt (gültiges Schloss-Symbol).
2. `https://volleyball.absosol.myds.me/health` → `{"status":"ok"}`.
3. Team anlegen (Teams → Neues Team) → erscheint es, schreibt die App
   nachweislich in die Synology-MariaDB.
4. Gegenprobe DB: phpMyAdmin oder SSH →
   `SELECT * FROM volleyball.teams;` zeigt das Team.

## Updates einspielen

1. Änderungen auf `master` pushen → GitHub-Action baut neue `latest`-Images.
2. Container Manager → Projekt `volleyball` → **Aktion** → **Bereinigen** ist
   nicht nötig; **Erstellen/Neu erstellen** mit „Image neu abrufen" genügt.
   Per SSH: `sudo docker compose -f docker-compose.synology.yml pull && sudo
   docker compose -f docker-compose.synology.yml up -d`.
3. Migrationen laufen beim Backend-Start automatisch.

## Troubleshooting

| Symptom | Ursache/Lösung |
|---|---|
| Backend-Log: „Datenbank nicht erreichbar" | `SYNOLOGY_DB_HOST` prüfen (LAN-IP statt DDNS-Name, Hairpin-NAT), Port 3307, MariaDB-Paket läuft? |
| `502 Bad Gateway` unter der Domain | Frontend-Container läuft nicht oder Ziel-Port im Reverse Proxy ≠ `FRONTEND_PORT` |
| Zertifikatswarnung | Zertifikat nicht dem Reverse-Proxy-Endpoint zugewiesen (Schritt 6.3) |
| Domain löst nicht auf | DDNS prüfen: `nslookup volleyball.absosol.myds.me`; ggf. DDNS-Eintrag in DSM neu speichern |
| `docker compose pull` → „denied" | GHCR-Packages noch privat (Schritt 1) |
