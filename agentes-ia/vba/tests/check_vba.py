"""A small static check of the VBA files (there is no VBA compiler outside Office).

Finds what Word's "Debug > Compile" would reject most often: undeclared names (Option Explicit), unclosed blocks
(If/For/Do/Select/With/Sub/Function/Property), For Each variables that are not Variant/Object, characters that the
VBA editor cannot import, and lines that are too long.
Usage: python vba/tests/check_vba.py   (exit code 1 when something is found)
"""

import re
import sys
from pathlib import Path

VBA = Path(__file__).resolve().parents[1]
FILES = ["MIText.bas", "MIPilot.bas", "MICtl.cls", "MIMain.cls", "MILetter.cls", "MIForm_code.txt"]

KEYWORDS = set("""
and as attribute binary byref byval call case close const declare dim do each else elseif end erase error exit
explicit false for function get goto if in is let lib like loop me mod new next not nothing on open option optional
or output preserve print private property ptrsafe public put redim resume select set step sub then to true until wend
while with withevents xor access write input append alias boolean byte collection currency date double integer long
longptr object single string variant empty null base compare text
""".split())

BUILTINS = set("""
abs array asc ascw callbyname cbool cbyte ccur cdate cdbl chr chrw cint clng clnglng clngptr createobject csng cstr
cvar date dateserial day debug dir doevents environ err error format getsetting hex iif inputbox instr instrrev int
isarray isdate isempty iserror ismissing isnull isnumeric isobject join kill lbound lcase left len loadpicture ltrim
mid month msgbox now oct replace rgb right rnd randomize rtrim savesetting shell space split str strcomp strconv
string strptr strreverse time timeserial timer trim typename ubound ucase val vartype year
vbcrlf vbcr vblf vbtab vbnullchar vbnullstring vbexclamation vbinformation vbquestion vbcritical vbyesno vbyesnocancel
vbyes vbno vbcancel vbok vbokonly vbnormalfocus vbobjecterror vbtextcompare vbbinarycompare vbmethod vbget vblet vbset
vbmsgboxresult vba userforms documents application thisdocument commandbars customizationcontext centimeterstopoints
activedocument msforms freefile unload
""".split())

TYPES_OK_FOR_EACH = {"variant", "object"}
OBJECT_TYPES = {"object", "collection", "mictl", "mimain", "miletter"}


def top_level_args(text):
    """Arguments of a call (top-level commas), or [] when there are none."""
    depth, cur, args = 0, "", []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            args.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip() or args:
        args.append(cur)
    return [a.strip() for a in args]


def closing(text, start):
    """Index of the ")" that closes the "(" at text[start]."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def strip_code(line):
    """The line without strings and comment (strings become "")."""
    out, i, n = [], 0, len(line)
    while i < n:
        c = line[i]
        if c == '"':
            j = i + 1
            while j < n:
                if line[j] == '"':
                    if j + 1 < n and line[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            out.append('""')
            i = j + 1
            continue
        if c == "'":
            break
        out.append(c)
        i += 1
    return "".join(out)


def logical_lines(text):
    """Joins " _" continuations. Yields (first line number, code)."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        start, parts = i + 1, []
        while True:
            code = strip_code(lines[i]).rstrip()
            if code.endswith(" _"):
                parts.append(code[:-2])
                i += 1
                continue
            parts.append(code)
            break
        i += 1
        yield start, " ".join(parts)


def split_statements(code):
    """Splits on ":" statement separators (not ":=")."""
    out, cur, i = [], "", 0
    while i < len(code):
        c = code[i]
        if c == ":" and code[i + 1:i + 2] != "=":
            out.append(cur)
            cur = ""
        else:
            cur += c
        i += 1
    out.append(cur)
    return [s.strip() for s in out if s.strip()]


DECL = re.compile(r"^(?:(?:public|private|static|dim|const|global)\s+)+(?:withevents\s+)?(.*)$", re.I)
PROC = re.compile(r"^(?:(?:public|private|friend|static)\s+)*(sub|function|property\s+get|property\s+let|"
                  r"property\s+set|declare\s+ptrsafe\s+function|declare\s+ptrsafe\s+sub|declare\s+function|"
                  r"declare\s+sub)\s+(\w+)\s*(?:lib\s+\"\"\s*(?:alias\s+\"\"\s*)?)?(?:\((.*)\))?", re.I)
IDENT = re.compile(r"(?<![\w.#$&])([A-Za-z_]\w*)\$?")


def declared_names(decl):
    """Names in 'a As Long, b(3) As String, c' (also parameters)."""
    names, depth, cur = [], 0, ""
    for ch in decl + ",":
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            m = re.match(r"\s*(?:optional\s+)?(?:byval\s+|byref\s+)?(?:paramarray\s+)?(\w+)", cur, re.I)
            t = re.search(r"\bas\s+(?:new\s+)?([\w.]+)", cur, re.I)
            if m:
                names.append((m.group(1), (t.group(1) if t else "variant").lower()))
            cur = ""
        else:
            cur += ch
    return names


