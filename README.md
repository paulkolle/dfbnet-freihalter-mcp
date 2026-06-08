# DFBNet Freihalter MCP

Inoffizieller lokaler MCP-Server und CLI-Client zum Verwalten von Freihaltern im DFBNet SRIA-Schiedsrichterbereich.

> **Inoffiziell:** Dieses Projekt ist nicht mit DFB GmbH, DFBNet, dem DFB oder einem Landesverband verbunden, wird nicht von ihnen unterstützt und ist nicht offiziell dokumentiert. Nutze es nur mit deinem eigenen berechtigten DFBNet-Zugang, beachte die für dich geltenden Nutzungsbedingungen und vermeide unnötige oder massenhafte automatisierte Requests.

## Was kann das Tool?

- DFBNet-SRIA-Freihalter auflisten
- Konflikte für ein Zeitfenster prüfen
- ganztägige Freihalter erstellen
- mehrtägige Freihalter als **ein einziges Intervall** erstellen
- Freihalter per ID löschen
- lokale Dry-runs für Payloads und Delete-URLs ausgeben
- als MCP-Tool in Hermes Agent laufen
- Tokens lokal aus einer Playwright-Login-Session verwalten

## Warum ein lokaler MCP?

Der Server läuft lokal über stdio, nicht als öffentlicher HTTP-Service:

```text
Hermes Agent
  -> MCP JSON-RPC über stdin/stdout
  -> lokaler dfbnet-freihalter-mcp Prozess
  -> DFBNet API mit Bearer Token
```

Dadurch bleiben DFBNet-Sessiondaten lokal auf deinem Rechner. Es wird kein Port geöffnet und kein Reverse Proxy benötigt.

## Schnellstart

### 1. Repository klonen

```bash
git clone https://github.com/<owner>/dfbnet-freihalter-mcp.git
cd dfbnet-freihalter-mcp
```

### 2. `uv` prüfen oder installieren

