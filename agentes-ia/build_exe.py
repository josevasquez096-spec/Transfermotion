"""Crea los ejecutables (.exe en Windows) de las apps de la suite con PyInstaller.

Uso:  python -m pip install -r requirements-dev.txt
      python build_exe.py            # todas las apps
      python build_exe.py DataPilot  # solo una

Los ejecutables quedan en la carpeta dist/. Cada uno es un único archivo que no necesita Python instalado.
"""

import os
import subprocess
import sys
from pathlib import Path

from suite.icons import save_ico

ROOT = Path(__file__).resolve().parent
APPS = {  # nombre: (texto del icono, color)
    "DataPilot": ("XL", "#217346"),
    "BIPilot": ("BI", "#B8860B"),
    "DocPilot": ("W", "#2B579A"),
    "SlidePilot": ("P", "#C43E1C"),
    "FraudPilot": ("FR", "#7B1E3A"),
    "IcePilot": ("IB", "#6D28D9"),
    "MailPilot": ("MP", "#0F6CBD"),
}
# Plantillas y temas que las librerías cargan desde sus propios archivos.
DATA_PACKAGES = ("sv_ttk", "docx", "pptx")
# python-docx y python-pptx abren sus plantillas con rutas como «docx/parts/../templates/…»: dentro del
# ejecutable esas carpetas tienen que existir, así que se crean con un archivo vacío.
PATH_DIRS = ("docx/parts", "pptx/oxml", "pptx/shapes")
EXCLUDES = ("matplotlib", "scipy", "IPython", "pytest", "notebook", "PyQt5", "PySide6")
# MailPilot: diccionarios del corrector (solo los tres idiomas de la suite) y el módulo de zonas horarias que
# pywin32 carga al convertir las fechas de Outlook.
SPELL_LANGS = {"MailPilot": ("en", "es", "fr")}
HIDDEN_IMPORTS = {"MailPilot": ("win32timezone",)}


def extra_args(name):
    args = []
    if name in SPELL_LANGS:
        import spellchecker

        resources = Path(spellchecker.__file__).parent / "resources"
        for lang in SPELL_LANGS[name]:
            args += ["--add-data", f"{resources / f'{lang}.json.gz'}{os.pathsep}spellchecker/resources"]
    for module in HIDDEN_IMPORTS.get(name, ()):
        if sys.platform == "win32":
            args += ["--hidden-import", module]
    return args


def build(name):
    icons = ROOT / "build" / "icons"
    icons.mkdir(parents=True, exist_ok=True)
    ico = icons / f"{name}.ico"
    save_ico(*APPS[name], ico)
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
           "--name", name, "--icon", str(ico), "--distpath", str(ROOT / "dist"),
           "--workpath", str(ROOT / "build" / name), "--specpath", str(ROOT / "build")]
    for pkg in DATA_PACKAGES:
        cmd += ["--collect-data", pkg]
    marker = ROOT / "build" / "keep.txt"
    marker.write_text("PilotSuite\n", encoding="utf-8")
    for folder in PATH_DIRS:
        cmd += ["--add-data", f"{marker}{os.pathsep}{folder}"]
    for mod in EXCLUDES:
        cmd += ["--exclude-module", mod]
    cmd += extra_args(name)
    cmd.append(str(ROOT / f"{name}.py"))
    print(f"\n=== {name} ===", flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT)


def main():
    names = sys.argv[1:] or list(APPS)
    unknown = [n for n in names if n not in APPS]
    if unknown:
        sys.exit(f"Apps desconocidas: {', '.join(unknown)}. Opciones: {', '.join(APPS)}")
    for name in names:
        build(name)
    print("\nListo. Ejecutables en:", ROOT / "dist")


if __name__ == "__main__":
    main()
