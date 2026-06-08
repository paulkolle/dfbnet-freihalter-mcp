# Sicherheit

## Inoffizielles Projekt

Dieses Projekt ist nicht offiziell von DFBNet/DFB unterstützt. Es arbeitet mit lokal gespeicherten Sessiondaten deines eigenen DFBNet-Zugangs. Behandle diese Daten wie Passwörter.

## Niemals veröffentlichen

Nicht committen, nicht in Issues posten, nicht in Screenshots teilen:

- `~/.dfbnet_env`
- `DFBNET_PASSWORD`
- `DFBNET_LOGIN_ID`, wenn du deinen Login nicht öffentlich machen willst
- `access_token`
- `refresh_token`
- `id_token`
- `token_state.json`
- `storage_state.json`
- Browserprofile wie `dfbnet_browser_profile/`
- Probe-Logs mit echten URLs, IDs oder personenbezogenen Daten

Die `.gitignore` schließt die üblichen lokalen Dateien aus. Prüfe vor jedem Push trotzdem:

```bash
git status --short --ignored
git diff --cached
```

## Wenn ein Secret geleakt wurde

1. DFBNet-Passwort ändern oder Session invalidieren, falls möglich.
2. `token_state.json` und `storage_state.json` lokal löschen.
3. Mit dem Probe-Script neu einloggen.
4. Falls der Leak in Git-Historie gelandet ist: Historie bereinigen, nicht nur einen neuen Commit mit Löschung machen.

## Sicherheitsprobleme melden

Bitte keine echten Tokens oder Passwörter in GitHub Issues posten.

Melde Sicherheitsprobleme mit:

- kurzer Beschreibung
- betroffener Version/Commit
- Reproduktionsschritten ohne echte Credentials
- redigierten Logs

## Betriebsregeln

- Nur mit deinem eigenen berechtigten DFBNet-Zugang nutzen.
- Vor Write-Operationen `dry-run-*` oder `list` verwenden.
- Keine Massenrequests oder parallele Automationsläufe starten.
- Bei HTTP 401/403 nicht blind retryen; erst Auth-State prüfen.
