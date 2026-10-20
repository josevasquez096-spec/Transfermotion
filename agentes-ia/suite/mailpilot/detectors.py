"""Identificación de datos sensibles y señales de phishing en correos (sin conexión)."""

import html as htmllib
import re
from urllib.parse import urlparse

from ..privacy import _CARD, _IBAN, luhn_ok

DEFAULT_CLAIM_REGEX = r"\b(?:R|FR|CLM|CASE|REC|RECL)-?\d{4,}(?:-\d+)*\b"
AMOUNT_RE = re.compile(r"(?:[$€£]\s?|\b(?:USD|EUR|MXN|COP|CAD|GBP|PEN|CLP|ARS|DOP)\s?)\d[\d.,]*\d"
                       r"|\b\d[\d.,]*\d\s?(?:USD|EUR|MXN|COP|CAD|GBP|€|dollars|euros|pesos)(?!\w)", re.I)
PHONE_RE = re.compile(r"(?<![\w.])\+?\d[\d ().-]{7,}\d(?!\w)")
URL_RE = re.compile(r"\b(?:https?://|www\.)[^\s<>\"')]+", re.I)
HREF_RE = re.compile(r"<a\b[^>]*?href\s*=\s*[\"']([^\"']+)[\"'][^>]*>(.*?)</a\s*>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
IP_URL = re.compile(r"^https?://\d{1,3}(?:\.\d{1,3}){3}", re.I)

FREEMAIL = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "msn.com", "yahoo.com",
            "yahoo.es", "yahoo.fr", "icloud.com", "me.com", "aol.com", "proton.me", "protonmail.com", "gmx.com",
            "gmx.net", "mail.com", "yandex.com", "zoho.com", "orange.fr", "free.fr", "laposte.net"}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "cutt.ly", "rebrand.ly", "buff.ly",
              "shorturl.at", "rb.gy", "t.ly", "tiny.cc"}
RISKY_TLDS = (".zip", ".mov", ".top", ".xyz", ".click", ".tk", ".gq", ".ml", ".cf", ".work", ".rest", ".country",
              ".support", ".loan", ".win", ".review")
RISKY_EXT = (".exe", ".js", ".vbs", ".scr", ".iso", ".img", ".html", ".htm", ".zip", ".rar", ".7z", ".docm",
             ".xlsm", ".pptm", ".lnk", ".hta", ".bat", ".cmd", ".ps1", ".jar", ".msi", ".one", ".svg")
# Nombres que se suelen suplantar: departamentos internos y marcas conocidas. Se evitan palabras genéricas
# («support», «seguridad», «banco») que usan a diario proveedores y bancos con los que se trabaja.
BRAND_WORDS = ("helpdesk", "help desk", "service desk", "it service", "it support", "soporte técnico",
               "mesa de ayuda", "support informatique", "microsoft", "office 365", "outlook", "paypal", "dhl",
               "fedex", "ups", "netflix", "amazon", "apple", "visa", "mastercard", "tesorería", "treasury", "trésorerie",
               "payroll", "nómina", "paie", "recursos humanos", "human resources", "ressources humaines")
TITLES = ("ceo", "cfo", "director", "directora", "directeur", "manager", "gerente", "president", "presidente")
PHISHING_THRESHOLD = 40  # «is:phishing» y los avisos de la app empiezan aquí (riesgo medio)
URGENCY = ("urgent", "immediately", "within 24 hours", "within 48 hours", "account suspended", "account locked",
           "action required", "final notice", "last warning", "expires today", "verify now", "urgente",
           "inmediato", "inmediatamente", "suspendida", "bloqueada", "última advertencia", "acción requerida",
           "en 24 horas", "immédiatement", "suspendu", "bloqué", "action requise", "dernier avertissement")
CREDENTIALS = ("password", "passcode", "one-time code", "otp", "pin", "login", "log in", "sign in",
               "verify your account", "verify your identity", "confirm your identity", "update your details",
               "update your information", "reset your password", "wire transfer", "gift card", "bank details",
               "change of bank account", "new bank account", "contraseña", "clave", "código", "verifique su cuenta",
               "verificar su cuenta", "actualice sus datos", "confirme su identidad", "transferencia urgente",
               "tarjeta de regalo", "cambio de cuenta", "nueva cuenta bancaria", "mot de passe", "code de vérification",
               "vérifiez votre compte", "mettez à jour vos informations", "virement urgent", "carte cadeau",
               "nouveau rib", "changement de rib")


def find_cards(text):
    out = []
    for m in _CARD.finditer(text or ""):
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and luhn_ok(digits):
            out.append(m.group(0))
    return out


def find_ibans(text):
    return [m.group(0) for m in _IBAN.finditer(text or "")]


def find_claims(text, pattern=DEFAULT_CLAIM_REGEX):
    """Números de reclamación (texto completo de cada coincidencia aunque el patrón tenga grupos)."""
    try:
        return [m.group(0) for m in re.finditer(pattern, text or "", re.I)]
    except re.error:
        return []


def find_amounts(text):
    return AMOUNT_RE.findall(text or "")