Dieses Projekt nutzt [`uv`](https://docs.astral.sh/uv/) für Python-Abhängigkeiten und Kommandoausführung.

Prüfen:

```bash
uv --version
```

Falls `uv` fehlt:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Danach ggf. die Shell neu laden bzw. den im Installer angezeigten `source`-/`export PATH`-Hinweis ausführen.

Offizielle Installationsanleitung: https://docs.astral.sh/uv/getting-started/installation/

### 3. Abhängigkeiten installieren

```bash
uv sync
uv run playwright install chromium
```

Auf Debian/Ubuntu ggf. zusätzlich:

```bash
uv run playwright install-deps chromium
```

### 4. Env-Datei anlegen

```bash
cp .env.example ~/.dfbnet_env
chmod 600 ~/.dfbnet_env
```

Dann `~/.dfbnet_env` bearbeiten:

```bash
DFBNET_REFEREE_ID=<deine-referee-id>
DFBNET_STORAGE_STATE=/absoluter/pfad/zum/repo/dfbnet_probe_out/storage_state.json
DFBNET_TOKEN_STATE=/absoluter/pfad/zum/repo/dfbnet_probe_out/token_state.json
DFBNET_TIMEZONE=Europe/Berlin
DFBNET_VERIFY_FROM=2025-07-01T00:00:00.000Z
```

Optional für Headless-Auto-Login:

```bash
DFBNET_LOGIN_ID=<dein-dfbnet-login>
DFBNET_PASSWORD=<dein-dfbnet-passwort>
```

Wenn du keine Passwörter in der Env-Datei speichern willst, nutze den manuellen Browser-Login im nächsten Schritt.

### 5. Token-State erzeugen

Manueller Login mit sichtbarem Browser:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run python scripts/dfbnet_login_probe.py \
  --out ./dfbnet_probe_out \
  --user-data-dir ./dfbnet_browser_profile
```

Im Browser bei DFBNet einloggen. Das Script schreibt danach u.a.:

```text
dfbnet_probe_out/token_state.json
dfbnet_probe_out/storage_state.json
```

Diese Dateien enthalten echte Sessiondaten und werden per `.gitignore` ausgeschlossen.

Headless-Auto-Login, falls `DFBNET_LOGIN_ID` und `DFBNET_PASSWORD` gesetzt sind:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run python scripts/dfbnet_login_probe.py \
  --headless \
  --out ./dfbnet_probe_out \
  --user-data-dir ./dfbnet_browser_profile
```

### 6. CLI testen

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run dfbnet-freihalter auth-status
```

Liste der Freihalter:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run dfbnet-freihalter list --from-iso '2025-07-01T00:00:00.000Z'
```

Dry-run für einen Tag:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run dfbnet-freihalter dry-run 2026-06-09
```

Dry-run für einen Zeitraum als ein Intervall:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run dfbnet-freihalter dry-run-range 2026-06-11 2026-06-13
```

Echten Zeitraum erstellen:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run dfbnet-freihalter create-range 2026-06-11 2026-06-13 --comment 'Urlaub'
```

Freihalter löschen:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run dfbnet-freihalter delete EXEMPTION_ID
```

## Hermes MCP einrichten

In `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  dfbnet_freihalter:
    command: "uv"
    args: ["run", "--project", "/absoluter/pfad/zum/dfbnet-freihalter-mcp", "dfbnet-freihalter-mcp"]
    timeout: 60
    connect_timeout: 30
    env:
      DFBNET_ENV_FILE: "/home/<user>/.dfbnet_env"
```

Test:

```bash
hermes mcp test dfbnet_freihalter
```

Erwartung:

```text
✓ Connected
✓ Tools discovered: 10
```

In einer laufenden Hermes-Session neu laden:

```text
/reload-mcp
```

Danach kann der Agent die Tools z.B. so nutzen:

```text
mcp_dfbnet_freihalter_create_date_range_exemption
mcp_dfbnet_freihalter_delete_exemption
```

## Verfügbare CLI-Kommandos

```bash
dfbnet-freihalter auth-status
dfbnet-freihalter list --from-iso '2025-07-01T00:00:00.000Z'
dfbnet-freihalter dry-run YYYY-MM-DD
dfbnet-freihalter dry-run-range YYYY-MM-DD YYYY-MM-DD
dfbnet-freihalter dry-run-delete EXEMPTION_ID
dfbnet-freihalter conflict YYYY-MM-DD
dfbnet-freihalter create-full-day YYYY-MM-DD [--comment TEXT]
dfbnet-freihalter create-range START_DATE END_DATE [--comment TEXT]
dfbnet-freihalter delete EXEMPTION_ID
```

Alle Kommandos akzeptieren optional:

```bash
--env-file /pfad/zur/env-datei
```

## Verfügbare MCP-Tools

Hermes registriert die Tools mit dem Prefix `mcp_dfbnet_freihalter_`:

- `auth_status`
- `dry_run_full_day_exemption`
- `dry_run_date_range_exemption`
- `dry_run_delete_exemption`
- `list_exemptions`
- `check_exemption_conflict`
- `create_full_day_exemption`
- `create_date_range_exemption`
- `delete_exemption`
- `create_exemption`

## Datumsmodell

Das Tool rechnet lokale ganztägige Freihalter in `Europe/Berlin` nach UTC um.

Beispiel 09.06.2026:

```text
lokal: 2026-06-09 00:00 bis 2026-06-09 23:59 Europe/Berlin
UTC:   2026-06-08T22:00:00.000Z bis 2026-06-09T21:59:00.000Z
```

Mehrtagige Freihalter werden nicht pro Tag geloopt, sondern als ein Intervall gesendet.

## Dokumentation

- `docs/SETUP.md` - ausführliche Einrichtung von Grund auf
- `docs/ARCHITECTURE.md` - Architektur, Auth-Fluss, API-Shape, Sicherheitsmodell
- `docs/PUBLISHING.md` - GitHub-Veröffentlichung und Secret-Check
- `SECURITY.md` - Umgang mit Tokens, Sessiondateien und Meldung von Sicherheitsproblemen

## Entwicklung

Tests:

```bash
uv run --extra dev pytest -q
```

Syntaxcheck:

```bash
uv run python -m py_compile dfbnet_freihalter_mcp/*.py scripts/dfbnet_login_probe.py
```

MCP-Discovery:

```bash
hermes mcp test dfbnet_freihalter
```

## Sicherheit

Nicht committen:

- `~/.dfbnet_env`
- `.env` / `.env.*`
- `dfbnet_probe_out/`
- `dfbnet_browser_profile/`
- `token_state.json`
- `storage_state.json`
- Browserprofile
- API-Probe-Logs mit echten Metadaten

Wenn ein Token oder Passwort versehentlich veröffentlicht wurde: DFBNet-Passwort ändern bzw. Session invalidieren und die Git-Historie bereinigen.

## Lizenz

MIT, siehe `LICENSE`.
