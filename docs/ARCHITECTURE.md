# Architektur

Dieses Dokument beschreibt den Aufbau des inoffiziellen DFBNet Freihalter MCPs.

## Ziel

Das Projekt verbindet drei Welten:

1. DFBNet SRIA-Webapp/Auth
2. ein lokales Python-CLI/API-Client-Modul
3. Hermes Agent über MCP

Es soll keine öffentliche API bereitstellen, sondern eine private lokale Automation für den eigenen berechtigten DFBNet-Zugang sein.

## Gesamtbild

```text
User / Hermes Prompt
  |
  v
Hermes Agent
  |
  | MCP JSON-RPC über stdin/stdout
  v
dfbnet-freihalter-mcp Prozess
  |
  | Python FastMCP Tool-Funktionen
  v
DfbnetClient
  |
  | TokenManager -> token_state.json / Keycloak Refresh
  | httpx -> DFBNet SRIA API
  v
https://api.dfbnet.org/api/referee
```

Der MCP ist ein stdio-MCP. Es gibt keinen HTTP-Port, keinen SSE-Endpoint und keinen dauerhaft separat gestarteten Webserver.

## Warum stdio-MCP?

Vorteile für diesen Use Case:

- keine öffentliche Angriffsfläche
- keine TLS-/Reverse-Proxy-Konfiguration
- DFBNet-Tokens bleiben lokal
- Hermes startet und beendet den Prozess selbst
- ideal für persönliche Tools mit lokalen Secrets

HTTP/StreamableHTTP-MCP wäre sinnvoll, wenn mehrere Clients denselben Server nutzen sollen. Für private DFBNet-Sessiondaten wäre das unnötig komplexer.

## Komponenten

```text
dfbnet_freihalter_mcp/
├── config.py   # liest ~/.dfbnet_env und Runtime-Konfiguration
├── auth.py     # Token-State laden, Ablauf prüfen, Refresh via Keycloak
├── dates.py    # lokale Europe/Berlin-Tage zu UTC-Zeitfenstern
├── client.py   # DFBNet API Client
├── cli.py      # dfbnet-freihalter Kommandozeile
└── server.py   # FastMCP Server und Tool-Definitionen

scripts/
└── dfbnet_login_probe.py  # Playwright Login/API Probe

tests/
└── test_dates_and_client.py
```

## Konfigurationsmodell

Die Konfiguration kommt aus einer Env-Datei, standardmäßig:

```text
~/.dfbnet_env
```

Wichtige Werte:

```bash
DFBNET_REFEREE_ID=<deine-referee-id>
DFBNET_TOKEN_STATE=/absoluter/pfad/dfbnet_probe_out/token_state.json
DFBNET_STORAGE_STATE=/absoluter/pfad/dfbnet_probe_out/storage_state.json
DFBNET_TIMEZONE=Europe/Berlin
DFBNET_VERIFY_FROM=2025-07-01T00:00:00.000Z
```

`DFBNET_REFEREE_ID` hat bewusst keinen echten Default. Dadurch kann beim Veröffentlichen des Repos keine persönliche ID im Code landen.

## Auth-Fluss

DFBNet SRIA nutzt eine Browser-Session und Keycloak Bearer Tokens.

### Initialer Login

```text
scripts/dfbnet_login_probe.py
  -> startet Playwright Chromium
  -> User loggt sich bei SRIA ein
  -> Script liest sessionStorage
  -> schreibt token_state.json und storage_state.json
```

`token_state.json` enthält u.a.:

- `access_token`
- `refresh_token`
- `expires_at`
- `updated_at`

Diese Datei ist geheim und darf nicht committed werden.

### Tool-Call mit gültigem Token

```text
MCP Tool
  -> DfbnetClient
  -> TokenManager.load()
  -> Access Token gültig
  -> DFBNet API Request mit Authorization: Bearer ...
```

### Tool-Call mit ablaufendem Token

```text
MCP Tool
  -> TokenManager.load()
  -> Access Token bald abgelaufen
  -> POST Keycloak token endpoint mit refresh_token
  -> token_state.json aktualisieren
  -> DFBNet API Request
```

Refresh Endpoint:

```text
https://auth.dfbnet.org/realms/dfbnet/protocol/openid-connect/token
```

Der MCP loggt keine vollständigen Tokens in Tool-Ausgaben.

## DFBNet-API-Form

Beobachtete API-Form der SRIA-Webapp, Stand der Entwicklung dieses Tools. Sie kann sich jederzeit ändern.

Basis:

