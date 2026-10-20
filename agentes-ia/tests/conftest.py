import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    # Configuración aislada: las pruebas no tocan la del usuario.
    os.environ["PILOT_SUITE_HOME"] = tempfile.mkdtemp(prefix="pilot_suite_tests_")
    os.environ.pop("ANTHROPIC_API_KEY", None)
