from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from suite.ai import FALLBACK_BETA, AIClient, AIError, _translate


class FakeClient:
    def __init__(self, text="OK", stop="end_turn"):
        self.calls = []
        self.text, self.stop = text, stop
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **kwargs):
        self.calls.append(kwargs)
        message = SimpleNamespace(stop_reason=self.stop, content=[SimpleNamespace(type="thinking", thinking=""),
                                                                   SimpleNamespace(type="text", text=self.text)])

        class Stream:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def get_final_message(self):
                return message

        return Stream()


def test_request_uses_effort_language_and_fallbacks():
    fake = FakeClient("hola")
    ai = AIClient("key", "claude-opus-5-5", "high", "fr", client=fake)
    assert ai.ask("System", "Prompt") == "hola"
    kw = fake.calls[0]
    assert kw["model"] == "claude-opus-5-5"
    assert kw["output_config"] == {"effort": "high"}
    assert kw["fallbacks"] == "default" and kw["betas"] == [FALLBACK_BETA]
    assert "French" in kw["system"]
    assert "thinking" not in kw


def test_haiku_has_no_fallbacks():
    fake = FakeClient()
    AIClient("key", "claude-haiku-5-5", client=fake).ask("s", "p")
    assert "fallbacks" not in fake.calls[0]


def test_json_output_with_schema():
    fake = FakeClient('{"a": 1}')
    schema = {"type": "object", "properties": {"a": {"type": "integer"}}, "required": ["a"],
              "additionalProperties": False}
    assert AIClient("key", client=fake).ask_json("s", "p", schema) == {"a": 1}
    assert fake.calls[0]["output_config"]["format"] == {"type": "json_schema", "schema": schema}


@pytest.mark.parametrize("text,stop,code", [("no json", "end_turn", "bad_output"), ("", "refusal", "refusal"),
                                            ('{"a"', "max_tokens", "truncated")])
def test_json_errors(text, stop, code):
    with pytest.raises(AIError) as err:
        AIClient("key", client=FakeClient(text, stop)).ask_json("s", "p", {"type": "object"})
    assert err.value.code == code


def test_invalid_settings_fall_back_to_defaults():
    ai = AIClient("key", "gpt-whatever", "extreme", client=FakeClient())
    assert ai.model == "claude-opus-5-5" and ai.effort == "medium"


def test_error_translation():
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")

    def status_error(cls, code):
        return cls("boom", response=httpx2.Response(code, request=request), body=None)

    assert _translate(status_error(anthropic.AuthenticationError, 401)).code == "auth"
    assert _translate(status_error(anthropic.RateLimitError, 429)).code == "rate"
    assert _translate(status_error(anthropic.BadRequestError, 400)).code == "bad_request"
    assert _translate(status_error(anthropic.InternalServerError, 500)).code == "server"
    assert _translate(anthropic.APIConnectionError(request=request)).code == "network"


def test_missing_key(tmp_path):
    from suite.settings import Settings

    with pytest.raises(AIError) as err:
        AIClient.from_settings(Settings.load(tmp_path / "s.json"), "es")
    assert err.value.code == "no_key"
