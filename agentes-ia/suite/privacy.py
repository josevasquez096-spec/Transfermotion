"""Anonimización de datos personales antes de enviarlos a la IA.

Sustituye correos, IBAN, tarjetas (con validación Luhn), teléfonos, números largos (cuentas,
documentos) y los valores conocidos que se le indiquen (nombre del cliente…) por marcadores como
[EMAIL_1]. Con `unmask` se restauran en la respuesta de la IA.
"""

import re

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,4})?\b")
_CARD = re.compile(r"(?<![\w.,])\d(?:[ -]?\d){12,18}(?![\w.,]?\d)")
_PHONE = re.compile(r"(?<![\w.,])\+?\(?\d[\d ().-]{6,}\d(?![\w])")
_LONG_NUMBER = re.compile(r"(?<![\w.,])\d{8,}(?![\w.,]?\d)")
_DATE_LIKE = re.compile(r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}$")
_AMOUNT_LIKE = re.compile(r"^\d{1,3}(?:[.,  ]\d{3})*(?:[.,]\d{1,2})?$|^\d+[.,]\d{1,2}$")


def luhn_ok(digits):
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


class Anonymizer:
    def __init__(self):
        self.mapping = {}  # marcador -> valor original
        self._reverse = {}
        self._counters = {}
        self._known = []

    def _token(self, kind, value):
        value = value.strip()
        if value in self._reverse:
            return self._reverse[value]
        self._counters[kind] = self._counters.get(kind, 0) + 1
        token = f"[{kind}_{self._counters[kind]}]"
        self.mapping[token] = value
        self._reverse[value] = token
        return token

    def add_known(self, value, kind):
        """Valor que siempre debe ocultarse (nombre del cliente, número de cuenta…)."""
        value = str(value or "").strip()
        if len(value) >= 3:
            self._known.append((value, kind))

    def mask(self, text):
        if not text:
            return text
        for value, kind in sorted(self._known, key=lambda item: -len(item[0])):
            text = re.sub(re.escape(value), lambda m, k=kind: self._token(k, m.group(0)), text, flags=re.IGNORECASE)
        text = _EMAIL.sub(lambda m: self._token("EMAIL", m.group(0)), text)
        text = _IBAN.sub(lambda m: self._token("IBAN", m.group(0)), text)
        text = _CARD.sub(self._card, text)
        text = _PHONE.sub(self._phone, text)
        text = _LONG_NUMBER.sub(lambda m: self._token("NUM", m.group(0)), text)
        return text

    def _card(self, match):
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if 13 <= len(digits) <= 19 and luhn_ok(digits):
            return self._token("CARD", raw)
        return raw

    def _phone(self, match):
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if not 8 <= len(digits) <= 15 or _DATE_LIKE.match(raw) or _AMOUNT_LIKE.match(raw):
            return raw
        if "[" in raw or raw.isdigit():  # solo dígitos: cuenta o documento (NUM)
            return raw
        return self._token("PHONE", raw)

    def unmask(self, text):
        if not text:
            return text
        for token, value in self.mapping.items():
            text = text.replace(token, value)
        return text
