"""Punto de entrada de DocPilot (también se usa para crear DocPilot.exe con PyInstaller)."""

from suite.selftest import maybe_run

if __name__ == "__main__":
    maybe_run("docpilot")  # DocPilot.exe --selftest
    from suite.docpilot.app import main

    main()
