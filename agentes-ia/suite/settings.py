"""Configuración compartida por las cinco apps (idioma, clave de IA, modelo…)."""

import json
import os
import sys
from pathlib import Path

DEFAULTS = {
    "lang": None,  # None = idioma del sistema
    "api_key": "",
    "model": "claude-opus-5-5",
    "effort": "medium",
    "anonymize": True,
}


def config_dir():
    if os.environ.get("PILOT_SUITE_HOME"):
        return Path(os.environ["PILOT_SUITE_HOME"])
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home())
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "PilotSuite"


class Settings(dict):
    def __init__(self, path, values):
        super().__init__({**DEFAULTS, **values})
        self.path = Path(path)

    @classmethod
    def load(cls, path=None):
        path = Path(path) if path else config_dir() / "settings.json"
        try:
            values = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(values, dict):
                values = {}
        except (OSError, ValueError):
            values = {}
        return cls(path, {k: v for k, v in values.items() if k in DEFAULTS})

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(dict(self), indent=2, ensure_ascii=False), encoding="utf-8")

    @property
    def api_key(self):
        return (self.get("api_key") or os.environ.get("ANTHROPIC_API_KEY") or "").strip()

    def data_dir(self):
        """Carpeta para datos locales (por ejemplo, la base de casos de FraudPilot)."""
        folder = self.path.parent
        folder.mkdir(parents=True, exist_ok=True)
        return folder
