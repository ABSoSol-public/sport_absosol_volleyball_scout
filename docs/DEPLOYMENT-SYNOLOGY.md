# Deployment auf der Synology

Gleiches Muster wie beim `yugioh_database`-Projekt (TCG Collection Manager):
**Quellcode auf die NAS, dort bauen und starten** — keine Registry, keine
fertigen Images. Eine einzige `docker-compose.yml`, Konfiguration über `.env`.

Ziel: die App läuft auf der NAS und ist unter **https://volleyball.<ddns-domain>.myds.me**
erreichbar (Subdomain-Muster, siehe Abschnitt 7 — die tcg-App bleibt parallel
unter ihrer eigenen Adresse erreichbar).

```
Browser ──HTTPS:443──► Router ──8443──► DSM Reverse Proxy (volleyball.<ddns-domain>.myds.me)
                                             │ HTTP
                                             ▼
                                       frontend-Container (feste IP 172.29.0.10:80)
                                             │ /api (Docker-Netz volleynet)
                                             ▼
                                       backend-Container (FastAPI)
                                             │ mysql 3307
                                             ▼
                                       MariaDB der Synology (DB "volleyball")
```

Voraussetzungen: DSM mit Container Manager, laufende MariaDB
(✅ DB `volleyball` + User `volleyball_database` existieren, Schema per Alembic
eingespielt am 2026-07-27), SSH-Zugang.

## 1. Datenbank vorbereiten

**Bereits erledigt** — DB `volleyball`, User `volleyball_database`, Schema liegt
drin (7 Tabellen + `alembic_version`). Nichts zu tun.

## 2. Projekt auf die Synology bringen

Anders als beim tcg-Projekt (damals ohne Git-Remote → `tar` über SSH) hat dieses
Repo ein öffentliches GitHub-Remote — der in der tcg-Doku als „vorzuziehen"
beschriebene Weg funktioniert hier direkt:

```bash
ssh admin@<synology-lan-ip>
mkdir -p /volume1/docker && cd /volume1/docker
git clone https://github.com/ABSoSol-public/sport_absosol_volleyball_scout.git volleyball
cd volleyball
```

(Falls `git` auf der NAS fehlt: Paket **Git Server** installieren — es bringt das
`git`-CLI mit. Alternativ der `tar`-über-SSH-Weg aus der tcg-Doku; `rsync` über
SSH blockiert DSM, bekannter Stolperstein von dort.)

## 3. Konfiguration

```bash
cp .env.example .env
nano .env
```

Wichtige Werte:

```ini
SYNOLOGY_DB_HOST=<LAN-IP der Synology>   # NICHT localhost, NICHT die DDNS-Adresse!
SYNOLOGY_DB_PORT=3307
SYNOLOGY_DB_NAME=volleyball
SYNOLOGY_DB_USER=volleyball_database
SYNOLOGY_DB_PASSWORD=<das Passwort>
FRONTEND_PORT=8081                        # 8080 ist auf der NAS schon vom tcg-Projekt belegt!
VOLLEYSCOUT_SECRET_KEY=<openssl rand -hex 32>   # Pflicht — signiert die Login-Sessions
VOLLEYSCOUT_COOKIE_SECURE=true            # Login-Cookie nur über HTTPS ausliefern
```

- **`SYNOLOGY_DB_HOST`**: MariaDB läuft als Synology-Paket, nicht im
  Compose-Netz. `localhost` zeigt im Container auf sich selbst; die DDNS-Adresse
  scheitert je nach Router am NAT-Loopback. → LAN-IP der NAS (gleiche Erkenntnis
  wie `DB_HOST` in der tcg-Doku).
- **`FRONTEND_PORT=8081`**: Host-Port des Frontends. 8080 ist auf dieser NAS
  bereits vom tcg-Projekt belegt.

## 4. Container bauen und starten

**Synology-Besonderheiten** (aus dem tcg-Projekt übernommen, dort getestet):
Docker-Befehle brauchen `sudo`; je nach DSM-Stand gibt es nur das eigenständige
`docker-compose` (Bindestrich) unter `/usr/local/bin/docker-compose`, nicht das
`docker compose`-Subcommand.

```bash
cd /volume1/docker/volleyball
sudo /usr/local/bin/docker-compose --env-file .env up -d --build
```

Alternativ per GUI: Container Manager → Projekt → Erstellen → Pfad
`/volume1/docker/volleyball` → vorhandene `docker-compose.yml` auswählen.

Der Backend-Container wartet beim Start auf die DB und führt automatisch
`alembic upgrade head` aus — Migrationen ziehen bei jedem Update von selbst nach.

## 5. Status prüfen

```bash
sudo /usr/local/bin/docker-compose ps
sudo /usr/local/bin/docker-compose logs -f backend
curl http://localhost:8081/health        # {"status":"ok"}
```

App im LAN-Browser: `http://<synology-lan-ip>:8081` → Team anlegen →
erscheint es, schreibt die App nachweislich in die MariaDB.

## 6. HTTPS + Subdomain (DSM-Reverse-Proxy)

Exakt das Subdomain-Muster aus der tcg-Doku (dort Abschnitt 11). Der Router
leitet extern **443 → intern 8443** bereits für das tcg-Projekt weiter — diese
eine Weiterleitung gilt für **alle** Subdomains gemeinsam, hier ist also nichts
Neues am Router zu tun.