def is_proc_start(st):
    m = PROC.match(st)
    if not m or st.lower().startswith("end "):
        return None
    return m


def call_problems(st, low, signatures, local, local_types, current, current_name):
    single = re.match(r"^(?:else)?if\b.*?\bthen\s+(.+)$", st, re.I)
    if single:   # one-line If: check the statements after Then (and Else)
        out = []
        for part in re.split(r"\s+else\s+", single.group(1), flags=re.I):
            out += call_problems(part.strip(), part.strip().lower(), signatures, local, local_types, current,
                                 current_name)
        return out
    out = []
    # Name(a, b) as a statement needs Call or no parentheses
    m = re.match(r"^(\w+)\s*\((.*)\)$", st)
    if m and m.group(1).lower() in signatures and m.group(1).lower() not in local and "=" not in st.split("(")[0]:
        if len(top_level_args(m.group(2))) > 1:
            out.append(f"'{m.group(1)}(...)' with several arguments must be called without parentheses")
    # argument counts of our own procedures
    for m2 in re.finditer(r"(?<![\w.])(\w+)\b", st):
        word = m2.group(1).lower()
        if word not in signatures or word in local or word == current_name:
            continue
        required, total, kind, _ret = signatures[word]
        rest = st[m2.end():]
        if rest.lstrip().startswith("."):
            continue   # a member of the object it returns (Fso.CopyFile ...)
        if m2.start() == 0 and not rest.lstrip().startswith(("=", "(")):
            args = top_level_args(rest)   # called as a statement: Name a, b
        elif rest.lstrip().startswith("("):
            start = m2.end() + (len(rest) - len(rest.lstrip()))
            end = closing(st, start)
            args = top_level_args(st[start + 1:end]) if end > 0 else []
        elif m2.start() == 0 and kind == "sub" or (m2.start() == 0 and kind == "function" and "=" not in st):
            args = top_level_args(rest)
        else:
            if kind in ("sub",) or required == 0:
                continue
            args = []
        if not (required <= len(args) <= total):
            out.append(f"'{m2.group(1)}' takes {required}-{total} argument(s), got {len(args)}")
    # objects need Set
    m3 = re.match(r"^(set\s+)?(\w+)\s*=\s*(.+)$", st, re.I)
    if m3:
        target, value = m3.group(2).lower(), m3.group(3).strip().lower()
        is_set = bool(m3.group(1))
        target_type = local_types.get(target)
        if target == current_name and current:
            target_type = current[3]
        callee = re.match(r"^(\w+)", value)
        value_type = signatures.get(callee.group(1), (0, 0, "", ""))[3] if callee else ""
        if value.startswith(("new ", "nothing", "createobject(", "documents.", "vba.userforms")):
            value_type = "object"
        if not is_set and target_type in OBJECT_TYPES and value_type in OBJECT_TYPES:
            out.append(f"'{m3.group(2)} = ...' assigns an object without Set")
        if is_set and target_type in ("string", "long", "integer", "boolean", "single", "double"):
            out.append(f"'Set {m3.group(2)}' but it is a {target_type}")
    return out


