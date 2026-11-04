"""The VBA (Word) version of MoreInfo Pilot: static check of every module, and the Word-independent code run in
LibreOffice Basic against the Python version (skipped when LibreOffice is not installed)."""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

VBA = Path(__file__).resolve().parents[1] / "vba"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, VBA / "tests" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_vba_modules_pass_the_static_check():
    assert _load("check_vba").check() == []


@pytest.mark.skipif(shutil.which("soffice") is None, reason="LibreOffice is not installed")
def test_vba_text_helpers_match_python():
    assert _load("run_libreoffice").run() == 0
