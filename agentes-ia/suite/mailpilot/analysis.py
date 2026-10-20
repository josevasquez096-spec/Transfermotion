"""Análisis del buzón sin conexión: resumen, remitentes y dominios frecuentes, sugerencias de organización,
phishing, datos sensibles enviados en claro (tarjetas, IBAN) e índice de reclamaciones.

Las tablas usan claves de columna (col_…) que la interfaz traduce antes de mostrarlas o exportarlas.
"""

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import pandas as pd
from openpyxl import Workbook

from ..tabular import write_df
from . import detectors

AUTOMATIC = re.compile(r"^(?:no-?reply|newsletters?|news|info|marketing|mailer|notifica\w*|notification\w*|"
                       r"boletin\w*|bulletin\w*|updates?)\b", re.I)
MB = 1024 * 1024


def _external(msg, internal):
    domain = msg.domain
    return bool(domain) and not any(domain == d or domain.endswith("." + d) for d in internal)


def overview(messages):
    dates = [m.received for m in messages if m.received]
    return {"total": len(messages), "unread": sum(m.unread for m in messages),
            "flagged": sum(m.flagged for m in messages), "attachments": sum(m.has_attachments for m in messages),
            "size_mb": round(sum(m.size for m in messages) / MB, 1), "senders": len({m.sender_email or m.sender_name
                                                                                     for m in messages}),
            "folders": len({(m.store_id, m.folder_path) for m in messages}),
            "oldest": min(dates) if dates else None, "newest": max(dates) if dates else None}


def senders(messages, n=20):
    rows = {}
    for m in messages:
        key = (m.sender_email or m.sender_name).lower()
        row = rows.setdefault(key, {"col_sender": m.sender_name, "col_email": m.sender_email, "col_count": 0,
                                    "col_unread": 0, "col_size_mb": 0.0, "col_last": None})
        row["col_count"] += 1
        row["col_unread"] += m.unread
        row["col_size_mb"] += m.size / MB
        if m.received and (row["col_last"] is None or m.received > row["col_last"]):
            row["col_last"] = m.received
    df = pd.DataFrame(rows.values(), columns=["col_sender", "col_email", "col_count", "col_unread", "col_size_mb",
                                              "col_last"])
    df["col_size_mb"] = df["col_size_mb"].round(2)
    return df.sort_values(["col_count", "col_unread"], ascending=False).head(n).reset_index(drop=True)


def domains(messages, internal, n=20):
    counts = Counter(m.domain for m in messages if m.domain)
    unread = Counter(m.domain for m in messages if m.domain and m.unread)
    rows = [{"col_domain": d, "col_count": c, "col_unread": unread[d],
             "col_internal": any(d == i or d.endswith("." + i) for i in internal)} for d, c in counts.most_common(n)]
    return pd.DataFrame(rows, columns=["col_domain", "col_count", "col_unread", "col_internal"])


def by_month(messages):
    counts = Counter(m.received.strftime("%Y-%m") for m in messages if m.received)
    return pd.DataFrame(sorted(counts.items()), columns=["col_month", "col_count"])


def suggestions(messages, internal, claim_pattern=detectors.DEFAULT_CLAIM_REGEX, now=None):
    """Ideas para ordenar el buzón: {key, params, query, action} (action: news, tag, read, review)."""
    now = now or datetime.now()
    out = []
    automatic = Counter(m.sender_email.lower() for m in messages
                        if m.sender_email and AUTOMATIC.match(m.sender_email.split("@")[0]))
    for email, count in automatic.most_common(5):
        if count >= 3:
            out.append({"key": "sug_newsletter", "params": {"sender": email, "n": count},
                        "query": f"from:{email}", "action": "news"})
    external = Counter(m.domain for m in messages if _external(m, internal) and m.domain not in detectors.FREEMAIL
                       and not AUTOMATIC.match(m.sender_email.split("@")[0]))
    for domain, count in external.most_common(3):
        if count >= 5:
            out.append({"key": "sug_domain", "params": {"domain": domain, "n": count},
                        "query": f"domain:{domain}", "action": "tag"})
    claims = [m for m in messages if not m.categories and detectors.find_claims(m.subject, claim_pattern)]
    if len(claims) >= 5:
        out.append({"key": "sug_claims", "params": {"n": len(claims)}, "query": "has:claim -has:category",
                    "action": "tag"})
    old_unread = [m for m in messages if m.unread and m.received and m.received < now - timedelta(days=30)]
    if len(old_unread) >= 5:
        out.append({"key": "sug_old_unread", "params": {"n": len(old_unread)}, "query": "is:unread older:30d",
                    "action": "read"})
    stale = [m for m in messages if m.flagged and m.received and m.received < now - timedelta(days=14)]
    if stale:
        out.append({"key": "sug_flags", "params": {"n": len(stale)}, "query": "is:flagged older:14d",
                    "action": "review"})
    big = [m for m in messages if m.size >= 5 * MB]
    if len(big) >= 3:
        out.append({"key": "sug_big", "params": {"n": len(big), "mb": round(sum(m.size for m in big) / MB)},
                    "query": "size:>5mb", "action": "review"})
    return out


