"""IcePilot: catálogo de juegos, validación del contenido y generación de tableros (sin interfaz).

Cada juego tiene columnas de contenido (lo que el usuario edita en la tabla) y opciones propias. La función
`prepare()` convierte la configuración en los datos que usa el juego HTML, Word o PowerPoint: normaliza el
contenido, genera tableros, cartones y sopas de letras (con semilla, para que se puedan repetir) y devuelve los
avisos de validación.
"""

import random
import re
import unicodedata

# Opciones: (clave, tipo, valor por defecto, mínimo/máximo u opciones)
GAMES = {
    "quiz": {"emoji": "🏆", "engine": "quiz", "columns": ["question", "a", "b", "c", "d", "correct", "explain"],
             "pptx": True, "teams": True,
             "options": [("seconds", "int", 20, (0, 120)), ("points", "int", 100, (1, 1000)),
                         ("shuffle", "bool", False, None), ("shuffle_options", "bool", False, None),
                         ("show_explain", "bool", True, None)]},
    "truefalse": {"emoji": "✅", "engine": "quiz", "columns": ["statement", "answer", "explain"],
                  "pptx": True, "teams": True,
                  "options": [("seconds", "int", 15, (0, 120)), ("points", "int", 100, (1, 1000)),
                              ("shuffle", "bool", False, None), ("show_explain", "bool", True, None)]},
    "trivia": {"emoji": "🧩", "engine": "trivia", "columns": ["category", "points", "question", "answer"],
               "pptx": True, "teams": True, "options": [("negative", "bool", False, None)]},
    "hangman": {"emoji": "🪢", "engine": "hangman", "columns": ["answer", "hint"], "pptx": False, "teams": True,
                "options": [("max_errors", "int", 6, (3, 10)), ("points", "int", 100, (1, 1000)),
                            ("shuffle", "bool", False, None)]},
    "emoji": {"emoji": "😀", "engine": "guess", "columns": ["prompt", "answer", "hint"], "pptx": True,
              "teams": True, "options": [("seconds", "int", 0, (0, 300)), ("points", "int", 100, (1, 1000)),
                                         ("shuffle", "bool", False, None)]},
    "scramble": {"emoji": "🔤", "engine": "guess", "columns": ["answer", "hint"], "pptx": True, "teams": True,
                 "options": [("seconds", "int", 30, (0, 300)), ("points", "int", 100, (1, 1000)),
                             ("shuffle", "bool", False, None)]},
    "snakes": {"emoji": "🐍", "engine": "snakes", "columns": ["question", "a", "b", "c", "d", "correct"],
               "pptx": False, "teams": True,
               "options": [("cells", "choice", "50", ("30", "50", "64", "100")),
                           ("mode", "choice", "challenge", ("dice", "question", "challenge")),
                           ("snakes", "int", 5, (0, 12)), ("ladders", "int", 5, (0, 12)),
                           ("exact_finish", "bool", False, None), ("six_again", "bool", True, None)]},
    "wheel": {"emoji": "🎡", "engine": "wheel", "columns": ["text"], "pptx": True, "teams": False,
              "options": [("remove", "bool", True, None), ("spin_seconds", "int", 5, (2, 12))]},
    "bingo": {"emoji": "🎱", "engine": "bingo", "columns": ["term"], "pptx": False, "teams": False,
              "options": [("size", "choice", "5", ("3", "4", "5")), ("free", "bool", True, None),
                          ("cards", "int", 30, (2, 300)), ("win", "choice", "line", ("line", "full"))]},
    "wordsearch": {"emoji": "🔎", "engine": "wordsearch", "columns": ["word", "clue"], "pptx": False,
                   "teams": False,
                   "options": [("size", "int", 12, (8, 20)), ("diagonal", "bool", True, None),
                               ("reverse", "bool", False, None), ("use_clues", "bool", False, None)]},
    "truths": {"emoji": "🤥", "engine": "truths", "columns": ["person", "s1", "s2", "s3", "lie"], "pptx": True,
               "teams": False, "options": []},
    "wouldrather": {"emoji": "🤔", "engine": "wouldrather", "columns": ["a", "b"], "pptx": True, "teams": False,
                    "options": []},
}
THEMES = {
    "bank": {"primary": "#0B3D91", "accent": "#00A3E0", "bg": "#EEF3FB", "text": "#0F172A", "dark": False},
    "purple": {"primary": "#5B21B6", "accent": "#F59E0B", "bg": "#F5F3FF", "text": "#1E1B4B", "dark": False},
    "teal": {"primary": "#0F766E", "accent": "#F97316", "bg": "#ECFDF5", "text": "#042F2E", "dark": False},
    "red": {"primary": "#B91C1C", "accent": "#FACC15", "bg": "#FEF2F2", "text": "#450A0A", "dark": False},
    "party": {"primary": "#DB2777", "accent": "#22C55E", "bg": "#FDF2F8", "text": "#500724", "dark": False},
    "dark": {"primary": "#1E293B", "accent": "#38BDF8", "bg": "#0F172A", "text": "#E2E8F0", "dark": True},
}
TEAM_COLORS = ["#E21B3C", "#1368CE", "#D89E00", "#26890C", "#8E44AD", "#E67E22", "#16A085", "#7F8C8D"]
TOKENS = ["🦊", "🐼", "🐸", "🐯", "🐧", "🦉", "🐙", "🦄"]
DEFAULT_TEAMS = {"es": ["Equipo Rojo", "Equipo Azul", "Equipo Amarillo", "Equipo Verde"],
                 "en": ["Red Team", "Blue Team", "Yellow Team", "Green Team"],
                 "fr": ["Équipe Rouge", "Équipe Bleue", "Équipe Jaune", "Équipe Verte"]}
