# Beitragen

Danke für dein Interesse. Dieses Projekt ist inoffiziell und arbeitet mit einer nicht offiziell dokumentierten Webapp/API. Beiträge sollten deshalb besonders vorsichtig mit Auth, Tokens und API-Last umgehen.

## Grundregeln

- Keine echten DFBNet-IDs, Tokens, Passwörter oder Probe-Logs committen.
- Keine Änderungen, die Massenautomation begünstigen.
- Write-Operationen müssen Dry-run- oder Verifikationspfade behalten.
- Dokumentation bitte auf Deutsch halten.
- API-Details als beobachtet und instabil formulieren, nicht als offizielle Spezifikation.

## Lokale Entwicklung

```bash
uv sync --extra dev
uv run playwright install chromium
uv run --extra dev pytest -q
uv run python -m py_compile dfbnet_freihalter_mcp/*.py scripts/dfbnet_login_probe.py
```

## Vor einem Pull Request

```bash
git status --short --ignored
uv run --extra dev pytest -q
grep -R "access_token\|refresh_token\|DFBNET_PASSWORD\|Authorization: Bearer" -n . \
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=dfbnet_probe_out --exclude-dir=dfbnet_browser_profile || true
```

Wenn du neue MCP-Tools hinzufügst, dokumentiere sie in `README.md` und `docs/SETUP.md`.
