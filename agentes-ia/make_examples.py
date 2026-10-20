"""Genera los juegos de ejemplo de IcePilot (contenido «Fraudes recurrentes») en ejemplos/icebreakers/.

Uso: python make_examples.py [es|en|fr]
"""

import sys
from pathlib import Path

from suite.icepilot import content, games, office
from suite.icepilot.build import build_html

NAMES = {"quiz": "01_quiz_kahoot", "truefalse": "02_verdadero_o_falso", "trivia": "03_trivia",
         "hangman": "04_ahorcado", "emoji": "05_emojis", "scramble": "06_palabras_desordenadas",
         "snakes": "07_serpientes_y_escaleras", "wheel": "08_ruleta", "bingo": "09_bingo", "wordsearch": "10_sopa_de_letras",
         "truths": "11_dos_verdades_y_una_mentira", "wouldrather": "12_que_prefieres"}


def main(lang="es"):
    out = Path(__file__).resolve().parent / "ejemplos" / "icebreakers" / lang
    out.mkdir(parents=True, exist_ok=True)
    for game, spec in games.GAMES.items():
        cfg = games.new_config(game, lang)
        cfg["seed"] = 2026
        cfg["title"], cfg["subtitle"] = content.pack_titles("fraud", lang)
        cfg["items"] = content.pack_items("fraud", game, lang, spec["columns"])
        if game == "snakes":
            cfg["teams"] = games.DEFAULT_TEAMS[lang][:3]
        page, warnings = build_html(cfg)
        assert not warnings, (game, warnings)
        (out / f"{NAMES[game]}.html").write_text(page, encoding="utf-8")
        if game == "bingo":
            office.build_docx(cfg, out / f"{NAMES[game]}_cartones.docx")
        if game == "quiz":
            office.build_pptx(cfg, out / f"{NAMES[game]}.pptx")
    print("Ejemplos en", out)


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["es"]))
