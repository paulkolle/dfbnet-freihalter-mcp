# Einrichtung von Grund auf

Diese Anleitung führt Schritt für Schritt durch die komplette Einrichtung des inoffiziellen DFBNet Freihalter MCPs.

> Dieses Projekt ist inoffiziell. Nutze es nur mit deinem eigenen berechtigten DFBNet-Zugang und beachte die für dich geltenden Nutzungsbedingungen.

## 1. Voraussetzungen

Du brauchst:

- Python 3.11 oder neuer
- `uv`
- Playwright/Chromium
- einen DFBNet SRIA-Zugang
- optional: Hermes Agent, wenn du den MCP als Agent-Tool nutzen willst

Prüfen:

```bash
python3 --version
uv --version
```

Falls `uv` fehlt, installiere es über die offizielle Astral-Anleitung:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Danach ggf. die Shell neu laden oder den angezeigten `source`-/`export PATH`-Hinweis ausführen und erneut prüfen:

```bash
uv --version
```

Offizielle Dokumentation: https://docs.astral.sh/uv/getting-started/installation/

Alternative Installationswege, z.B. Homebrew, pipx oder Windows, stehen ebenfalls dort.

## 2. Repository klonen

```bash
git clone https://github.com/<owner>/dfbnet-freihalter-mcp.git
cd dfbnet-freihalter-mcp
```

Wenn du den Code nur lokal nutzt, ist auch ein beliebiger anderer Pfad möglich. Wichtig ist später nur, dass du in der Hermes-Konfiguration den absoluten Projektpfad verwendest.

## 3. Python-Abhängigkeiten installieren

```bash
uv sync
```

Playwright-Browser installieren:

```bash
uv run playwright install chromium
```

Auf Debian/Ubuntu kann zusätzlich nötig sein:

```bash
uv run playwright install-deps chromium
```

## 4. Lokale Env-Datei anlegen

Kopiere die Beispielkonfiguration:

```bash
cp .env.example ~/.dfbnet_env
chmod 600 ~/.dfbnet_env
```

Öffne `~/.dfbnet_env` und passe die Werte an:

```bash
DFBNET_REFEREE_ID=<deine-referee-id>
DFBNET_STORAGE_STATE=/absoluter/pfad/zum/dfbnet-freihalter-mcp/dfbnet_probe_out/storage_state.json
DFBNET_TOKEN_STATE=/absoluter/pfad/zum/dfbnet-freihalter-mcp/dfbnet_probe_out/token_state.json
DFBNET_TIMEZONE=Europe/Berlin
DFBNET_VERIFY_FROM=2025-07-01T00:00:00.000Z
```

### Referee-ID finden

Die Referee-ID ist der lange Wert in DFBNet-SRIA-API-URLs, z.B.:

```text
/api/referee/referee/<DFBNET_REFEREE_ID>/exemption
```

Du findest sie im Browser-Network-Tab, wenn du in SRIA die Freihalter-Seite öffnest oder einen Freihalter lädst.

Nicht committen:

- `~/.dfbnet_env`
- `dfbnet_probe_out/`
- `dfbnet_browser_profile/`
- `token_state.json`
- `storage_state.json`

## 5. Token-State erzeugen

DFBNet SRIA nutzt Browser-Login und Bearer Tokens. Das Tool speichert keinen fest einkopierten cURL-Token, sondern liest Tokens aus einer lokalen Playwright-Session und refreshes sie später über Keycloak.

### Variante A: manueller Browser-Login

Empfohlen, wenn du kein Passwort lokal speichern möchtest:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run python scripts/dfbnet_login_probe.py \
  --out ./dfbnet_probe_out \
  --user-data-dir ./dfbnet_browser_profile
```

Dann:

1. Im geöffneten Browser bei DFBNet einloggen.
2. Warten, bis SRIA geladen ist.
3. Optional einmal die Freihalter-Seite öffnen, damit API-Traffic sichtbar wird.
4. Script beenden, wenn `token_state.json` geschrieben wurde.

Prüfen:

```bash
test -f ./dfbnet_probe_out/token_state.json
chmod 600 ./dfbnet_probe_out/token_state.json ./dfbnet_probe_out/storage_state.json
```

### Variante B: Headless-Auto-Login

Nur wenn du `DFBNET_LOGIN_ID` und `DFBNET_PASSWORD` in `~/.dfbnet_env` gesetzt hast:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run python scripts/dfbnet_login_probe.py \
  --headless \
  --out ./dfbnet_probe_out \
  --user-data-dir ./dfbnet_browser_profile
```