1. **Zertifikat**: Systemsteuerung → Sicherheit → Zertifikat → Hinzufügen →
   „Zertifikat von Let's Encrypt holen" → Domainname:
   `volleyball.<ddns-domain>.myds.me`. (Synology-DDNS löst `*.<ddns-domain>.myds.me`
   automatisch auf die NAS auf, keine extra DNS-Konfiguration nötig.)
2. **Reverse Proxy**: Systemsteuerung → Anmeldeportal → Erweitert →
   Reverse Proxy → Erstellen:

   | Feld | Wert |
   |---|---|
   | Beschreibung | `volleyball` |
   | Quelle: Protokoll | HTTPS |
   | Quelle: Hostname | `volleyball.<ddns-domain>.myds.me` |
   | Quelle: Port | **8443** (nicht 443 — DSMs eigenes Portal schluckt sonst die Regel) |
   | Ziel: Protokoll | HTTP |
   | Ziel: Hostname | **`172.29.0.10`** (feste Container-IP, nicht `localhost`, nicht LAN-IP:8081) |
   | Ziel: Port | **80** (Container-intern, nicht `FRONTEND_PORT`) |

3. **Zertifikat zuweisen**: Systemsteuerung → Sicherheit → Zertifikat →
   Einstellungen → den neuen Eintrag `volleyball.<ddns-domain>.myds.me` auf das
   Subdomain-Zertifikat aus Schritt 1 stellen.

**Warum feste Container-IP als Ziel?** Erfahrungswerte aus dem tcg-Projekt:
`localhost` erreicht Container aus DSMs nginx nicht zuverlässig, und der Weg
über LAN-IP + veröffentlichten Port lief nach einem DSM-Update intermittierend
in `INTERNAL_ERROR`-Abbrüche. Die feste IP im eigenen Docker-Netz
(`volleynet`/172.29.0.10 — bewusst ein anderes Subnetz als `tcgnet`/172.28.0.10,
damit beide Stacks parallel laufen) umgeht beides.

## 6b. Login-Benutzer anlegen

Ohne Benutzer kommt niemand über den Login hinaus (bewusst keine Registrierung).
Auf der NAS im Projektordner:

```bash
sudo /usr/local/bin/docker-compose exec -T backend python -m app.cli create-user <name> <passwort> [admin|viewer]
```

(Oder von einem Rechner mit laufendem lokalem Stack: `./create-user.sh …` —
beide schreiben in dieselbe Synology-DB.) Erneuter Aufruf mit gleichem Namen
setzt das Passwort neu; `viewer` = Nur-Lese-Zugriff.

> Hinweis bei `VOLLEYSCOUT_COOKIE_SECURE=true`: der Login funktioniert dann nur
> über HTTPS (also über die Domain), nicht mehr über `http://<NAS-IP>:8081` —
> das ist Absicht (kein Klartext-Login im LAN), zum Debuggen notfalls kurzzeitig
> auf `false` stellen und neu starten.

## 7. End-to-End-Verifikation

1. `https://volleyball.<ddns-domain>.myds.me` → App lädt mit gültigem Zertifikat.
2. `https://volleyball.<ddns-domain>.myds.me/health` → `{"status":"ok"}`.
3. Team anlegen, Match anlegen, Satz starten, ein paar Rallys scouten, Undo —
   danach in der DB gegenprüfen: `SELECT * FROM volleyball.live_events;`

## Updates einspielen

```bash
ssh admin@<synology-lan-ip>
cd /volume1/docker/volleyball
git pull
sudo /usr/local/bin/docker-compose --env-file .env up -d --build
```

Migrationen laufen beim Backend-Neustart automatisch. Stolperstein aus der
tcg-Doku gilt auch hier: `--build` pullt Basis-Images (`python:3.13-slim`,
`node:22-alpine`, `nginx:1.27-alpine`) **nicht** neu — bei kryptischen
Build-Fehlern nach langer Zeit die Basis-Images einmal `sudo docker pull`-en
und mit `build --no-cache` neu bauen.

## Ports & Firewall

| Port | Zweck |
|---|---|
| 8081 (Host, `FRONTEND_PORT`) | Frontend / einziger veröffentlichter App-Port |
| 8000 (nur 127.0.0.1 der NAS) | Backend direkt, nur für Debugging |
| 3307 (Synology-MariaDB) | nur intern, niemals ins Internet weiterleiten |
| extern 443 → intern 8443 | bereits vorhanden (tcg), gilt für alle Subdomains |

## Troubleshooting

| Symptom | Ursache/Lösung |
|---|---|
| Backend-Log „Datenbank nicht erreichbar" | `SYNOLOGY_DB_HOST` = LAN-IP? Port 3307? MariaDB-Paket läuft? |
| Port-Konflikt beim Start | `FRONTEND_PORT` kollidiert (8080 = tcg) → 8081 gesetzt? |
| DSM-Login-Seite statt App unter der Domain | Reverse-Proxy-Quelle steht auf 443 statt **8443** |
| `502`/hängende Requests über die Domain | Reverse-Proxy-Ziel muss `172.29.0.10:80` sein (nicht localhost/LAN-IP) |
| Zertifikatswarnung | Zertifikat dem Eintrag `volleyball.<ddns-domain>.myds.me` zugewiesen (Schritt 6.3)? |
| `docker-compose: command not found` | Vollen Pfad nutzen: `/usr/local/bin/docker-compose`, mit `sudo` |
