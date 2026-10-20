"""Punto de entrada de DataPilot (también se usa para crear DataPilot.exe con PyInstaller)."""

from suite.selftest import maybe_run

if __name__ == "__main__":
    maybe_run("datapilot")  # DataPilot.exe --selftest
    from suite.datapilot.app import main

    main()