Falls DFBNet Captcha, MFA oder geänderte Login-Formulare nutzt, kann Headless scheitern. Dann Variante A verwenden.

## 6. CLI testen

Auth-Status ohne Token-Leak:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run dfbnet-freihalter auth-status
```

Liste der Freihalter:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run dfbnet-freihalter list --from-iso '2025-07-01T00:00:00.000Z'
```

Dry-run für einen ganztägigen Freihalter:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run dfbnet-freihalter dry-run 2026-06-09
```

Erwarteter Payload in der Sommerzeit:

```json
{
  "from": "2026-06-08T22:00:00.000Z",
  "until": "2026-06-09T21:59:00.000Z",
  "reason": "PREVENTED",
  "comment": null
}
```

Dry-run für einen Zeitraum:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run dfbnet-freihalter dry-run-range 2026-06-11 2026-06-13
```

Dieser Zeitraum wird als **ein** Intervall modelliert, nicht als drei einzelne Freihalter.

## 7. Echte Änderungen ausführen

Vor echten Writes immer erst dry-run oder list verwenden.

Einzeltag erstellen:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run dfbnet-freihalter create-full-day 2026-06-09 --comment 'privat'
```

Zeitraum erstellen:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run dfbnet-freihalter create-range 2026-06-11 2026-06-13 --comment 'Urlaub'
```

Freihalter löschen:

```bash
DFBNET_ENV_FILE=~/.dfbnet_env uv run dfbnet-freihalter list --from-iso '2025-07-01T00:00:00.000Z'
DFBNET_ENV_FILE=~/.dfbnet_env uv run dfbnet-freihalter dry-run-delete EXEMPTION_ID
DFBNET_ENV_FILE=~/.dfbnet_env uv run dfbnet-freihalter delete EXEMPTION_ID
```

Create/Delete erwarten HTTP 204 und laden danach die Liste erneut zur Verifikation.

## 8. Hermes MCP konfigurieren

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

In laufender Hermes-CLI neu laden:

```text
/reload-mcp
```

Gateway neu starten:

```bash
hermes gateway restart
```

## 9. Verfügbare MCP-Tools

Hermes registriert die Tools mit Prefix `mcp_dfbnet_freihalter_`:

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

## 10. Tests

```bash
uv run --extra dev pytest -q
uv run python -m py_compile dfbnet_freihalter_mcp/*.py scripts/dfbnet_login_probe.py
```

## 11. Troubleshooting

### `DFBNET_REFEREE_ID is required`

`DFBNET_REFEREE_ID` fehlt in `~/.dfbnet_env` oder `DFBNET_ENV_FILE` zeigt auf die falsche Datei.

### `token_state not found`

`DFBNET_TOKEN_STATE` zeigt auf eine Datei, die noch nicht existiert. Führe das Probe-Script aus.

### `Access token expired and no refresh_token`

Der Token-State enthält keinen Refresh-Token. Login erneut durchführen.

### HTTP 401/403

Mögliche Ursachen:

- Session abgelaufen
- Refresh Token ungültig
- DFBNet-Login erfordert erneute Anmeldung
- falsche Referee-ID

Lösung: Token-State neu erzeugen und `auth-status` prüfen.

### MCP-Tools erscheinen nicht in Hermes

```bash
hermes mcp test dfbnet_freihalter
```

Dann in Hermes:

```text
/reload-mcp
```

Wenn sich die Tool-Liste geändert hat, den Hermes-Prozess komplett neu starten.

## 12. Veröffentlichung/Fork-Hinweise

Wenn du dieses Projekt forkst oder veröffentlichst:

- keine echten Referee-IDs committen
- keine Token-State-Dateien committen
- keine Browserprofile committen
- README-Disclaimer beibehalten
- keine offizielle DFBNet-Unterstützung suggerieren
