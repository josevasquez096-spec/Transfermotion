"""Genera el archivo HTML autónomo de cada juego (sin internet: todo va dentro del archivo)."""

import html
import json

from . import web_base, web_games
from .games import ALPHABET, GAMES, TEAM_COLORS, TOKENS, default_options, prepare, theme_colors
from .web_text import RULES, UI

# La política de seguridad impide que la página haga cualquier conexión externa.
CSP = ("default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; "
       "font-src 'none'; connect-src 'none'; form-action 'none'; base-uri 'none'")


def _rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def _mix(color, other, amount):
    a, b = _rgb(color), _rgb(other)
    return "#" + "".join(f"{round(x * (1 - amount) + y * amount):02X}" for x, y in zip(a, b))


def _rgba(color, alpha):
    r, g, b = _rgb(color)
    return f"rgba({r},{g},{b},{alpha})"


def css_vars(theme):
    surface = "#1E293B" if theme["dark"] else "#FFFFFF"
    return (f":root{{--primary:{theme['primary']};--accent:{theme['accent']};--bg:{theme['bg']};--text:{theme['text']};"
            f"--surface:{surface};--primary-soft:{_mix(theme['primary'], surface, 0.86)};"
            f"--cell-alt:{_mix(theme['primary'], surface, 0.93)};--accent-a:{_rgba(theme['accent'], 0.22)};"
            f"--primary-a:{_rgba(theme['primary'], 0.18)}}}")


def payload(cfg):
    game = cfg["type"]
    data, warnings = prepare(cfg)
    lang = cfg.get("lang", "es")
    theme = theme_colors(cfg)
    options = {**default_options(game), **(cfg.get("options") or {})}
    return {
        "type": game, "lang": lang, "title": cfg.get("title") or "IcePilot", "subtitle": cfg.get("subtitle", ""),
        "emoji": cfg.get("emoji") or GAMES[game]["emoji"], "sound": bool(cfg.get("sound", True)),
        "teams": [t for t in cfg.get("teams", []) if t.strip()] if GAMES[game]["teams"] else [],
        "team_colors": TEAM_COLORS, "tokens": TOKENS, "colors": {"primary": theme["primary"], "accent": theme["accent"]},
        "dark": theme["dark"], "options": options, "data": data, "rules": RULES[game][lang], "ui": UI[lang],
        "alphabet": ALPHABET[lang],
    }, warnings


def build_html(cfg):
    """Devuelve (html, avisos)."""
    data, warnings = payload(cfg)
    engine = GAMES[cfg["type"]]["engine"]
    css, js, runner = web_games.ENGINES[engine]
    theme = theme_colors(cfg)
    # JSON seguro dentro de <script>: sin «<», «>» ni «&» literales.
    blob = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    title = html.escape(data["title"])
    page = f"""<!doctype html>
<html lang="{data['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="generator" content="IcePilot">
<title>{title}</title>
<style>{css_vars(theme)}{web_base.CSS}{css}</style>
</head>
<body>
<header class="top">
  <div class="brand"><span class="logo emoji">{html.escape(data['emoji'])}</span>
    <div><h1>{title}</h1><p>{html.escape(data['subtitle'])}</p></div></div>
  <div class="tools"><button id="btn-rules">📖</button><button id="btn-sound">🔊</button><button id="btn-full">⛶</button></div>
</header>
<main><div id="stage"></div><aside id="score" hidden></aside></main>
<footer id="offline"></footer>
<script type="application/json" id="game-data">{blob}</script>
<script>
{web_base.JS}
{js}
setupChrome();
{runner}();
</script>
</body>
</html>
"""
    return page, warnings