```text
https://api.dfbnet.org/api/referee
```

Endpoints:

```http
GET    /referee/{referee_id}/exemption?from={iso}
GET    /referee/{referee_id}/exemption-conflict?from={iso}&until={iso}
POST   /referee/{referee_id}/exemption
DELETE /referee/{referee_id}/exemption/{exemption_id}
```

Create/Delete-Erfolg ist HTTP 204 ohne Body.

## Datums- und Payload-Modell

DFBNet erwartet UTC-Zeitpunkte. Die UI arbeitet für ganztägige Freihalter aber logisch lokal.

Das Tool modelliert ganztägige Freihalter so:

```text
Start lokal: YYYY-MM-DD 00:00:00 Europe/Berlin
Ende lokal:  YYYY-MM-DD 23:59:00 Europe/Berlin
```

Dann wird nach UTC konvertiert:

```text
YYYY-MM-DDTHH:MM:SS.mmmZ
```

Beispiel Sommerzeit:

```text
lokal: 2026-06-09 00:00 Europe/Berlin
UTC:   2026-06-08T22:00:00.000Z

lokal: 2026-06-09 23:59 Europe/Berlin
UTC:   2026-06-09T21:59:00.000Z
```

Payload:

```json
{
  "from": "2026-06-08T22:00:00.000Z",
  "until": "2026-06-09T21:59:00.000Z",
  "reason": "PREVENTED",
  "comment": null
}
```

Mehrtagige Freihalter werden als ein Intervall erstellt:

```text
2026-06-11 00:00 lokal bis 2026-06-13 23:59 lokal
```

Nicht als Schleife über 11., 12., 13. Juni.

## Runtime-Fluss: Zeitraum erstellen

```text
create_date_range_exemption(start_date, end_date)
  -> dates.date_range_payload()
  -> optional GET /exemption-conflict
  -> POST /exemption
  -> HTTP 204 prüfen
  -> optional GET /exemption?from=...
  -> Match im Ergebnis suchen
  -> Ergebnis an MCP/Hermes zurückgeben
```

## Runtime-Fluss: löschen

```text
delete_exemption(exemption_id)
  -> DELETE /exemption/{exemption_id}
  -> HTTP 204 prüfen
  -> optional GET /exemption?from=...
  -> prüfen, dass ID nicht mehr vorhanden ist
```

## MCP Tool-Registrierung

`server.py` definiert FastMCP-Tools. Hermes entdeckt sie beim Start oder bei `/reload-mcp`.

Toolnamen in `server.py`:

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

Hermes macht daraus z.B.:

```text
mcp_dfbnet_freihalter_create_date_range_exemption
```

## Sicherheitsmodell

Schutzmaßnahmen:

- lokale stdio-Verbindung statt öffentlicher HTTP-Service
- keine echten Default-IDs im Code
- keine Secrets im Repo
- `.gitignore` schließt Runtime-State und Browserprofile aus
- `auth_status()` gibt nur Token-Zusammenfassungen aus
- Probe-Script redigiert Authorization-/Cookie-/Token-Felder
- Dry-run-Tools für ungefährliche Vorprüfung
- Create/Delete prüfen HTTP 204 und verifizieren danach per Liste

Nicht abgedeckt:

- keine offizielle API-Stabilitätsgarantie
- keine Captcha-/MFA-Umgehung
- kein Rechte-/Mandantenmodell innerhalb des MCPs
- keine serverseitige Freigabe pro Write-Call

## Fehler- und Wiederherstellungsmodell

### Token abgelaufen

Normalfall: Refresh über `refresh_token`.

### Refresh fehlgeschlagen

Neu einloggen und `token_state.json` neu erzeugen.

### API 401/403

Mögliche Ursachen:

- ungültige Session
- falsche Referee-ID
- geänderte DFBNet-Berechtigungen
- DFBNet verlangt erneuten Login

### Verifikation schlägt fehl

Der Write kann HTTP 204 liefern, aber die Nachprüfung findet den Eintrag nicht. In diesem Fall nicht blind erneut senden, sondern mit `list_exemptions` prüfen, um Doppelanlagen zu vermeiden.

## Erweiterungspunkte

- idempotenter Create-Modus: existierenden identischen Freihalter erkennen und überspringen
- bessere Ausgabeformate für Agenten
- optionaler lokaler Approval-Layer vor Write-Tools
- Update/Edit bestehender Freihalter, falls API-Shape bekannt ist
- CI mit Secret-Scan
- Paketveröffentlichung auf PyPI, falls rechtlich/organisatorisch gewünscht
