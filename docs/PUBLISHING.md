# Veröffentlichung auf GitHub

Diese Checkliste hilft, das Projekt sicher auf GitHub zu veröffentlichen.

## Vor dem ersten Commit

Prüfen, dass sensible lokale Dateien ignoriert werden:

```bash
git status --short --ignored
```

Erwartung: lokale Runtime-Daten erscheinen mit `!!`, z.B.:

```text
!! .venv/
!! dfbnet_browser_profile/
!! dfbnet_probe_out/
!! dfbnet_probe_out_alt/
```

Trackbar sein dürfen u.a.:

```text
.env.example
.github/workflows/ci.yml
.gitignore
README.md
CONTRIBUTING.md
LICENSE
SECURITY.md
dfbnet_freihalter_mcp/
docs/
pyproject.toml
scripts/
tests/
uv.lock
```

## Secret-Check

Einfacher lokaler Check:

```bash
python3 - <<'PY'
from pathlib import Path
skip = {'.git', '.venv', 'dfbnet_probe_out', 'dfbnet_probe_out_alt', 'dfbnet_browser_profile'}
needles = ["Bearer " + "eyJ", "access_token=" + "eyJ", "refresh_token=" + "eyJ", "id_token=" + "eyJ"]
hits = []
for path in Path('.').rglob('*'):
    if any(part in skip for part in path.parts) or not path.is_file():
        continue
    try:
        text = path.read_text(encoding='utf-8')
    except Exception:
        continue
    if any(needle in text for needle in needles):
        hits.append(str(path))
if hits:
    print('Potential secrets found:')
    print('\n'.join(hits))
    raise SystemExit(1)
print('No obvious bearer/JWT token patterns found')
PY
```

Falls installiert, zusätzlich:

```bash
gitleaks detect --no-git --source .
```

## Tests

```bash
uv sync --extra dev
uv run --extra dev pytest -q
uv run python -m py_compile dfbnet_freihalter_mcp/*.py scripts/dfbnet_login_probe.py
```

## Repository erstellen

Mit GitHub CLI:

```bash
gh repo create dfbnet-freihalter-mcp --public --source . --push \
  --description "Inoffizieller lokaler MCP-Server und CLI-Client für DFBNet SRIA Freihalter"
```

Oder manuell auf GitHub ein leeres Repo erstellen und dann:

```bash
git remote add origin https://github.com/<owner>/dfbnet-freihalter-mcp.git
git add .
git commit -m "Initial public release"
git push -u origin main
```

## Empfohlene Repository-Einstellungen

- Description: `Inoffizieller lokaler MCP-Server und CLI-Client für DFBNet SRIA Freihalter`
- Topics: `mcp`, `dfbnet`, `sria`, `referee`, `python`, `automation`
- Issues aktivieren
- Wiki optional deaktivieren
- Branch protection für `main`, wenn mehrere Personen beitragen

## Wichtige Formulierungen beibehalten

README und Security-Hinweise sollten klar sagen:

- inoffiziell
- keine Verbindung zu DFB/DFBNet
- nur eigener berechtigter Account
- keine Massenautomation
- keine Tokens/Sessiondaten veröffentlichen

## Was nie veröffentlicht werden darf

- echte cURL-Beispiele mit Bearer Token
- persönliche Referee-ID
- `~/.dfbnet_env`
- `token_state.json`
- `storage_state.json`
- Browserprofile
- API-Probe-Logs mit personenbezogenen Daten
