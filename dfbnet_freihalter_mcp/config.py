from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


DEFAULT_ENV_FILE = "~/.dfbnet_env"
DEFAULT_STORAGE_STATE = "~/.hermes/dfbnet/storage_state.json"
DEFAULT_TOKEN_STATE = "~/.hermes/dfbnet/token_state.json"


@dataclass(frozen=True)
class DfbnetConfig:
    referee_id: str
    env_file: Path
    storage_state_path: Path
    token_state_path: Path
    api_base_url: str = "https://api.dfbnet.org/api/referee"
    auth_base_url: str = "https://auth.dfbnet.org/realms/dfbnet"
    client_id: str = "referee-administration"
    origin: str = "https://sria.dfbnet.org"
    timezone: str = "Europe/Berlin"
    verify_after_create_from: str = "2025-07-01T00:00:00.000Z"


def _expand(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def load_config(env_file: str | Path | None = None) -> DfbnetConfig:
    env_path = _expand(env_file or os.getenv("DFBNET_ENV_FILE", DEFAULT_ENV_FILE))
    if load_dotenv and env_path.exists():
        load_dotenv(env_path)

    storage = os.getenv("DFBNET_STORAGE_STATE") or DEFAULT_STORAGE_STATE
    token_state = os.getenv("DFBNET_TOKEN_STATE") or DEFAULT_TOKEN_STATE
    referee_id = os.getenv("DFBNET_REFEREE_ID")
    if not referee_id:
        raise ValueError(
            "DFBNET_REFEREE_ID is required. Set it in ~/.dfbnet_env or pass --env-file. "
            "See docs/SETUP.md for the first-time setup."
        )
    return DfbnetConfig(
        referee_id=referee_id,
        env_file=env_path,
        storage_state_path=_expand(storage),
        token_state_path=_expand(token_state),
        api_base_url=os.getenv("DFBNET_API_BASE_URL", "https://api.dfbnet.org/api/referee").rstrip("/"),
        auth_base_url=os.getenv("DFBNET_AUTH_BASE_URL", "https://auth.dfbnet.org/realms/dfbnet").rstrip("/"),
        client_id=os.getenv("DFBNET_CLIENT_ID", "referee-administration"),
        origin=os.getenv("DFBNET_ORIGIN", "https://sria.dfbnet.org"),
        timezone=os.getenv("DFBNET_TIMEZONE", "Europe/Berlin"),
        verify_after_create_from=os.getenv("DFBNET_VERIFY_FROM", "2025-07-01T00:00:00.000Z"),
    )
