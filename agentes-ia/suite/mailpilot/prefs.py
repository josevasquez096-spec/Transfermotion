"""Preferencias de MailPilot guardadas en el equipo: reglas, búsquedas, diccionario personal, buzones abiertos…"""

import json
from pathlib import Path

from .detectors import DEFAULT_CLAIM_REGEX

DEFAULTS = {
    "backend": "",  # «outlook» o «demo»: la última conexión que funcionó
    "internal_domains": "",  # dominios propios separados por comas (vacío = el del buzón principal)
    "claim_regex": DEFAULT_CLAIM_REGEX,
    "user_words": [],  # palabras que el corrector debe aceptar
    "saved_searches": [],  # [{"name", "query"}]
    "shared": [],  # buzones compartidos que se vuelven a abrir al conectar
    "rules": [],  # reglas locales (MailRule.to_dict())
}


class Prefs(dict):
    def __init__(self, path, values):
        super().__init__({k: list(v) if isinstance(v, list) else v for k, v in DEFAULTS.items()})
        self.update({k: v for k, v in values.items() if k in DEFAULTS and isinstance(v, type(DEFAULTS[k]))})
        self.path = Path(path)

    @classmethod
    def load(cls, path):
        try:
            values = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            values = {}
        return cls(path, values if isinstance(values, dict) else {})

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(dict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def domains(self, fallback=()):
        own = [d.strip().lstrip("@").lower() for d in self["internal_domains"].replace(";", ",").split(",")]
        return [d for d in own if d] or [d for d in fallback if d]
