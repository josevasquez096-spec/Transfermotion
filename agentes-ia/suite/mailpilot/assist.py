"""Funciones de IA de MailPilot (opcionales: necesitan internet y una clave de API).

Mejorar o traducir un correo al inglés, resumir un correo y proponer reglas para ordenar el buzón. Si está
activada la anonimización, los datos personales se sustituyen por marcadores antes de enviarlos.
"""

from ..ai import STR, STR_LIST, obj

TONES = ("professional", "friendly", "concise", "firm", "apologetic")
TONE_TEXT = {"professional": "professional and courteous", "friendly": "warm and friendly, but professional",
             "concise": "short, direct and clear", "firm": "firm but polite", "apologetic": "empathetic and apologetic"}

EMAIL_SCHEMA = obj({"subject": STR, "body": STR, "changes": STR_LIST})
_EMAIL_RULES = """Rules:
- The subject and body of the email must be in English.
- Keep the meaning, facts, names, amounts, dates, claim numbers and placeholders such as [EMAIL_1] or [Name]
  exactly as written. Do not invent information, promises or deadlines.
- Keep the greeting, the closing and the signature lines.
- "changes": 3 to 8 short notes about the main improvements, so the user learns from them."""
REWRITE_SYSTEM = ("You are an expert editor of professional business emails written in English by non-native "
                  "speakers who work in a bank's fraud claims team. Rewrite the email in clear, natural and correct "
                  "English with the requested tone.\n" + _EMAIL_RULES)
TRANSLATE_SYSTEM = ("You translate business emails into natural, professional English for a bank's fraud claims "
                    "team. Translate the email with the requested tone; do not translate word by word.\n"
                    + _EMAIL_RULES)

SUMMARY_SCHEMA = obj({"summary": STR, "actions": STR_LIST, "reply": STR})
SUMMARY_SYSTEM = (
    "You help a bank employee handle incoming email. Summarize the email in 2 to 4 sentences, list the concrete "
    "actions it requires (who, what and when, only if stated) and draft a short, professional reply in English. "
    "The reply must not promise outcomes, refunds or deadlines that the email does not mention. Keep placeholders "
    "such as [EMAIL_1] exactly as written.")

ORGANIZE_SCHEMA = obj({
    "rules": {"type": "array", "items": obj({"name": STR, "query": STR, "folder": STR, "category": STR})},
    "notes": STR_LIST,
})
ORGANIZE_SYSTEM = """You help a bank employee organize an Outlook mailbox. From the statistics provided, propose up
to 8 useful rules. Each rule has:
- "name": a short name.
- "query": a search in this syntax: words (all must appear), "exact phrase", -word to exclude, a OR b,
  from:address-or-domain, subject:word, domain:example.com, has:attachment, has:claim, is:unread, is:external.
- "folder": an existing folder path from the list, a new short folder name, or "" to keep messages in place.
- "category": an existing category name, a new short category name, or "" for none.
Prefer rules for newsletters and automatic notifications, card networks, vendors and recurring internal reports.
Never propose rules that move messages from customers or about claims out of the inbox without a category.
"notes": 2 to 5 short tips for keeping the mailbox tidy."""


def email_prompt(subject, body, tone):
    return f"Tone: {TONE_TEXT.get(tone, TONE_TEXT['professional'])}\n\nSubject: {subject}\n\nEmail:\n<<<\n{body}\n>>>"


def organize_prompt(overview, senders, domains, folders, categories):
    lines = [f"Messages analyzed: {overview['total']} (unread: {overview['unread']})", "", "Top senders:"]
    lines += [f"- {r['col_email'] or r['col_sender']}: {r['col_count']} messages" for _, r in senders.iterrows()]
    lines += ["", "Top domains:"]
    lines += [f"- {r['col_domain']}: {r['col_count']} ({'internal' if r['col_internal'] else 'external'})"
              for _, r in domains.iterrows()]
    lines += ["", "Existing folders:"] + [f"- {path}" for path in folders]
    lines += ["", "Existing categories:"] + [f"- {name}" for name in categories]
    return "\n".join(lines)


def unmask_all(data, anon):
    """Restaura los datos anonimizados en todas las cadenas de la respuesta."""
    if anon is None:
        return data
    if isinstance(data, str):
        return anon.unmask(data)
    if isinstance(data, list):
        return [unmask_all(v, anon) for v in data]
    if isinstance(data, dict):
        return {k: unmask_all(v, anon) for k, v in data.items()}
    return data
