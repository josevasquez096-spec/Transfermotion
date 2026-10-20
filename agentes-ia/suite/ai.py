"""Cliente de Claude (API de Anthropic) compartido por los agentes.

Cada agente hace peticiones de un solo paso: texto libre (`ask`) o JSON validado contra un
esquema (`ask_json`, con salidas estructuradas). Los errores se convierten en `AIError` con un
código que la interfaz traduce (err_auth, err_rate, …).
"""

import json

try:
    import anthropic
except ImportError:  # la app sigue funcionando sin IA
    anthropic = None

from .i18n import AI_LANG

MODELS = ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5")
EFFORTS = ("low", "medium", "high")
# Si un modelo rechaza la petición, la API la repite con el modelo de respaldo recomendado.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AIError(Exception):
    def __init__(self, code, detail=""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


class AIClient:
    def __init__(self, api_key, model=MODELS[0], effort="medium", lang="es", client=None):
        if client is None:
            if anthropic is None:
                raise AIError("no_sdk")
            client = anthropic.Anthropic(api_key=api_key, max_retries=3)
        self.client = client
        self.model = model if model in MODELS else MODELS[0]
        self.effort = effort if effort in EFFORTS else "medium"
        self.lang = lang

    @classmethod
    def from_settings(cls, settings, lang):
        if not settings.api_key:
            raise AIError("no_key")
        return cls(settings.api_key, settings.get("model"), settings.get("effort"), lang)

    def _system(self, system):
        return (
            f"{system.strip()}\n\nWrite every human-readable text of your answer in {AI_LANG.get(self.lang, 'Spanish')}, "
            "unless the user explicitly asks for another language. Never invent data that was not provided."
        )

    def request_kwargs(self, system, prompt, max_tokens, schema=None):
        output_config = {"effort": self.effort}
        if schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": schema}
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": self._system(system),
            "messages": [{"role": "user", "content": prompt}],
            "output_config": output_config,
        }
        # Haiku no tiene respaldo en el servidor.
        if not self.model.startswith("claude-haiku"):
            kwargs["betas"] = [FALLBACK_BETA]
            kwargs["fallbacks"] = "default"
        return kwargs

    def _run(self, system, prompt, max_tokens, schema=None):
        kwargs = self.request_kwargs(system, prompt, max_tokens, schema)
        try:
            with self.client.beta.messages.stream(**kwargs) as stream:
                message = stream.get_final_message()
        except Exception as exc:  # se traduce a un AIError con código
            raise _translate(exc) from exc
        if message.stop_reason == "refusal":
            raise AIError("refusal")
        text = "".join(block.text for block in message.content if block.type == "text").strip()
        if message.stop_reason == "max_tokens" and (schema is not None or not text):
            raise AIError("truncated")
        return text

    def ask(self, system, prompt, max_tokens=16000):
        return self._run(system, prompt, max_tokens)

    def ask_json(self, system, prompt, schema, max_tokens=16000):
        text = self._run(system, prompt, max_tokens, schema)
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise AIError("bad_output") from exc
        if not isinstance(data, dict):
            raise AIError("bad_output")
        return data

    def ping(self):
        return self.ask("You are a connectivity check.", "Reply with the single word: OK", max_tokens=200)


def _translate(exc):
    if anthropic is None or isinstance(exc, AIError):
        return exc if isinstance(exc, AIError) else AIError("server", str(exc))
    if isinstance(exc, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return AIError("auth")
    if isinstance(exc, anthropic.RateLimitError):
        return AIError("rate")
    if isinstance(exc, anthropic.BadRequestError):
        return AIError("bad_request", exc.message)
    if isinstance(exc, anthropic.APIStatusError):
        return AIError("server", str(exc.status_code))
    if isinstance(exc, anthropic.APIConnectionError):
        return AIError("network")
    return AIError("server", type(exc).__name__)


def obj(properties, required=None):
    """Atajo para esquemas JSON estrictos (todas las propiedades obligatorias)."""
    return {
        "type": "object",
        "properties": properties,
        "required": list(required if required is not None else properties),
        "additionalProperties": False,
    }


STR = {"type": "string"}
STR_LIST = {"type": "array", "items": {"type": "string"}}