def check():
    problems = []
    module_names, public_names = set(), set()
    parsed, signatures = {}, {}
    for name in FILES:
        path = VBA / name
        raw = path.read_bytes()
        try:
            raw.decode("ascii")
        except UnicodeDecodeError as e:
            problems.append(f"{name}: non-ASCII character at byte {e.start}")
        text = raw.decode("cp1252", errors="replace")
        for no, raw_line in enumerate(text.splitlines(), 1):
            if len(raw_line) > 1000:
                problems.append(f"{name}:{no}: line too long")
        lines = list(logical_lines(text))
        parsed[name] = lines
        module_names.add(path.stem.lower())
        in_proc = False
        for _no, code in lines:
            st = code.strip()
            low = st.lower()
            m = is_proc_start(st)
            if m:
                public_names.add(m.group(2).lower())
                in_proc = "declare" not in low.split("(")[0]
                params = top_level_args(m.group(3) or "")
                required = sum(1 for a in params if not a.lower().startswith("optional"))
                ret = re.search(r"\)\s*as\s+([\w.]+)\s*$", st, re.I)
                sig = (required, len(params), m.group(1).lower(), ret.group(1).lower() if ret else "")
                scope = name if low.startswith("private") else "*"
                signatures.setdefault(scope, {})[m.group(2).lower()] = sig
                continue
            if re.match(r"^end\s+(sub|function|property)\b", low):
                in_proc = False
                continue
            if not in_proc:
                d = DECL.match(st)
                if d:
                    for n, _t in declared_names(re.sub(r"=.*$", "", d.group(1))):
                        public_names.add(n.lower())
    known = KEYWORDS | BUILTINS | public_names | module_names

    for name, lines in parsed.items():
        stack, local, local_types = [], set(), {}
        current, current_name = None, ""
        sigs = {**signatures.get("*", {}), **signatures.get(name, {})}
        for no, code in lines:
            stripped = code.strip()
            if not stripped or stripped.lower().startswith(("attribute ", "version ", "begin", "multiuse")):
                continue
            if stripped == "END" and name.endswith(".cls"):
                continue
            if re.match(r"^\w+:$", stripped):   # label
                continue
            for st in split_statements(stripped):
                low = st.lower()
                m = is_proc_start(st)
                if m and "declare" not in low.split("(")[0]:
                    stack.append(("proc", no))
                    local, local_types = set(), {}
                    sigs = {**signatures.get("*", {}), **signatures.get(name, {})}
                    current = sigs.get(m.group(2).lower())
                    current_name = m.group(2).lower()
                    if m.group(3):
                        for n, t in declared_names(m.group(3)):
                            local.add(n.lower())
                            local_types[n.lower()] = t
                    continue
                if m:
                    continue
                if re.match(r"^end\s+(sub|function|property)\b", low):
                    if not stack or stack[-1][0] != "proc":
                        problems.append(f"{name}:{no}: End Sub/Function closes {stack[-1] if stack else None}")
                    else:
                        stack.pop()
                    continue
                d = DECL.match(st)
                if d:
                    body = re.sub(r"=.*$", "", d.group(1)) if low.startswith("const") or " const " in f" {low} " \
                        else d.group(1)
                    if stack:
                        for n, t in declared_names(body):
                            local.add(n.lower())
                            local_types[n.lower()] = t
                        if not re.search(r"=", d.group(1)):
                            continue
                        st = d.group(1).split("=", 1)[1]   # check the value of a Const
                        low = st.lower()
                    else:
                        continue
                # blocks
                if re.match(r"^if\b.*\bthen$", low):
                    stack.append(("if", no))
                elif re.match(r"^(else\s*if\b.*then|elseif\b.*then|else)$", low):
                    if not stack or stack[-1][0] != "if":
                        problems.append(f"{name}:{no}: Else without If")
                elif re.match(r"^end\s+if$", low):
                    if not stack or stack[-1][0] != "if":
                        problems.append(f"{name}:{no}: End If without If (open: {stack[-1] if stack else None})")
                    else:
                        stack.pop()
                elif re.match(r"^for\b", low):
                    stack.append(("for", no))
                    fe = re.match(r"^for\s+each\s+(\w+)", low)
                    if fe:
                        t = local_types.get(fe.group(1))
                        if t is not None and t not in TYPES_OK_FOR_EACH:
                            problems.append(f"{name}:{no}: For Each variable '{fe.group(1)}' is {t} "
                                            "(must be Variant or Object)")
                elif re.match(r"^next\b", low):
                    if not stack or stack[-1][0] != "for":
                        problems.append(f"{name}:{no}: Next without For (open: {stack[-1] if stack else None})")
                    else:
                        stack.pop()
                elif re.match(r"^do\b", low):
                    stack.append(("do", no))
                elif re.match(r"^loop\b", low):
                    if not stack or stack[-1][0] != "do":
                        problems.append(f"{name}:{no}: Loop without Do")
                    else:
                        stack.pop()
                elif re.match(r"^select\s+case\b", low):
                    stack.append(("select", no))
                elif re.match(r"^end\s+select$", low):
                    if not stack or stack[-1][0] != "select":
                        problems.append(f"{name}:{no}: End Select without Select")
                    else:
                        stack.pop()
                elif re.match(r"^with\b", low):
                    stack.append(("with", no))
                elif re.match(r"^end\s+with$", low):
                    if not stack or stack[-1][0] != "with":
                        problems.append(f"{name}:{no}: End With without With")
                    else:
                        stack.pop()
                if not stack:
                    continue
                problems.extend(f"{name}:{no}: {msg}" for msg in call_problems(st, low, sigs, local,
                                                                                local_types, current, current_name))
                # undeclared names
                body = re.sub(r"\b\w+\s*:=", " ", st)
                body = re.sub(r"\b(as|new)\s+[\w.]+", " ", body, flags=re.I)
                body = re.sub(r"\b(goto|resume)\s+\w+", " ", body, flags=re.I)
                body = re.sub(r"#\w*", " ", body)
                body = re.sub(r"&H[0-9A-Fa-f]+&?", " ", body)
                for m2 in IDENT.finditer(body):
                    word = m2.group(1).lower()
                    if word not in known and word not in local:
                        problems.append(f"{name}:{no}: '{m2.group(1)}' is not declared")
        if stack:
            problems.append(f"{name}: blocks left open: {stack}")
    return problems


if __name__ == "__main__":
    found = check()
    for p in found:
        print(p)
    print(f"{len(found)} problem(s)")
    sys.exit(1 if found else 0)