def find_phones(text):
    out = []
    for m in PHONE_RE.finditer(text or ""):
        digits = re.sub(r"\D", "", m.group(0))
        if 8 <= len(digits) <= 15 and not re.match(r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}$", m.group(0)):
            out.append(m.group(0))
    return out


def find_links(text, html=""):
    links = URL_RE.findall(text or "")
    links += [h for h, _ in HREF_RE.findall(html or "") if h.lower().startswith(("http", "www"))]
    return list(dict.fromkeys(links))


DETECTORS = {"card": find_cards, "iban": find_ibans, "claim": find_claims, "amount": find_amounts,
             "phone": find_phones, "link": lambda text: find_links(text)}


def mask_card(card):
    digits = re.sub(r"\D", "", card)
    return f"**** **** **** {digits[-4:]}"


def mask_iban(iban):
    compact = re.sub(r"\s", "", iban)
    return f"{compact[:4]} **** **** {compact[-4:]}"


def _host(url):
    if url.lower().startswith("www."):
        url = "http://" + url
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def _registrable(host):
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "com", "gob", "gov", "org", "net", "edu") and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


_HOMOGLYPHS = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t"})


def _skeleton(label):
    return label.translate(_HOMOGLYPHS).replace("rn", "m").replace("vv", "w").replace("-", "")


def _distance(a, b):
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, cb in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (ca != cb))
    return row[-1]


def lookalike(domain, internal):
    """True si el dominio imita a uno interno: banco-dem0.com, bancodemo-secure.com, banco-demo.com.verify.top…"""
    if not domain:
        return False
    label = _registrable(domain).split(".")[0]
    flat = domain.replace("-", "").replace(".", "")
    for own_domain in internal:
        if domain == own_domain or domain.endswith("." + own_domain):
            return False
        own = _registrable(own_domain).split(".")[0]
        if len(own) < 4:
            continue
        if _skeleton(label) == _skeleton(own) or own.replace("-", "") in flat:
            return True
        if _distance(label, own) <= (1 if len(own) < 8 else 2):
            return True
    return False


def _org_names(internal):
    """«banco-demo.com» → {"banco-demo", "banco demo", "bancodemo"}: el nombre de la propia empresa."""
    names = set()
    for domain in internal:
        label = domain.split(".")[0]
        if len(label) >= 4:
            names |= {label, label.replace("-", " "), label.replace("-", "")}
    return names


def phishing_score(msg, body="", html="", internal_domains=()):
    """(puntuación 0-100, lista de señales). Las señales son claves de traducción."""
    flags = []
    internal = {d.lower().lstrip("@") for d in internal_domains if d}
    domain = msg.domain
    external = bool(domain) and not any(domain == d or domain.endswith("." + d) for d in internal)
    name = (msg.sender_name or "").lower()
    text = f"{msg.subject}\n{body}".lower()
    plain_domain = domain.replace("-", "")
    score = 0
    if external:
        score += 10
        flags.append("ph_external")
        if lookalike(domain, internal):
            score += 30
            flags.append("ph_lookalike")
        brands = [w for w in BRAND_WORDS if w in name and w.replace(" ", "") not in plain_domain]
        own_name = any(n in name for n in _org_names(internal))
        if brands or own_name:
            score += 20
            flags.append("ph_impersonation")
        if domain in FREEMAIL and (brands or own_name or any(re.search(rf"\b{t}\b", name) for t in TITLES)):
            score += 15
            flags.append("ph_freemail")
    if "@" in name and msg.sender_email and msg.sender_email.lower() not in name:
        score += 25
        flags.append("ph_name_email")
    if msg.reply_to and "@" in msg.reply_to and msg.reply_to.lower().rsplit("@", 1)[1] != domain:
        score += 20
        flags.append("ph_reply_to")
    if any(w in text for w in URGENCY):
        score += 15
        flags.append("ph_urgency")
    if any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in CREDENTIALS):
        score += 20
        flags.append("ph_credentials")
    mismatch = False
    for href, label in HREF_RE.findall(html or ""):
        shown = htmllib.unescape(TAG_RE.sub("", label)).strip()
        host = _host(href)
        if re.match(r"^(https?://|www\.)?[\w-]+(\.[\w-]+)+", shown) and host:
            shown_host = _host(shown if "://" in shown else "http://" + shown)
            if shown_host and _registrable(shown_host) != _registrable(host):
                mismatch = True
    if mismatch:
        score += 25
        flags.append("ph_link_mismatch")
    links = find_links(body, html)
    hosts = {_host(u) for u in links}
    if any(IP_URL.match(u) for u in links):
        score += 20
        flags.append("ph_ip_link")
    if hosts & SHORTENERS:
        score += 10
        flags.append("ph_shortener")
    if any(h.endswith(RISKY_TLDS) for h in hosts if h):
        score += 10
        flags.append("ph_tld")
    if any(a.lower().endswith(RISKY_EXT) for a in msg.attachments or []):
        score += 20
        flags.append("ph_attachment")
    return min(100, score), flags


def risk_level(score):
    return "high" if score >= 60 else "medium" if score >= PHISHING_THRESHOLD else "low"