def phishing(messages, internal):
    """[(puntuación, señales, correo)] de los sospechosos (los correos deben traer cuerpo y HTML)."""
    rows = []
    for m in messages:
        score, flags = detectors.phishing_score(m, m.body or "", m.html or "", internal)
        if score >= detectors.PHISHING_THRESHOLD:
            rows.append((score, flags, m))
    return sorted(rows, key=lambda r: (-r[0], -(r[2].received or datetime.min).timestamp()))


def sensitive(messages):
    """[(tipo, valor enmascarado, correo)] con tarjetas (Luhn) e IBAN escritos en asunto o cuerpo."""
    rows = []
    for m in messages:
        text = f"{m.subject}\n{m.body or ''}"
        rows += [("card", detectors.mask_card(c), m) for c in dict.fromkeys(detectors.find_cards(text))]
        rows += [("iban", detectors.mask_iban(i), m) for i in dict.fromkeys(detectors.find_ibans(text))]
    return rows


def claims(messages, pattern=detectors.DEFAULT_CLAIM_REGEX, internal=()):
    """Tabla con cada número de reclamación: correos, fechas, no leídos, carpetas y remitentes externos."""
    index = defaultdict(list)
    for m in messages:
        for claim in dict.fromkeys(c.upper() for c in detectors.find_claims(f"{m.subject}\n{m.body or ''}", pattern)):
            index[claim].append(m)
    rows = []
    for claim, items in index.items():
        dates = [m.received for m in items if m.received]
        last = max(items, key=lambda m: m.received or datetime.min)
        people = dict.fromkeys(m.sender_name for m in items if _external(m, internal) and m.sender_name)
        rows.append({"col_claim": claim, "col_count": len(items), "col_unread": sum(m.unread for m in items),
                     "col_first": min(dates) if dates else None, "col_last": max(dates) if dates else None,
                     "col_customers": ", ".join(people), "col_folders": ", ".join(dict.fromkeys(m.folder_path
                                                                                                 for m in items)),
                     "col_subject": last.subject})
    df = pd.DataFrame(rows, columns=["col_claim", "col_count", "col_unread", "col_first", "col_last",
                                     "col_customers", "col_folders", "col_subject"])
    return df.sort_values(["col_last", "col_count"], ascending=False, na_position="last").reset_index(drop=True)


def message_table(messages, extra=None):
    """Lista de correos para mostrar o exportar; `extra` añade columnas propias (lista de dict por correo)."""
    rows = []
    for n, m in enumerate(messages):
        row = {"col_date": m.received, "col_sender": m.sender_name, "col_email": m.sender_email,
               "col_subject": m.subject, "col_folder": m.folder_path, "col_categories": ", ".join(m.categories),
               "col_unread": m.unread, "col_size_kb": round(m.size / 1024)}
        if extra:
            row.update(extra[n])
        rows.append(row)
    return pd.DataFrame(rows)


def export_excel(path, sheets):
    """Guarda varias tablas (nombre de hoja, DataFrame) en un libro de Excel."""
    wb = Workbook()
    wb.remove(wb.active)
    for name, df in sheets:
        write_df(wb.create_sheet(re.sub(r"[\[\]:*?/\\]", " ", name)[:31] or "Datos"), df, accent="0F6CBD")
    wb.save(path)
    return path
