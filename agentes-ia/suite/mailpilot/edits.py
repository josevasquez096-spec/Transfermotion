"""Borradores: separar el historial citado y aplicar correcciones sin reescribir todo el correo.

Outlook guarda el borrador como un documento de Word con formato, firma e imágenes. En lugar de sustituir el
cuerpo entero (se perdería el formato), `diff_changes` calcula cambios pequeños de «buscar → reemplazar» que se
aplican en orden, cada uno a partir del anterior; `apply_changes` hace lo mismo sobre un texto normal.
"""

import difflib
import re

_TOKEN = re.compile(r"\w+|\s+|[^\w\s]")
# Principio del mensaje citado en respuestas y reenvíos (Outlook, Gmail…) en los tres idiomas.
_QUOTED = re.compile(
    r"^(?:_{10,}\s*$"
    r"|-{3,}\s*(?:original message|mensaje original|message d'origine)\s*-{3,}"
    r"|(?:from|de)\s?:.+\n(?:.*\n){0,3}?(?:sent|enviado|envoyé|date|fecha)\s?:"
    r"|(?:on|el|le) .{5,120}(?:wrote|escribió|a écrit)\s?:\s*$)",
    re.I | re.M)
_CONTROL = re.compile(r"[\x00-\x08\x0e-\x1f]")


def word_text(text):
    """Texto de un documento de Word con saltos «\\n» y sin caracteres de control (misma longitud)."""
    text = text.replace("\r", "\n").replace("\x0b", "\n").replace("\x07", "\n").replace("\x0c", "\n")
    return _CONTROL.sub(" ", text)


def split_quoted(text):
    """(texto propio, historial citado). El texto propio es siempre un prefijo del original."""
    m = _QUOTED.search(text or "")
    if not m:
        return text or "", ""
    return text[:m.start()], text[m.start():]


def diff_changes(old, new, max_steps=40):
    """Cambios (buscar, reemplazar, saltos) que convierten `old` en `new`.

    Cada búsqueda empieza donde terminó el cambio anterior. Se añaden palabras de contexto (primero sin cruzar
    saltos de línea) hasta que el fragmento sea el primero que aparece desde ahí; un cambio pegado al anterior
    se une con él. Si aun así no basta, `saltos` dice cuántas apariciones hay que pasar antes de la buena."""
    a, b = _TOKEN.findall(old), _TOKEN.findall(new)
    offs_a, offs_b = _offsets(a), _offsets(b)
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    regions = []  # [lo, hi, jlo, jhi] en tokens de `old` y de `new`
    for n, (tag, i1, i2, j1, j2) in enumerate(ops):
        if tag == "equal":
            continue
        ceiling = ops[n + 1][2] if n + 1 < len(ops) else len(a)  # fin del bloque igual que sigue
        lo, hi, jlo, jhi = i1, i2, j1, j2
        newlines = False
        for step in range(max_steps):
            floor = regions[-1][1] if regions else 0
            find = old[offs_a[lo]:offs_a[hi]]
            if find and old.find(find, offs_a[floor]) == offs_a[lo]:
                break
            left = lo > floor and (newlines or "\n" not in a[lo - 1])
            right = hi < ceiling and (newlines or "\n" not in a[hi])
            if left and (step % 2 == 0 or not right or not find):
                lo, jlo = lo - 1, jlo - 1
            elif right:
                hi, jhi = hi + 1, jhi + 1
            elif left:
                lo, jlo = lo - 1, jlo - 1
            elif not newlines:
                newlines = True
            elif regions and lo == floor:  # pegado al cambio anterior: se aplican juntos
                lo, _, jlo, _ = regions.pop()
            else:
                break
        regions.append([lo, hi, jlo, jhi])
    changes, floor = [], 0
    for lo, hi, jlo, jhi in regions:
        find, replace = old[offs_a[lo]:offs_a[hi]], new[offs_b[jlo]:offs_b[jhi]]
        skips, at = 0, old.find(find, offs_a[floor]) if find else -1
        while find and 0 <= at < offs_a[lo]:
            skips += 1
            at = old.find(find, at + len(find))
        changes.append((find, replace, skips))
        floor = hi
    return changes


def _offsets(tokens):
    out, pos = [0], 0
    for token in tokens:
        pos += len(token)
        out.append(pos)
    return out


def apply_changes(text, changes):
    """Aplica en orden los cambios de `diff_changes`. Devuelve (texto, aplicados, fallidos)."""
    pos, applied, failed = 0, 0, 0
    for find, replace, skips in changes:
        at = text.find(find, pos) if find else -1
        for _ in range(skips):
            if at < 0:
                break
            at = text.find(find, at + len(find))
        if at < 0:
            failed += 1
            continue
        text = text[:at] + replace + text[at + len(find):]
        pos = at + len(replace)
        applied += 1
    return text, applied, failed