TRUE_FALSE = {"es": ("Verdadero", "Falso"), "en": ("True", "False"), "fr": ("Vrai", "Faux")}
ALPHABET = {"es": "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ", "en": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "fr": "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}
BOARD_SHAPES = {"30": (6, 5), "50": (10, 5), "64": (8, 8), "100": (10, 10)}


def default_options(game):
    return {key: default for key, _, default, _ in GAMES[game]["options"]}


def new_config(game="quiz", lang="es"):
    return {
        "type": game, "lang": lang, "title": "", "subtitle": "", "emoji": GAMES[game]["emoji"], "theme": "bank",
        "primary": "", "accent": "", "teams": DEFAULT_TEAMS[lang][:2] if GAMES[game]["teams"] else [],
        "sound": True, "seed": random.randint(1, 999_999), "options": default_options(game), "items": [],
    }


def _clean(value):
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def strip_accents(text, keep_enye=False):
    out = []
    for ch in text:
        if keep_enye and ch in "ñÑ":
            out.append(ch)
            continue
        decomposed = unicodedata.normalize("NFD", ch)
        out.append("".join(c for c in decomposed if unicodedata.category(c) != "Mn"))
    return "".join(out)


def _correct_index(value, options):
    """Acepta A-D, 1-4 o el texto de la opción correcta."""
    v = _clean(value)
    if not v:
        return None
    if len(v) == 1 and v.upper() in "ABCD":
        i = "ABCD".index(v.upper())
        return i if i < len(options) else None
    if v.isdigit() and 1 <= int(v) <= len(options):
        return int(v) - 1
    for i, opt in enumerate(options):
        if opt.strip().lower() == v.lower():
            return i
    return None


TRUE_WORDS = {"v", "verdadero", "verdad", "true", "t", "vrai", "si", "sí", "yes", "y", "1", "x", "cierto", "oui"}
FALSE_WORDS = {"f", "falso", "false", "faux", "no", "non", "0", "mito", "myth", "mythe"}


def _questions(items, warn):
    out = []
    for n, it in enumerate(items, start=1):
        q = _clean(it.get("question"))
        options = [_clean(it.get(k)) for k in "abcd"]
        options = [o for o in options if o]
        if not q:
            continue
        if not options:  # pregunta abierta: la columna «correcta» lleva la respuesta
            answer = _clean(it.get("correct"))
            if not answer:
                warn("w_correct", n=n)
                continue
            out.append({"q": q, "options": [], "correct": None, "answer": answer,
                        "explain": _clean(it.get("explain"))})
            continue
        if len(options) == 1:
            warn("w_options", n=n)
            continue
        correct = _correct_index(it.get("correct"), options)
        if correct is None:
            warn("w_correct", n=n)
            continue
        out.append({"q": q, "options": options, "correct": correct, "answer": options[correct],
                    "explain": _clean(it.get("explain"))})
    return out


def scramble(word, rng):
    """Desordena las letras de cada palabra (siempre distinto del original si es posible)."""
    parts = []
    for w in word.split():
        letters = list(w)
        if len(set(letters)) > 1:
            for _ in range(20):
                rng.shuffle(letters)
                if "".join(letters) != w:
                    break
        parts.append("".join(letters))
    return " / ".join(parts)


def snakes_board(cells, n_snakes, n_ladders, rng):
    """Tablero de serpientes y escaleras: tramos cortos y casi verticales para que se lean bien."""
    cols, rows = BOARD_SHAPES[str(cells)]
    total = cols * rows
    max_rows = max(2, rows // 2 + 1)

    def where(n):
        r, k = (n - 1) // cols, (n - 1) % cols
        return r, (k if r % 2 == 0 else cols - 1 - k)

    def attempt(n_s, n_l):
        used, snakes, ladders = {1, total}, [], []
        for kind, count in (("ladder", n_l), ("snake", n_s)):
            for _ in range(count):
                for _ in range(300):
                    a, b = rng.randint(2, total - 1), rng.randint(2, total - 1)
                    low, high = min(a, b), max(a, b)
                    (r1, c1), (r2, c2) = where(low), where(high)
                    if not 1 <= r2 - r1 <= max_rows or abs(c2 - c1) > 2 or low in used or high in used:
                        continue
                    if kind == "ladder" and high > total - 2:
                        continue
                    used.update((low, high))
                    if kind == "ladder":
                        ladders.append([low, high])
                    else:
                        snakes.append([high, low])
                    break
                else:
                    return None
        return {"cols": cols, "rows": rows, "total": total, "snakes": sorted(snakes), "ladders": sorted(ladders)}

    n_s, n_l = n_snakes, n_ladders
    while True:
        for _ in range(50):
            board = attempt(n_s, n_l)
            if board:
                return board
        if n_s == 0 and n_l == 0:
            return {"cols": cols, "rows": rows, "total": total, "snakes": [], "ladders": []}
        if n_s >= n_l and n_s > 0:
            n_s -= 1
        else:
            n_l -= 1


def bingo_cards(n_terms, size, free, n_cards, rng):
    cells = size * size
    center = cells // 2 if free and size % 2 == 1 else None
    need = cells - (1 if center is not None else 0)
    cards, seen = [], set()
    for _ in range(n_cards * 50):
        if len(cards) == n_cards:
            break
        chosen = rng.sample(range(n_terms), need)
        card = list(chosen)
        if center is not None:
            card.insert(center, -1)  # casilla libre
        key = tuple(card)
        if key in seen:
            continue
        seen.add(key)
        cards.append(card)
    return cards


DIRECTIONS = {"h": (0, 1), "v": (1, 0), "d": (1, 1), "u": (-1, 1)}


def word_search(words, size, diagonal, reverse, lang, rng):
    """Coloca las palabras en una cuadrícula. Devuelve (cuadrícula, colocaciones, no_colocadas)."""
    dirs = [DIRECTIONS["h"], DIRECTIONS["v"]] + ([DIRECTIONS["d"], DIRECTIONS["u"]] if diagonal else [])
    if reverse:
        dirs += [(-dr, -dc) for dr, dc in dirs]
    grid = [[""] * size for _ in range(size)]
    placements, missing = [], []
    for word in sorted(words, key=len, reverse=True):
        placed = False
        for _ in range(600):
            dr, dc = rng.choice(dirs)
            r, c = rng.randrange(size), rng.randrange(size)
            end_r, end_c = r + dr * (len(word) - 1), c + dc * (len(word) - 1)
            if not (0 <= end_r < size and 0 <= end_c < size):
                continue
            if all(grid[r + dr * i][c + dc * i] in ("", ch) for i, ch in enumerate(word)):
                for i, ch in enumerate(word):
                    grid[r + dr * i][c + dc * i] = ch
                placements.append({"word": word, "r": r, "c": c, "dr": dr, "dc": dc})
                placed = True
                break
        if not placed:
            missing.append(word)
    letters = ALPHABET.get(lang, ALPHABET["en"])
    for r in range(size):
        for c in range(size):
            if not grid[r][c]:
                grid[r][c] = rng.choice(letters)
    return ["".join(row) for row in grid], placements, missing


def wordsearch_word(text, lang):
    word = strip_accents(text.upper(), keep_enye=lang == "es")
    return re.sub(r"[^A-ZÑ]", "", word)


def prepare(cfg):
    """Datos listos para el juego + lista de avisos [(clave, parámetros)]."""
    game = cfg["type"]
    opts = {**default_options(game), **(cfg.get("options") or {})}
    lang = cfg.get("lang", "es")
    rng = random.Random(cfg.get("seed", 1))
    items = [{k: _clean(v) for k, v in it.items()} for it in cfg.get("items", [])]
    items = [it for it in items if any(it.values())]
    warnings = []

    def warn(key, **params):
        warnings.append((key, params))

    data = {}
    if game == "quiz":
        data["questions"] = _questions(items, warn)
    elif game == "truefalse":
        labels = TRUE_FALSE.get(lang, TRUE_FALSE["en"])
        questions = []
        for n, it in enumerate(items, start=1):
            answer = strip_accents(it.get("answer", "")).lower()
            if not it.get("statement"):
                continue
            if answer in {strip_accents(w) for w in TRUE_WORDS}:
                correct = 0
            elif answer in FALSE_WORDS:
                correct = 1
            else:
                warn("w_truefalse", n=n)
                continue
            questions.append({"q": it["statement"], "options": list(labels), "correct": correct,
                              "answer": labels[correct], "explain": it.get("explain", "")})
        data["questions"] = questions
    elif game == "trivia":
        cats = {}
        for n, it in enumerate(items, start=1):
            if not it.get("question"):
                continue
            cat = it.get("category") or "—"
            try:
                pts = int(float(it.get("points") or 0))
            except ValueError:
                pts = 0
            cats.setdefault(cat, []).append({"points": pts, "q": it["question"], "a": it.get("answer", "")})
        board = []
        for cat, qs in list(cats.items())[:6]:
            for i, q in enumerate(qs):
                q["points"] = q["points"] or (i + 1) * 100
            board.append({"category": cat, "questions": sorted(qs, key=lambda x: x["points"])[:6]})
        if len(cats) > 6:
            warn("w_trivia_cats")
        data["board"] = board
    elif game == "hangman":
        words = [{"answer": it["answer"].upper(), "hint": it.get("hint", "")} for it in items if it.get("answer")]
        for w in words:
            if len(w["answer"]) > 40:
                warn("w_long", word=w["answer"][:20])
        data["words"] = words
    elif game in ("emoji", "scramble"):
        rounds = []
        for it in items:
            if not it.get("answer"):
                continue
            prompt = it.get("prompt", "") if game == "emoji" else scramble(it["answer"].upper(), rng)
            rounds.append({"prompt": prompt or "❓", "answer": it["answer"], "hint": it.get("hint", "")})
        data["rounds"] = rounds
    elif game == "snakes":
        data["board"] = snakes_board(opts["cells"], int(opts["snakes"]), int(opts["ladders"]), rng)
        data["questions"] = _questions(items, warn)
        data["tokens"] = TOKENS
        if opts["mode"] != "dice" and not data["questions"]:
            warn("w_snakes_questions")
    elif game == "wheel":
        data["entries"] = [it["text"] for it in items if it.get("text")]
        if len(data["entries"]) < 2:
            warn("w_min", n=2)
    elif game == "bingo":
        terms = list(dict.fromkeys(it["term"] for it in items if it.get("term")))
        size = int(opts["size"])
        need = size * size - (1 if opts["free"] and size % 2 else 0)
        data["terms"] = terms
        data["size"] = size
        if len(terms) < need:
            warn("w_bingo_terms", need=need, have=len(terms))
            data["cards"] = []
        else:
            data["cards"] = bingo_cards(len(terms), size, opts["free"], int(opts["cards"]), rng)
            if len(data["cards"]) < int(opts["cards"]):
                warn("w_bingo_unique", n=len(data["cards"]))
    elif game == "wordsearch":
        entries = []
        for it in items:
            word = wordsearch_word(it.get("word", ""), lang)
            if len(word) >= 2:
                entries.append({"word": word, "label": it.get("word", ""), "clue": it.get("clue", "")})
        size = int(opts["size"])
        longest = max((len(e["word"]) for e in entries), default=0)
        size = max(size, longest)
        grid, placements, missing = word_search([e["word"] for e in entries], size, opts["diagonal"],
                                                opts["reverse"], lang, rng)
        for _ in range(4):
            if not missing:
                break
            size += 1
            grid, placements, missing = word_search([e["word"] for e in entries], size, opts["diagonal"],
                                                    opts["reverse"], lang, rng)
        if missing:
            warn("w_wordsearch", words=", ".join(missing))
        placed = {p["word"] for p in placements}
        data.update(grid=grid, placements=placements, words=[e for e in entries if e["word"] in placed])
    elif game == "truths":
        people = []
        for n, it in enumerate(items, start=1):
            statements = [it.get(k, "") for k in ("s1", "s2", "s3")]
            if not all(statements):
                continue
            lie = it.get("lie", "")
            if lie not in ("1", "2", "3"):
                warn("w_lie", n=n)
                continue
            people.append({"person": it.get("person", "") or f"#{n}", "statements": statements, "lie": int(lie) - 1})
        data["people"] = people
    elif game == "wouldrather":
        data["pairs"] = [{"a": it["a"], "b": it["b"]} for it in items if it.get("a") and it.get("b")]
    count = sum(len(v) for k, v in data.items() if k in ("questions", "board", "words", "rounds", "entries", "terms",
                                                        "people", "pairs") and isinstance(v, list))
    if game == "snakes":
        count = 1
    if not count:
        warnings.insert(0, ("w_empty", {}))
    if opts.get("shuffle"):
        for key in ("questions", "words", "rounds"):
            if key in data and game != "snakes":
                rng.shuffle(data[key])
    if opts.get("shuffle_options"):
        for q in data.get("questions", []):
            if q["correct"] is not None:
                right = q["options"][q["correct"]]
                rng.shuffle(q["options"])
                q["correct"] = q["options"].index(right)
    return data, warnings


def theme_colors(cfg):
    theme = dict(THEMES.get(cfg.get("theme"), THEMES["bank"]))
    for key in ("primary", "accent"):
        if re.fullmatch(r"#[0-9a-fA-F]{6}", cfg.get(key) or ""):
            theme[key] = cfg[key]
    return theme
